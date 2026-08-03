import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_preflight():
    spec = importlib.util.spec_from_file_location("preflight", ROOT / "scripts" / "preflight.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_layout(root: Path, mode: str = "standalone", token: str = "a" * 32, version: str = "1.0.1"):
    for rel in ("manager/state", "manager/backups", "manager/templates", "local", "tls", "archive", "env"):
        path = root / rel
        path.mkdir(parents=True, exist_ok=True)
        # Preflight validates container UID 10001 writability via ownership/world-write.
        path.chmod(0o777)
    (root / "compose.yaml").write_text("services: {}\n")
    env_file = root / "env" / "env_file"
    env_file.write_text("SC4S_DEST_SPLUNK_HEC_DEFAULT_URL=https://splunk:8088\nSC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN=test-fixture-token\n")
    env_file.chmod(0o666)
    (root / "env_file").symlink_to("env/env_file")
    (root / ".env").write_text(f"SC4S_MANAGER_VERSION={version}\n")
    manual = token if mode == "standalone" else ""
    proxy = token if mode == "proxy" else ""
    (root / "manager.env").write_text(
        f"SC4S_MANAGER_AUTH_MODE={mode}\nSC4S_MANAGER_MANUAL_LOGIN_TOKEN={manual}\nSC4S_MANAGER_PROXY_SECRET={proxy}\n"
    )


def test_preflight_accepts_complete_offline_standalone_layout(tmp_path):
    preflight = load_preflight()
    write_layout(tmp_path)
    report = preflight.run_preflight(tmp_path, offline=True)
    assert report["ok"] is True


def test_preflight_rejects_missing_auth_choice_and_latest(tmp_path):
    preflight = load_preflight()
    write_layout(tmp_path, mode="", token="change-me", version="latest")
    report = preflight.run_preflight(tmp_path, offline=True)
    failed = {item["name"] for item in report["checks"] if not item["ok"]}
    assert {"auth", "manager_version"} <= failed


def test_preflight_allows_docker_socket_safety_comment_but_rejects_mount(tmp_path):
    preflight = load_preflight()
    write_layout(tmp_path)
    compose = tmp_path / "compose.yaml"
    compose.write_text("# Never mount /var/run/docker.sock\nservices: {}\n")
    report = preflight.run_preflight(tmp_path, offline=True)
    assert next(item for item in report["checks"] if item["name"] == "docker_socket")["ok"] is True

    compose.write_text("services:\n  manager:\n    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock\n")
    report = preflight.run_preflight(tmp_path, offline=True)
    assert next(item for item in report["checks"] if item["name"] == "docker_socket")["ok"] is False

def test_preflight_control_socket_message_is_not_false_assurance(tmp_path):
    preflight = load_preflight()
    write_layout(tmp_path)
    report = preflight.run_preflight(tmp_path, offline=True)
    control = next(item for item in report["checks"] if item["name"] == "control")
    assert control["ok"] is True
    assert "observe_only" in control["detail"] or "/run/sc4s-manager" in control["detail"]


def test_preflight_rejects_paths_not_writable_for_container_uid(tmp_path):
    preflight = load_preflight()
    write_layout(tmp_path)
    locked = tmp_path / "manager" / "state"
    locked.chmod(0o700)
    report = preflight.run_preflight(tmp_path, offline=True)
    writability = next(item for item in report["checks"] if item["name"] == "writability")
    # When not running as UID 10001/root-owned 10001, world-write/ownership gate applies.
    if locked.stat().st_uid != 10001:
        assert writability["ok"] is False
        assert "UID 10001" in writability["detail"] or "10001" in writability["action"]

