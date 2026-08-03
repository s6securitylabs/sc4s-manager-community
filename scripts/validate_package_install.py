#!/usr/bin/env python3
"""Validate a SC4S Manager package install/upgrade/rollback on a disposable host.

Modes:
  --dry-run          Check artifact structure and script syntax only; no system changes.
  --artifact <path>  Path to the sc4s-manager-<version>.tar.gz to validate.
  --workdir <path>   Scratch directory for extraction and intermediate state.
  --evidence-out     Write a JSON evidence file suitable for docs/acceptance/.

Dry-run mode is safe for CI. Live mode is intended for disposable VM/LXC targets
where systemd is available. Do not run live mode on production systems.

Evidence JSON must not contain secrets. argv/stdout/stderr entries are redacted.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SECRET_PATTERN = re.compile(
    r"(TOKEN|SECRET|PASSWORD|CREDENTIAL|HEC_TOKEN)[A-Z0-9_]*\s*[:=]\s*[\"']?[A-Za-z0-9+/=]{12,}",
    re.IGNORECASE,
)

PACKAGE_VERSION = "unknown"


def _now_utc() -> str:
    return datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _redact(text: str) -> str:
    return SECRET_PATTERN.sub(r"\1=[REDACTED]", text)


def _redact_findings(text: str) -> list[str]:
    findings: list[str] = []
    for match in SECRET_PATTERN.finditer(text):
        findings.append(f"possible secret near: {match.group(1)!r}")
    return findings


def _run_check(cmd: list[str], workdir: Path, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {
            "argv": [_redact(a) for a in cmd],
            "mode": "dry-run-skipped",
            "ok": None,
            "stdout_summary": "",
            "stderr_summary": "",
        }
    result = subprocess.run(
        cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(workdir)
    )
    return {
        "argv": [_redact(a) for a in cmd],
        "mode": "live",
        "ok": result.returncode == 0,
        "stdout_summary": _redact(result.stdout[:500]),
        "stderr_summary": _redact(result.stderr[:500]),
    }


def _check_tar_structure(artifact: Path) -> tuple[bool, list[str]]:
    """Return (ok, issues) checking the tarball has the expected root dir."""
    issues: list[str] = []
    try:
        with tarfile.open(artifact) as tf:
            members = tf.getnames()
    except tarfile.TarError as exc:
        return False, [f"tarball open error: {exc}"]

    if not members:
        return False, ["tarball is empty"]
    if not any(m.startswith("sc4s-manager/") for m in members):
        issues.append("tarball root dir is not sc4s-manager/")

    return len(issues) == 0, issues


def _safe_extract_tarball(artifact: Path, extract_dir: Path) -> Path:
    """Extract a release tarball safely and return the extracted package root."""
    package_root = extract_dir / "sc4s-manager"
    with tarfile.open(artifact) as tf:
        for member in tf.getmembers():
            target = (extract_dir / member.name).resolve()
            if not target.is_relative_to(extract_dir.resolve()):
                raise ValueError(f"unsafe archive member path: {member.name}")
        tf.extractall(extract_dir)
    return package_root


def _validate_artifact_install_surface(package_root: Path) -> list[str]:
    """Check that the extracted artifact supports the documented install path."""
    issues: list[str] = []
    required_paths = [
        "deploy/compose/compose.yaml",
        "deploy/compose/.env.example",
        "deploy/compose/env_file.example",
        "deploy/compose/manager.env.example",
        "deploy/install/install.sh",
        "deploy/upgrade/upgrade.sh",
        "deploy/rollback/rollback.sh",
        "scripts/preflight.py",
        "LICENSE",
        "Dockerfile",
        ".github/workflows/release.yml",
        "frontend/dist/index.html",
    ]
    for rel in required_paths:
        if not (package_root / rel).exists():
            issues.append(f"artifact missing install path: {rel}")

    compose = package_root / "deploy" / "compose" / "compose.yaml"
    if compose.exists():
        compose_text = compose.read_text(encoding="utf-8")
        expected_snippets = [
            "/opt/sc4s/env_file",
            "/opt/sc4s/manager.env",
            "/opt/sc4s/local:/etc/syslog-ng/conf.d/local",
            "/opt/sc4s/archive:/var/lib/syslog-ng/archive",
            "/opt/sc4s/tls:/etc/syslog-ng/tls",
            "splunk-sc4s-var:/var/lib/syslog-ng",
            "ghcr.io/splunk/splunk-connect-for-syslog/container3:3.46.0",
            "ghcr.io/s6securitylabs/sc4s-manager",
        ]
        for snippet in expected_snippets:
            if snippet not in compose_text:
                issues.append(f"compose template missing expected install snippet: {snippet}")
        if ":/var/run/docker.sock" in compose_text or "source: /var/run/docker.sock" in compose_text:
            issues.append("compose template must not mount /var/run/docker.sock")

    return issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate SC4S Manager package install/upgrade/rollback on a disposable host."
    )
    parser.add_argument("--artifact", help="Path to sc4s-manager-<version>.tar.gz")
    parser.add_argument("--workdir", required=True, help="Scratch directory for extraction and state")
    parser.add_argument("--dry-run", action="store_true", help="Check artifact structure and syntax only; no system changes")
    parser.add_argument("--evidence-out", help="Write evidence JSON to this path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.dry_run and not args.artifact:
        print("error: --dry-run or --artifact is required", file=sys.stderr)
        return 1

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    artifact_sha256: str = ""
    artifact_ok: bool = True
    artifact_issues: list[str] = []
    version = PACKAGE_VERSION

    extracted_package_root: Path | None = None
    if args.artifact:
        artifact_path = Path(args.artifact)
        if not artifact_path.exists():
            print(f"error: artifact not found: {artifact_path}", file=sys.stderr)
            return 1
        artifact_sha256 = _sha256_file(artifact_path)
        stem = artifact_path.stem.replace(".tar", "")
        if stem.startswith("sc4s-manager-"):
            version = stem[len("sc4s-manager-"):]
        if args.dry_run:
            artifact_ok, artifact_issues = _check_tar_structure(artifact_path)
            if artifact_ok:
                extract_dir = workdir / "extracted"
                extract_dir.mkdir(parents=True, exist_ok=True)
                try:
                    extracted_package_root = _safe_extract_tarball(artifact_path, extract_dir)
                    artifact_issues.extend(_validate_artifact_install_surface(extracted_package_root))
                except (tarfile.TarError, ValueError) as exc:
                    artifact_issues.append(f"artifact extract error: {exc}")
            artifact_ok = artifact_ok and not artifact_issues

    started_at = _now_utc()
    commands: list[dict[str, Any]] = []

    if args.dry_run:
        install_ok: bool | None = None
        install_notes = "dry-run: structure check only"
        upgrade_dry_run_ok: bool | None = None
        rollback_dry_run_ok: bool | None = None
        if extracted_package_root is not None and not artifact_issues:
            backup_fixture = workdir / "rollback-backup.fixture"
            backup_fixture.write_text("dry-run fixture", encoding="utf-8")
            planner_commands = [
                ("artifact-install-dry-run", ["bash", str(extracted_package_root / "deploy/install/install.sh"), "--dry-run"]),
                ("artifact-upgrade-dry-run", ["bash", str(extracted_package_root / "deploy/upgrade/upgrade.sh"), "--artifact", str(Path(args.artifact).resolve()), "--dry-run"]),
                ("artifact-rollback-dry-run", ["bash", str(extracted_package_root / "deploy/rollback/rollback.sh"), "--backup", str(backup_fixture), "--dry-run"]),
            ]
            planner_results: dict[str, bool] = {}
            for mode, cmd in planner_commands:
                result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(extracted_package_root))
                planner_results[mode] = result.returncode == 0
                commands.append({
                    "argv": [_redact(a) for a in cmd], "mode": mode, "ok": result.returncode == 0,
                    "stdout_summary": _redact(result.stdout[:500]), "stderr_summary": _redact(result.stderr[:500]),
                })
            install_ok = planner_results["artifact-install-dry-run"]
            upgrade_dry_run_ok = planner_results["artifact-upgrade-dry-run"]
            rollback_dry_run_ok = planner_results["artifact-rollback-dry-run"]
            install_notes = "artifact install dry-run executed"
        if artifact_issues:
            install_ok = False
            install_notes = "; ".join(artifact_issues)
        upgrade_ok: bool | None = None
        rollback_ok: bool | None = None
        manager_state = "dry-run-not-checked"
        control_daemon_state = "dry-run-not-checked"
        imports_preserved: bool | None = None
        backups_preserved: bool | None = None
        audit_preserved: bool | None = None
    else:
        # Install/upgrade/rollback scripts are planners, not disposable-host lifecycle
        # executors. Do not mislabel a dry-run planner invocation as live lifecycle
        # evidence — fail closed until a real host drill exists.
        install_ok = False
        install_notes = (
            "live lifecycle not executed; install/upgrade/rollback scripts are planners only. "
            "Use --dry-run for planner checks, or capture disposable-host package-drill evidence separately."
        )
        upgrade_ok = False
        rollback_ok = False
        upgrade_dry_run_ok = None
        rollback_dry_run_ok = None
        manager_state = "not-run"
        control_daemon_state = "not-run"
        imports_preserved = None
        backups_preserved = None
        audit_preserved = None
        commands.append({
            "argv": ["live-lifecycle"],
            "mode": "live",
            "ok": False,
            "stdout_summary": "",
            "stderr_summary": install_notes,
        })

    finished_at = _now_utc()

    all_text = json.dumps({"artifact_sha256": artifact_sha256, "version": version})
    redaction_findings = _redact_findings(all_text)

    planner_gate_ok = install_ok is True and upgrade_dry_run_ok is True and rollback_dry_run_ok is True
    lifecycle_gate_ok = install_ok is True and upgrade_ok is True and rollback_ok is True
    evidence: dict[str, Any] = {
        # dry-run without --artifact is a skeleton evidence write; with --artifact it
        # requires the full planner gate. Non-dry-run requires real lifecycle evidence
        # (currently unavailable, so fail closed).
        "ok": (
            artifact_ok and planner_gate_ok if args.dry_run and args.artifact
            else artifact_ok if args.dry_run
            else artifact_ok and lifecycle_gate_ok
        ),
        "planner_gate_ok": planner_gate_ok,
        "lifecycle_gate_ok": lifecycle_gate_ok,
        "version": version,
        "artifact_sha256": artifact_sha256,
        "install": {
            "started_at": started_at,
            "finished_at": finished_at,
            "ok": install_ok,
            "notes": install_notes,
        },
        "upgrade": {
            "ok": upgrade_ok,
            "dry_run_ok": upgrade_dry_run_ok,
        },
        "rollback": {
            "ok": rollback_ok,
            "dry_run_ok": rollback_dry_run_ok,
        },
        "service_state": {
            "manager": manager_state,
            "control_daemon": control_daemon_state,
        },
        "state_preservation": {
            "imports": imports_preserved,
            "backups": backups_preserved,
            "audit": audit_preserved,
        },
        "redaction": {
            "findings": redaction_findings,
        },
        "commands": commands,
    }

    evidence_json = json.dumps(evidence, indent=2, sort_keys=True)

    if args.evidence_out:
        Path(args.evidence_out).write_text(evidence_json, encoding="utf-8")
        print(f"evidence: {args.evidence_out}")
    else:
        print(evidence_json)

    return 0 if evidence["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
