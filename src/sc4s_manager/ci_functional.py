from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from sc4s_manager.packs import load_packs

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UI_STATIC_PAGES = [
    {"route": "/", "label": "Dashboard", "kind": "static"},
    {"route": "/library", "label": "SecHub Resources", "kind": "static"},
    {"route": "/catalogue", "label": "Source Catalogue", "kind": "static"},
    {"route": "/packs", "label": "Packs", "kind": "static"},
    {"route": "/onboarding-preview", "label": "Onboarding Preview", "kind": "static"},
    {"route": "/sources", "label": "Sources", "kind": "static"},
    {"route": "/destinations", "label": "Destinations", "kind": "static"},
    {"route": "/routes", "label": "Routes", "kind": "static"},
    {"route": "/exports", "label": "Exports", "kind": "static"},
]
SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|secret|token|session|authorization|cookie)\s*[:=]\s*[^\s,}]+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        text = f"{text}T00:00:00Z"
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def redacted_command(command: str, secrets: Iterable[str]) -> str:
    redacted = command
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def build_splunk_lxc_plan(
    *,
    ctid: int,
    hostname: str,
    splunk_image: str,
    admin_password: str,
    indexes: list[str],
    hec_token_name: str = "sc4s-manager-ci-hec",
    network: str | None = None,
    storage: str = "local-zfs",
    memory_mb: int = 8192,
    cores: int = 4,
) -> dict[str, Any]:
    """Return a sanitized, executable command plan for the disposable Splunk LXC.

    The plan deliberately redacts the easy CI-only password from evidence while
    still recording enough commands for an operator/CI wrapper to execute.
    """

    if ctid <= 0:
        raise ValueError("ctid must be positive")
    if not hostname:
        raise ValueError("hostname is required")
    if not splunk_image:
        raise ValueError("splunk_image is required")
    clean_indexes = sorted(dict.fromkeys(index for index in indexes if index))
    if not clean_indexes:
        raise ValueError("at least one Splunk index is required")

    net_arg = network or "name=eth0,bridge=vmbr0,ip=dhcp,type=veth"
    raw_commands = [
        f"sudo -n pct create {ctid} local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst --hostname {hostname} --storage {storage} --cores {cores} --memory {memory_mb} --swap 1024 --onboot 0 --features nesting=1,keyctl=1 --net0 {net_arg}",
        f"sudo -n pct set {ctid} --description 'Disposable SC4S Manager CI Splunk test LXC; safe to destroy'",
        f"sudo -n pct start {ctid}",
        f"sudo -n pct exec {ctid} -- sh -lc 'apt-get update && apt-get install -y docker.io curl jq'",
        (
            "sudo -n pct exec {ctid} -- sh -lc "
            "'docker run -d --name sc4s-manager-ci-splunk --hostname sc4s-manager-ci-splunk "
            "-p 8000:8000 -p 8088:8088 -p 8089:8089 "
            "-e SPLUNK_START_ARGS=--accept-license -e SPLUNK_PASSWORD={password} "
            "{image}'"
        ).format(ctid=ctid, password=admin_password, image=splunk_image),
        f"sudo -n pct exec {ctid} -- sh -lc 'until docker exec sc4s-manager-ci-splunk /opt/splunk/bin/splunk status --accept-license >/dev/null 2>&1; do sleep 5; done'",
        f"sudo -n pct exec {ctid} -- sh -lc 'docker exec sc4s-manager-ci-splunk /opt/splunk/bin/splunk http-event-collector enable -auth admin:{admin_password}'",
    ]
    for index in clean_indexes:
        raw_commands.append(
            f"sudo -n pct exec {ctid} -- sh -lc 'docker exec sc4s-manager-ci-splunk /opt/splunk/bin/splunk add index {index} -auth admin:{admin_password} || true'"
        )
    raw_commands.append(
        f"sudo -n pct exec {ctid} -- sh -lc 'docker exec sc4s-manager-ci-splunk /opt/splunk/bin/splunk http-event-collector create {hec_token_name} -index {clean_indexes[0]} -auth admin:{admin_password} || true'"
    )
    commands = [redacted_command(command, [admin_password]) for command in raw_commands]
    return {
        "kind": "splunk_lxc_plan",
        "disposable": True,
        "ctid": ctid,
        "hostname": hostname,
        "network": net_arg,
        "splunk": {
            "image": splunk_image,
            "admin_password_policy": "ci_only_easy_password",
            "admin_password": "[REDACTED]",
            "hec_token_name": hec_token_name,
            "indexes": clean_indexes,
            "ports": {"web": 8000, "hec": 8088, "management": 8089},
        },
        "commands": commands,
        "raw_command_count": len(raw_commands),
    }


