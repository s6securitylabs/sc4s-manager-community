from pathlib import Path
import os
import re
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_compose_template_does_not_grant_docker_socket_access():
    manager_unit = read("deploy/systemd/sc4s-manager.service")
    compose = read("deploy/compose/compose.yaml")

    assert "docker.sock" not in manager_unit
    assert ":/var/run/docker.sock" not in compose
    assert "SC4S_CONTROL_SOCKET=/run/sc4s-manager/control.sock" in manager_unit
    assert "host-root Docker control" in compose


def test_compose_defaults_pin_manager_and_sc4s_images():
    compose = read("deploy/compose/compose.yaml")
    defaults = read("deploy/compose/.env.example")

    assert "SC4S_MANAGER_VERSION:-latest" not in compose
    assert "SC4S_MANAGER_VERSION=latest" not in defaults
    assert "SC4S_MANAGER_VERSION:-1.0.2" in compose
    assert "SC4S_MANAGER_VERSION=1.0.2" in defaults


def test_dockerfile_packages_frontend_and_runs_non_root():
    dockerfile = read("Dockerfile")

    assert "FROM node:" in dockerfile
    assert "FROM python:3.11" in dockerfile
    assert "COPY --from=frontend-builder" in dockerfile
    assert "USER sc4s-manager" in dockerfile
    assert "EXPOSE 8090" in dockerfile
    assert "HEALTHCHECK" in dockerfile


def test_templates_do_not_contain_literal_secret_values():
    paths = [
        "deploy/compose/compose.yaml",
        "deploy/compose/.env.example",
        "deploy/compose/manager.env.example",
        "deploy/compose/env_file.example",
        "deploy/systemd/sc4s-manager.service",
        "docs/acceptance/security-acceptance.md",
    ]
    secret_assignment = re.compile(
        r"(TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*\s*[:=]\s*['\"]?[A-Za-z0-9+/=]{12,}",
        re.IGNORECASE,
    )
    for path in paths:
        text = read(path)
        assert not secret_assignment.search(text), path


def test_systemd_units_reference_packaged_unit_names():
    manager_unit = read("deploy/systemd/sc4s-manager.service")
    control_unit = read("deploy/systemd/sc4s-manager-control.service")
    socket_unit = read("deploy/systemd/sc4s-manager-control.socket")

    assert "sc4s-manager-control.service" in manager_unit
    assert "sc4s-control.service" not in manager_unit
    assert "Requires=sc4s-manager-control.socket" in control_unit
    assert "WantedBy=multi-user.target" not in control_unit
    assert "Service=sc4s-manager-control.service" in socket_unit
    assert "SocketMode=0660" in socket_unit


def test_control_audit_path_is_inside_packaged_state_root():
    control_unit = read("deploy/systemd/sc4s-manager-control.service")
    control_code = read("src/sc4s_manager/control.py")

    assert "SC4S_CONTROL_AUDIT=/opt/sc4s-manager/state/control-audit.jsonl" in control_unit
    assert '"/opt/sc4s-manager/state/control-audit.jsonl"' in control_code
    legacy_state_root = "/opt/sc4s-" + "n" + "ext/state"
    assert legacy_state_root not in control_unit
    assert legacy_state_root not in control_code


def test_manager_defaults_and_install_plan_use_packaged_runtime_root():
    app_code = read("src/sc4s_manager/app.py")
    install = read("deploy/install/install.sh")

    assert 'os.environ.get("SC4S_MANAGER_ROOT", "/opt/sc4s-manager")' in app_code
    assert "manager runtime directories under $prefix/state, $prefix/backups, and $prefix/templates" in install
    assert "SC4S TLS/config directories under /opt/sc4s/tls and /opt/sc4s/local" in install
    assert "sc4s-manager:sc4s-manager" in install


