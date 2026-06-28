"""Tests for the package/install validator skeleton (Task 1.3)."""
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_package_install.py"


def run_validator(*args):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
    )


def test_validator_script_exists():
    assert VALIDATOR.exists(), f"validator script missing: {VALIDATOR}"


def test_validator_dry_run_exits_zero(tmp_path):
    result = run_validator("--dry-run", "--workdir", str(tmp_path))
    assert result.returncode == 0, result.stderr


def test_validator_dry_run_writes_evidence_json(tmp_path):
    evidence_out = tmp_path / "evidence.json"
    result = run_validator("--dry-run", "--workdir", str(tmp_path), "--evidence-out", str(evidence_out))
    assert result.returncode == 0, result.stderr
    assert evidence_out.exists(), "evidence-out file must be written by --dry-run"
    evidence = json.loads(evidence_out.read_text())
    assert "ok" in evidence
    assert "version" in evidence


def test_validator_evidence_contains_required_fields(tmp_path):
    evidence_out = tmp_path / "evidence.json"
    run_validator("--dry-run", "--workdir", str(tmp_path), "--evidence-out", str(evidence_out))
    assert evidence_out.exists()
    evidence = json.loads(evidence_out.read_text())

    assert "ok" in evidence
    assert "version" in evidence
    assert "artifact_sha256" in evidence

    install = evidence.get("install")
    assert isinstance(install, dict), "evidence.install must be a dict"
    assert "started_at" in install
    assert "finished_at" in install
    assert "ok" in install

    assert "upgrade" in evidence
    assert "ok" in evidence["upgrade"]
    assert "rollback" in evidence
    assert "ok" in evidence["rollback"]

    service_state = evidence.get("service_state")
    assert isinstance(service_state, dict), "evidence.service_state must be a dict"
    assert "manager" in service_state
    assert "control_daemon" in service_state

    assert "state_preservation" in evidence
    sp = evidence["state_preservation"]
    assert "imports" in sp
    assert "backups" in sp
    assert "audit" in sp

    assert "redaction" in evidence
    assert "findings" in evidence["redaction"]

    assert "commands" in evidence
    assert isinstance(evidence["commands"], list)


def test_validator_evidence_does_not_contain_secrets(tmp_path):
    evidence_out = tmp_path / "evidence.json"
    run_validator("--dry-run", "--workdir", str(tmp_path), "--evidence-out", str(evidence_out))
    assert evidence_out.exists()
    text = evidence_out.read_text()
    secret_pattern = re.compile(
        r"(TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*\s*[:=]\s*[\"']?[A-Za-z0-9+/=]{12,}",
        re.IGNORECASE,
    )
    assert not secret_pattern.search(text), "evidence must not contain literal secret values"


def test_validator_requires_dry_run_or_artifact():
    """Running without --dry-run and without --artifact must fail."""
    result = run_validator("--workdir", "/tmp/nonexistent-sc4s-drill")
    assert result.returncode != 0, "validator must fail without --dry-run or --artifact"


def test_validator_rejects_artifact_missing_install_surface(tmp_path):
    """Dry-run with --artifact must reject archives that cannot follow the install runbook."""
    import tarfile

    artifact_root = tmp_path / "artifact-root"
    app_py = artifact_root / "src" / "sc4s_manager" / "app.py"
    app_py.parent.mkdir(parents=True)
    app_py.write_text("# packaged app\n")
    artifact = tmp_path / "sc4s-manager-0.0.1.tar.gz"
    with tarfile.open(artifact, "w:gz") as tf:
        tf.add(app_py, arcname="sc4s-manager/src/sc4s_manager/app.py")

    evidence_out = tmp_path / "evidence.json"
    result = run_validator(
        "--dry-run",
        "--artifact", str(artifact),
        "--workdir", str(tmp_path),
        "--evidence-out", str(evidence_out),
    )
    assert result.returncode != 0
    assert evidence_out.exists()
    evidence = json.loads(evidence_out.read_text())
    assert evidence["ok"] is False
    assert "artifact missing install path" in evidence["install"]["notes"]


def test_validator_dry_run_executes_packaged_install_instructions(tmp_path):
    """A built release tarball should run its packaged install dry-run from the extracted artifact."""
    build_out = tmp_path / "release"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_release_artifact.py"),
            "--version", "0.0.1-test",
            "--output-dir", str(build_out),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    artifact = build_out / "sc4s-manager-0.0.1-test.tar.gz"

    evidence_out = tmp_path / "evidence.json"
    validate = run_validator(
        "--dry-run",
        "--artifact", str(artifact),
        "--workdir", str(tmp_path / "work"),
        "--evidence-out", str(evidence_out),
    )
    assert validate.returncode == 0, validate.stderr
    evidence = json.loads(evidence_out.read_text())
    assert evidence["artifact_sha256"] not in ("", None)
    assert evidence["install"]["ok"] is True
    assert evidence["install"]["notes"] == "artifact install dry-run executed"
    assert any(cmd["mode"] == "artifact-install-dry-run" for cmd in evidence["commands"])


def test_package_install_evidence_template_exists():
    template = ROOT / "docs" / "acceptance" / "package-install-template.json"
    assert template.exists(), f"package-install evidence template missing: {template}"
    data = json.loads(template.read_text())
    assert "ok" in data
    assert "install" in data
    assert "service_state" in data
    assert "redaction" in data