def expected_ui_pages(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for page in DEFAULT_UI_STATIC_PAGES:
        pages.append({**page, "screenshot_required": True})
    for pack in sorted(packs, key=lambda item: str(item.get("id", ""))):
        pack_id = str(pack.get("id", "")).strip()
        if pack_id:
            pages.append({
                "route": f"/packs/{pack_id}",
                "label": f"Pack: {pack.get('display_name', pack_id)}",
                "kind": "pack_detail",
                "pack_id": pack_id,
                "screenshot_required": True,
            })
    return pages


def pack_artifact_hashes(pack: dict[str, Any]) -> dict[str, str]:
    base = Path(pack.get("pack_dir") or "")
    hashes: dict[str, str] = {}
    if not base.exists():
        return hashes
    paths = ["pack.json"]
    for artifact in pack.get("export_artifacts", []):
        source_path = artifact.get("source_path")
        if source_path:
            paths.append(str(source_path))
    for event_set in pack.get("test_event_sets", []):
        path = event_set.get("path")
        if path:
            paths.append(str(path))
    for rel in sorted(dict.fromkeys(paths)):
        path = (base / rel).resolve()
        try:
            path.relative_to(base.resolve())
        except ValueError:
            continue
        if path.is_file():
            hashes[str(path)] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def build_ci_pack_matrix(packs: list[dict[str, Any]], *, release_mode: bool = False) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for pack in sorted(packs, key=lambda item: str(item.get("id", ""))):
        ci = pack.get("ci") if isinstance(pack.get("ci"), dict) else {}
        last_updated = parse_timestamp(ci.get("last_updated"))
        last_tested = parse_timestamp(ci.get("last_tested"))
        status = "selected"
        reason = "selected for CI functional pipeline test"
        if release_mode:
            raw_last_updated = ci.get("last_updated")
            raw_last_tested = ci.get("last_tested")
            if not raw_last_updated or not raw_last_tested:
                status = "stale"
                reason = "missing ci.last_updated or ci.last_tested metadata"
            elif not last_updated or not last_tested:
                status = "stale"
                reason = "invalid ci timestamp metadata"
            elif last_updated > last_tested:
                status = "stale"
                reason = "last_updated is newer than last_tested"
        families = [str(family.get("id")) for family in pack.get("event_families", [])]
        matrix.append({
            "pack_id": pack.get("id"),
            "version": pack.get("version"),
            "status": status,
            "reason": reason,
            "required_index": pack.get("default_index"),
            "default_source": pack.get("default_source"),
            "recommended_transport": pack.get("recommended_transport"),
            "event_sets": [event_set.get("id") for event_set in pack.get("test_event_sets", [])],
            "event_families": families,
            "last_updated": ci.get("last_updated"),
            "last_tested": ci.get("last_tested"),
            "tested_commit": ci.get("tested_commit"),
            "artifact_hashes": pack_artifact_hashes(pack),
        })
    return matrix


def splunk_quote(value: str) -> str:
    return '"' + str(value).replace('"', '\\"') + '"'


def splunk_field_expr(field_name: str) -> str:
    text = str(field_name)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_:.:-]*", text):
        return text
    return "'" + text.replace("'", "\\'") + "'"


def field_presence_alias(field_name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_]+", "_", str(field_name)).strip("_") or "field"
    return f"{base}_present"


def build_basic_spl(pack: dict[str, Any], marker: str) -> str:
    return f'index={pack["default_index"]} {splunk_quote(marker)} | stats count as count by index sourcetype source host'


def build_targeted_spl(pack: dict[str, Any], marker: str) -> dict[str, dict[str, str]]:
    targeted: dict[str, dict[str, str]] = {}
    base = f'index={pack["default_index"]} {splunk_quote(marker)}'
    for family in pack.get("event_families", []):
        family_id = str(family["id"])
        sourcetype = family["expected_sourcetype"]
        required_fields = [str(field) for field in family.get("required_fields", [])]
        required_exprs = [
            f'count(eval(isnotnull({splunk_field_expr(field)}))) as {field_presence_alias(field)}'
            for field in required_fields
        ]
        targeted[family_id] = {
            "sourcetype_search": f'{base} sourcetype={splunk_quote(sourcetype)} | stats count as count by sourcetype',
            "required_fields_search": f'{base} sourcetype={splunk_quote(sourcetype)} | stats {", ".join(required_exprs) if required_exprs else "count as count"}',
        }
    return targeted


def build_run_manifest(packs: list[dict[str, Any]], *, release_mode: bool = False, marker: str | None = None) -> dict[str, Any]:
    marker_id = marker or "sc4s-ci-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    indexes = sorted({str(pack.get("default_index")) for pack in packs if pack.get("default_index")})
    return {
        "generated_at_utc": utc_now(),
        "release_mode": release_mode,
        "marker": marker_id,
        "required_indexes": indexes,
        "ui_pages": expected_ui_pages(packs),
        "pack_matrix": build_ci_pack_matrix(packs, release_mode=release_mode),
        "splunk_plan": build_splunk_lxc_plan(
            ctid=1091,
            hostname="sc4s-manager-ci-splunk",
            splunk_image="splunk/splunk:10.2.3",
            admin_password="changeme-ci-only",
            indexes=indexes or ["sc4s_ci"],
        ),
        "spl_templates": {
            pack["id"]: {
                "basic": build_basic_spl(pack, marker_id),
                "targeted": build_targeted_spl(pack, marker_id),
            }
            for pack in packs
        },
    }