def test_dry_run_scripts_reject_execute_flags():
    install = subprocess.run(
        [str(ROOT / "deploy/install/install.sh"), "--execute"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    upgrade = subprocess.run(
        [str(ROOT / "deploy/upgrade/upgrade.sh"), "--execute", "--artifact", str(ROOT / "README.md")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert install.returncode == 2
    assert upgrade.returncode == 2


def test_upgrade_dry_run_rejects_non_archive_artifacts():
    result = subprocess.run(
        [str(ROOT / "deploy/upgrade/upgrade.sh"), "--dry-run", "--artifact", str(ROOT / "README.md")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 1
    assert "not a supported archive" in result.stderr


def test_dry_run_scripts_do_not_run_frontend_build_tools(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    npm_marker = tmp_path / "npm-was-called"
    fake_npm = fake_bin / "npm"
    fake_npm.write_text(f"#!/usr/bin/env bash\ntouch {npm_marker}\nexit 99\n")
    fake_npm.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

    install = subprocess.run(
        [str(ROOT / "deploy/install/install.sh"), "--dry-run"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    artifact_root = tmp_path / "artifact-root"
    app_py = artifact_root / "src" / "sc4s_manager" / "app.py"
    app_py.parent.mkdir(parents=True)
    app_py.write_text("# packaged app marker\n")
    artifact = tmp_path / "sc4s-manager.tar"
    with tarfile.open(artifact, "w") as tar:
        tar.add(app_py, arcname="sc4s-manager/src/sc4s_manager/app.py")

    upgrade = subprocess.run(
        [str(ROOT / "deploy/upgrade/upgrade.sh"), "--dry-run", "--artifact", str(artifact)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert install.returncode == 0, install.stderr
    assert upgrade.returncode == 0, upgrade.stderr
    assert not npm_marker.exists(), "dry-run scripts must not invoke npm or mutate frontend outputs"
    combined_output = install.stdout + install.stderr + upgrade.stdout + upgrade.stderr
    assert "running npm build" not in combined_output
    assert "scripts/build_frontend.sh" in combined_output


def test_frontend_build_is_an_explicit_packaging_script():
    build_script = read("scripts/build_frontend.sh")
    install = read("deploy/install/install.sh")
    upgrade = read("deploy/upgrade/upgrade.sh")

    assert "npm run build" in build_script
    assert "npm ci" in build_script
    assert "npm run build" not in install
    assert "npm run build" not in upgrade
    assert "scripts/build_frontend.sh" in install
    assert "scripts/build_frontend.sh" in upgrade


def test_build_release_artifact_script_exists():
    build_script = ROOT / "scripts" / "build_release_artifact.py"
    binary_script = ROOT / "scripts" / "build_binary.py"
    assert build_script.exists()
    assert binary_script.exists()
    source = build_script.read_text()
    binary_source = binary_script.read_text()
    assert "--allow-missing-frontend" in source
    assert "PyInstaller" in binary_source
    assert "--add-data" in binary_source
    assert "npm run build" not in source, "build_release_artifact.py must not call npm run build"
    assert "npm ci" not in source, "build_release_artifact.py must not call npm ci"
    assert "npm install" not in source, "build_release_artifact.py must not call npm install"


def test_github_release_workflow_validates_install_artifact_before_publish():
    workflow = read(".github/workflows/release.yml")

    assert "Build release tarball" in workflow
    assert "Validate release tarball install dry run" in workflow
    assert "scripts/validate_package_install.py" in workflow
    assert "--artifact \"dist/release/sc4s-manager-${{ steps.version.outputs.version }}.tar.gz\"" in workflow
    assert "--evidence-out \"dist/release/package-install-dry-run.json\"" in workflow
    assert workflow.index("Build release tarball") < workflow.index("Validate release tarball install dry run")
    assert workflow.index("Validate release tarball install dry run") < workflow.index("Build and push Docker image")
    assert "docker/build-push-action@v7" in workflow
    assert "IMAGE_NAME: ghcr.io/${{ github.repository }}" in workflow
    assert "${{ env.IMAGE_NAME }}:${{ steps.version.outputs.version }}" in workflow


def test_build_release_artifact_script_does_not_run_npm(tmp_path):
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
        ["python3", str(ROOT / "scripts" / "build_release_artifact.py"),
         "--version", "0.0.1-test",
         "--output-dir", str(out_dir),
         "--allow-missing-frontend"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(ROOT),
    )

    assert result.returncode == 0, result.stderr
    assert not npm_marker.exists(), "build_release_artifact.py must not invoke npm"
