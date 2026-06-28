"""Tests for release artifact manifest contract (Task 1.1) and build script (Task 1.2)."""
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_packaging():
    sys.path.insert(0, str(ROOT / "src"))
    from sc4s_manager import packaging
    return packaging


def test_release_manifest_reports_missing_frontend_dist_without_building_it(tmp_path):
    packaging = load_packaging()
    manifest = packaging.build_manifest(
        version="0.0.1-test",
        git_commit="abc1234",
        created_at="2026-06-14T00:00:00Z",
        root=tmp_path,
    )
    assert "frontend/dist/index.html" in manifest["missing_required_paths"]
    assert manifest["frontend_dist_present"] is False


def test_release_manifest_contains_systemd_control_daemon_units(tmp_path):
    packaging = load_packaging()
    for path_str in packaging.REQUIRED_ARTIFACT_PATHS:
        p = tmp_path / path_str
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("placeholder")

    manifest = packaging.build_manifest(
        version="0.0.1-test",
        git_commit="abc1234",
        created_at="2026-06-14T00:00:00Z",
        root=tmp_path,
    )

    path_names = [entry["path"] for entry in manifest["paths"]]
    assert "deploy/systemd/sc4s-manager-control.service" in path_names
    assert "deploy/systemd/sc4s-manager-control.socket" in path_names
    assert "deploy/systemd/sc4s-manager.service" in path_names
    assert "Dockerfile" in path_names
    assert "deploy/compose/compose.yaml" in path_names
    assert "scripts/build_binary.py" in path_names
    assert "src/sc4s_manager/standalone.py" in path_names
    assert ".github/workflows/release.yml" in path_names
    assert manifest["missing_required_paths"] == []
    assert manifest["frontend_dist_present"] is True


def test_release_compose_matches_sc4s_docker_first_layout():
    """Compose deployment should follow the upstream SC4S /opt/sc4s Docker-first layout."""
    compose_text = (ROOT / "deploy" / "compose" / "compose.yaml").read_text(encoding="utf-8")

    assert "/opt/sc4s/env_file" in compose_text
    assert "/opt/sc4s/local:/etc/syslog-ng/conf.d/local" in compose_text
    assert "/opt/sc4s/archive:/var/lib/syslog-ng/archive" in compose_text
    assert "/opt/sc4s/tls:/etc/syslog-ng/tls" in compose_text
    assert "splunk-sc4s-var:/var/lib/syslog-ng" in compose_text
    assert "/opt/sc4s/manager.env" in compose_text
    assert "- /var/run/docker.sock" not in compose_text
    assert "source: /var/run/docker.sock" not in compose_text
    assert "container3:3.43.0" in compose_text
    assert (ROOT / "deploy" / "compose" / "env_file.example").exists()
    assert (ROOT / "deploy" / "compose" / "manager.env.example").exists()


def test_release_manifest_does_not_include_secret_values(tmp_path):
    packaging = load_packaging()
    manifest = packaging.build_manifest(
        version="0.0.1-test",
        git_commit="abc1234",
        created_at="2026-06-14T00:00:00Z",
        root=tmp_path,
    )
    text = json.dumps(manifest)
    secret_pattern = re.compile(
        r"(TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*\s*[:=]\s*[\"']?[A-Za-z0-9+/=]{12,}",
        re.IGNORECASE,
    )
    assert not secret_pattern.search(text), "manifest must not include literal secret values"


def test_release_manifest_paths_include_sha256(tmp_path):
    packaging = load_packaging()
    for path_str in packaging.REQUIRED_ARTIFACT_PATHS:
        p = tmp_path / path_str
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("placeholder")

    manifest = packaging.build_manifest(
        version="0.0.1-test",
        git_commit="abc1234",
        created_at="2026-06-14T00:00:00Z",
        root=tmp_path,
    )

    for entry in manifest["paths"]:
        assert "sha256" in entry, f"path entry missing sha256: {entry}"
        assert "size_bytes" in entry, f"path entry missing size_bytes: {entry}"
        assert isinstance(entry["sha256"], str) and len(entry["sha256"]) == 64


def test_release_manifest_has_required_top_level_fields(tmp_path):
    packaging = load_packaging()
    manifest = packaging.build_manifest(
        version="0.9.0",
        git_commit="deadbeef",
        created_at="2026-06-14T12:00:00Z",
        root=tmp_path,
    )
    for field in ("version", "git_commit", "created_at", "paths", "frontend_dist_present", "missing_required_paths"):
        assert field in manifest, f"manifest missing required field: {field}"
    assert manifest["version"] == "0.9.0"
    assert manifest["git_commit"] == "deadbeef"
    assert manifest["created_at"] == "2026-06-14T12:00:00Z"


def test_build_release_artifact_fails_without_frontend_dist(tmp_path):
    """build_release_artifact.py must fail when frontend/dist is absent unless --allow-missing-frontend."""
    frontend_dist = ROOT / "frontend" / "dist"
    hidden_dist = None
    if frontend_dist.exists():
        hidden_dist = frontend_dist.parent / f".dist-hidden-for-test-{os.getpid()}"
        frontend_dist.rename(hidden_dist)
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_release_artifact.py"),
             "--version", "0.0.1-test",
             "--output-dir", str(tmp_path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(ROOT),
        )
    finally:
        if hidden_dist is not None and hidden_dist.exists():
            hidden_dist.rename(frontend_dist)
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "frontend" in combined.lower() or "dist" in combined.lower()


def test_build_release_artifact_dry_run_with_allow_missing_frontend(tmp_path):
    """With --allow-missing-frontend the builder must not error on missing dist."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_release_artifact.py"),
         "--version", "0.0.1-test",
         "--output-dir", str(tmp_path),
         "--allow-missing-frontend"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    output_files = list(tmp_path.iterdir())
    names = [f.name for f in output_files]
    assert any("manifest.json" in n for n in names), f"manifest.json not in {names}"


def test_build_release_artifact_produces_tarball_with_root_dir(tmp_path):
    """Tarball must use a deterministic root dir sc4s-manager/."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_release_artifact.py"),
         "--version", "0.0.1-test",
         "--output-dir", str(tmp_path),
         "--allow-missing-frontend"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    tarballs = list(tmp_path.glob("sc4s-manager-*.tar.gz"))
    assert tarballs, f"no tarball found in {tmp_path}"
    tarball = tarballs[0]
    with tarfile.open(tarball) as tf:
        members = tf.getnames()
    assert any(m.startswith("sc4s-manager/") for m in members), "tarball root must be sc4s-manager/"
    assert "sc4s-manager/frontend/dist/index.html" in members
    assert any(m.startswith("sc4s-manager/frontend/dist/assets/") for m in members)
    assert any(m.startswith("sc4s-manager/packs/pan_panos/") for m in members)
    assert not any("frontend/dist/dist/" in m for m in members)
    assert not any("packs/packs/" in m for m in members)


def test_build_release_artifact_does_not_invoke_npm(tmp_path):
    """build_release_artifact.py must never run npm."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    npm_marker = tmp_path / "npm-was-called"
    fake_npm = fake_bin / "npm"
    fake_npm.write_text(f"#!/usr/bin/env bash\ntouch {npm_marker}\nexit 99\n")
    fake_npm.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_release_artifact.py"),
         "--version", "0.0.1-test",
         "--output-dir", str(out_dir),
         "--allow-missing-frontend"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(ROOT),
    )

    assert not npm_marker.exists(), "build_release_artifact.py must not invoke npm"
