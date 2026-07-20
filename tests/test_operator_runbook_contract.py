from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_operator_runbooks_state_real_compose_and_lifecycle_boundaries():
    install = read("docs/runbooks/install.md")
    upgrade = read("docs/runbooks/upgrade.md")
    rollback = read("docs/runbooks/rollback.md")
    drill = read("docs/runbooks/install-upgrade-rollback-drill.md")
    architecture = read("docs/architecture.md")

    for text in (upgrade, rollback, drill):
        assert "dry-run" in text
    assert "planners only" in install
    assert "does **not** provide a control daemon" in install
    assert "does not consume systemd's passed socket" in install
    assert "--execute`, `--apply`, and `--rollback` are rejected" in install
    assert "does not perform this upgrade" in upgrade
    assert "has no rollback mode" in rollback
    assert "prior drill command using those flags is invalid" in drill
    assert "does not make control daemon functionality exist inside the Docker-only deployment" in architecture


def test_install_runbook_covers_permissions_selinux_auth_and_verification():
    install = read("docs/runbooks/install.md")

    for required in (
        "UID/GID `10001`",
        "SELinux",
        "X-SC4S-Manager-Proxy",
        "X-Authentik-Groups",
        "docker compose -f compose.yaml config -q",
        "http://127.0.0.1:8090/health",
        "http://127.0.0.1:8080/health",
        "Abort if either service repeatedly restarts",
    ):
        assert required in install


def test_runbooks_do_not_advertise_rejected_execute_or_rollback_commands_as_workflows():
    for path in (
        "README.md",
        "docs/runbooks/install.md",
        "docs/runbooks/upgrade.md",
        "docs/runbooks/rollback.md",
        "docs/runbooks/install-upgrade-rollback-drill.md",
    ):
        text = read(path)
        assert "sudo bash deploy/install/install.sh --execute" not in text, path
        assert "sudo bash deploy/upgrade/upgrade.sh --artifact" not in text, path
        assert "deploy/install/install.sh --rollback" not in text, path