def validate_ci_evidence(evidence: dict[str, Any], *, release_mode: bool = False) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if evidence.get("secrets_redacted") is not True:
        findings.append({"ok": False, "detail": "secrets_redacted must be true"})
    rendered = json.dumps(evidence, sort_keys=True)
    for pattern in SECRET_PATTERNS:
        match = pattern.search(rendered)
        if match and "[REDACTED]" not in match.group(0):
            findings.append({"ok": False, "detail": f"possible unredacted secret near {match.group(1)}"})
            break

    expected_routes = {page.get("route") for page in evidence.get("expected_ui_pages", []) if page.get("route")}
    seen_routes = {page.get("route") for page in evidence.get("ui_pages", []) if page.get("route")}
    for route in sorted(expected_routes - seen_routes):
        findings.append({"ok": False, "detail": f"missing UI evidence for expected route {route}"})

    for page in evidence.get("ui_pages", []):
        route = page.get("route", "<unknown>")
        if not page.get("screenshot_path"):
            findings.append({"ok": False, "detail": f"UI route {route} missing screenshot"})
        if page.get("console_errors"):
            findings.append({"ok": False, "detail": f"UI route {route} has console errors"})
        if page.get("critical_api_failures"):
            findings.append({"ok": False, "detail": f"UI route {route} has critical API failures"})
        redirect_url = str(page.get("redirect_url", "")).lower()
        try:
            login_host = urlsplit(redirect_url).hostname == "login.s6ops.com"
        except ValueError:
            login_host = False
        if page.get("status") in {302, 303} or "application/o/authorize" in redirect_url or login_host:
            findings.append({"ok": False, "detail": f"UI route {route} authenticated page appears to be a login redirect"})

    for row in evidence.get("pack_matrix", []):
        status = row.get("status")
        pack_id = row.get("pack_id", "<unknown>")
        if release_mode and status in {"stale", "failed", "unsupported", "skipped"}:
            findings.append({"ok": False, "detail": f"pack {pack_id} is {status}: {row.get('reason', '')}"})

    for result in evidence.get("spl_results", []):
        pack_id = result.get("pack_id", "<unknown>")
        marker = result.get("marker")
        count = result.get("result_count")
        if not isinstance(count, int) or count <= 0:
            findings.append({"ok": False, "detail": f"pack {pack_id} SPL result_count must be greater than zero"})
        if marker and marker not in json.dumps(result.get("results", []), sort_keys=True):
            findings.append({"ok": False, "detail": f"pack {pack_id} SPL results do not contain marker"})

    return findings or [{"ok": True, "detail": "CI functional evidence is valid"}]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(command: str, *, timeout: int = 900) -> dict[str, Any]:
    completed = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=timeout)
    return {"command": command, "returncode": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or validate SC4S Manager CI functional acceptance evidence.")
    parser.add_argument("--packs-root", default=str(ROOT / "packs"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "acceptance" / "ci-functional-manifest.json"))
    parser.add_argument("--release-mode", action="store_true")
    parser.add_argument("--execute-lxc-plan", action="store_true", help="Execute the disposable Splunk LXC plan. Off by default for safety.")
    parser.add_argument("--validate-evidence", help="Validate an existing CI functional evidence JSON file.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.validate_evidence:
        evidence = json.loads(Path(args.validate_evidence).read_text(encoding="utf-8"))
        findings = validate_ci_evidence(evidence, release_mode=args.release_mode)
        print(json.dumps({"ok": all(finding["ok"] for finding in findings), "findings": findings}, indent=2, sort_keys=True))
        return 0 if all(finding["ok"] for finding in findings) else 1

    packs = load_packs(args.packs_root)
    manifest = build_run_manifest(packs, release_mode=args.release_mode)
    if args.execute_lxc_plan:
        executed = []
        for command in manifest["splunk_plan"]["commands"]:
            # Commands are redacted for evidence; execution requires the raw plan in a CI wrapper.
            # Refuse to execute redacted commands rather than giving a fake green build.
            if "[REDACTED]" in command:
                raise SystemExit("refusing to execute redacted command plan; provide CI wrapper with runtime secret injection")
            executed.append(run_command(command))
        manifest["lxc_execution"] = executed
    write_json(Path(args.output), manifest)
    print(json.dumps({"ok": True, "output": args.output, "packs": len(packs), "ui_pages": len(manifest["ui_pages"])}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
