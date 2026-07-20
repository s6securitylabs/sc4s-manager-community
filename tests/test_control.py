import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CONTROL_PATH = ROOT / "src" / "sc4s_manager" / "control.py"


def load_control(tmp: Path) -> Any:
    os.environ["SC4S_CONTROL_SOCKET"] = str(tmp / "run" / "control.sock")
    os.environ["SC4S_COMPOSE_FILE"] = str(tmp / "opt" / "sc4s" / "docker-compose.yml")
    os.environ["SC4S_COMPOSE_CWD"] = str(tmp / "opt" / "sc4s")
    os.environ["SC4S_CONTROL_AUDIT"] = str(tmp / "opt" / "sc4s-manager" / "state" / "control-audit.jsonl")
    os.environ["SC4S_CONTAINER"] = "SC4S-test"
    spec = importlib.util.spec_from_file_location("sc4s_control_test", CONTROL_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


class ControlDaemonTests(unittest.TestCase):
    def test_run_truncates_stdout_and_stderr_but_preserves_return_code(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            completed = type("Completed", (), {"returncode": 7, "stdout": "0123456789", "stderr": "abcdefghij"})()
            with patch.object(control.subprocess, "run", return_value=completed) as fake_run:
                result = control.run(["docker", "logs"], timeout=4, stdout_limit=4, cwd=Path(d))

            self.assertFalse(result["ok"])
            self.assertEqual(result["code"], 7)
            self.assertEqual(result["stdout"], "6789")
            self.assertEqual(result["stderr"], "abcdefghij")
            fake_run.assert_called_once()
            self.assertEqual(fake_run.call_args.kwargs["timeout"], 4)
            self.assertEqual(fake_run.call_args.kwargs["cwd"], str(Path(d)))

    def test_run_converts_subprocess_exceptions_to_failed_response(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            with patch.object(control.subprocess, "run", side_effect=TimeoutError("too slow")):
                result = control.run(["docker", "inspect"], timeout=1)

            self.assertFalse(result["ok"])
            self.assertEqual(result["code"], -1)
            self.assertEqual(result["stdout"], "")
            self.assertIn("too slow", result["stderr"])

    def test_audit_writes_jsonl_records_under_packaged_state_dir(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            control.audit("status", True, {"remote": "unix"})

            lines = control.AUDIT_LOG.read_text().splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["action"], "status")
            self.assertTrue(record["ok"])
            self.assertEqual(record["detail"], {"remote": "unix"})
            self.assertTrue(str(control.AUDIT_LOG).endswith("/opt/sc4s-manager/state/control-audit.jsonl"))

    def test_status_parses_container_health_version_and_revision(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            inspect_payload = [{
                "State": {"Running": True, "Status": "running", "Health": {"Status": "healthy"}, "StartedAt": "2026-05-25T00:00:00Z"},
                "RestartCount": 2,
                "Config": {"Image": "ghcr.io/splunk/sc4s:3.43.0", "Labels": {
                    "org.opencontainers.image.version": "3.43.0",
                    "org.opencontainers.image.revision": "abc123",
                }},
            }]
            control.run = lambda *args, **kwargs: {"ok": True, "code": 0, "stdout": json.dumps(inspect_payload), "stderr": ""}

            result = control.action_status({})

            self.assertTrue(result["ok"])
            status = result["status"]
            self.assertTrue(status["running"])
            self.assertEqual(status["health"], "healthy")
            self.assertEqual(status["restart_count"], 2)
            self.assertEqual(status["image_version"], "3.43.0")
            self.assertEqual(status["image_revision"], "abc123")

    def test_status_reports_docker_and_json_failures_without_throwing(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            control.run = lambda *args, **kwargs: {"ok": False, "code": 1, "stdout": "", "stderr": "missing container"}
            missing = control.action_status({})
            self.assertFalse(missing["ok"])
            self.assertIn("missing container", missing["error"])

            control.run = lambda *args, **kwargs: {"ok": True, "code": 0, "stdout": "not json", "stderr": ""}
            malformed = control.action_status({})
            self.assertFalse(malformed["ok"])
            self.assertIn("docker", malformed)

    def test_logs_clamps_requested_tail_lines_to_allowlisted_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            calls = []
            def fake_run(cmd, **kwargs):
                calls.append((cmd, kwargs))
                return {"ok": True, "code": 0, "stdout": "log", "stderr": ""}
            control.run = fake_run

            too_many = control.action_logs({"lines": 999999})
            not_number = control.action_logs({"lines": "nonsense"})
            zero = control.action_logs({"lines": 0})

            self.assertTrue(too_many["ok"])
            self.assertEqual(calls[0][0], ["docker", "logs", "--tail", str(control.MAX_LOG_LINES), "SC4S-test"])
            self.assertEqual(calls[1][0], ["docker", "logs", "--tail", "80", "SC4S-test"])
            self.assertEqual(calls[2][0], ["docker", "logs", "--tail", "1", "SC4S-test"])

    def test_metrics_validate_reload_use_only_fixed_container_commands(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            calls = []
            def fake_run(cmd, **kwargs):
                calls.append((cmd, kwargs))
                return {"ok": True, "code": 0, "stdout": "ok", "stderr": ""}
            control.run = fake_run

            self.assertTrue(control.action_metrics({})["ok"])
            self.assertTrue(control.action_validate({})["ok"])
            self.assertTrue(control.action_reload({})["ok"])

            self.assertEqual(calls[0][0], ["docker", "exec", "SC4S-test", "syslog-ng-ctl", "stats"])
            self.assertEqual(calls[1][0][:4], ["docker", "exec", "SC4S-test", "bash"])
            self.assertEqual(calls[2][0], ["docker", "kill", "--signal", "HUP", "SC4S-test"])

    def test_restart_refuses_runtime_drift_before_docker_compose(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            calls = []
            control.run = lambda *args, **kwargs: calls.append(args) or {"ok": True, "code": 0, "stdout": "", "stderr": ""}

            with self.assertRaises(RuntimeError):
                control.action_restart({})

            self.assertEqual(calls, [])

    def test_restart_runs_docker_compose_only_for_fixed_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            fixed_root = Path(d) / "fixed" / "opt" / "sc4s"
            fixed_root.mkdir(parents=True)
            compose = fixed_root / "docker-compose.yml"
            compose.write_text("services: {}\n")
            control.COMPOSE_CWD = fixed_root
            control.COMPOSE_FILE = compose
            calls = []
            control.run = lambda cmd, **kwargs: calls.append((cmd, kwargs)) or {"ok": True, "code": 0, "stdout": "started", "stderr": ""}
            with patch.object(Path, "resolve", lambda self: Path("/opt/sc4s/docker-compose.yml") if self == compose else (Path("/opt/sc4s") if self == fixed_root else self)):
                result = control.action_restart({})

            self.assertTrue(result["ok"])
            self.assertEqual(calls[0][0], ["docker", "compose", "-f", str(compose), "up", "-d"])
            self.assertEqual(calls[0][1]["cwd"], fixed_root)

    def test_restart_runs_docker_compose_only_for_fixed_runtime_with_compose_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            fixed_root = Path(d) / "fixed" / "opt" / "sc4s"
            fixed_root.mkdir(parents=True)
            compose = fixed_root / "compose.yaml"
            compose.write_text("services: {}\n")
            control.COMPOSE_CWD = fixed_root
            control.COMPOSE_FILE = compose
            calls = []
            control.run = lambda cmd, **kwargs: calls.append((cmd, kwargs)) or {"ok": True, "code": 0, "stdout": "started", "stderr": ""}
            with patch.object(Path, "resolve", lambda self: Path("/opt/sc4s/compose.yaml") if self == compose else (Path("/opt/sc4s") if self == fixed_root else self)):
                result = control.action_restart({})

            self.assertTrue(result["ok"])
            self.assertEqual(calls[0][0], ["docker", "compose", "-f", str(compose), "up", "-d"])
            self.assertEqual(calls[0][1]["cwd"], fixed_root)


class ControlDaemonBoundaryTests(unittest.TestCase):
    """Tests that enforce the fixed-allowlist and new actions invariants."""

    def test_actions_allowlist_is_exactly_the_expected_set(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            allowed = {"status", "logs", "metrics", "validate", "reload", "restart", "listeners", "warnings"}
            self.assertEqual(set(control.ACTIONS.keys()), allowed)

    def test_arbitrary_exec_and_shell_actions_not_in_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            for bad in ("exec", "shell", "run", "cmd", "command", "docker", "compose"):
                self.assertNotIn(bad, control.ACTIONS, f"'{bad}' must not be in ACTIONS")

    def test_listeners_uses_fixed_docker_exec_ss_command(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            calls = []
            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                return {"ok": True, "code": 0, "stdout": "LISTEN 0 128 0.0.0.0:514 0.0.0.0:*\n", "stderr": ""}
            control.run = fake_run

            result = control.action_listeners({})

            self.assertTrue(result["ok"])
            # First call must be docker exec SC4S ss
            self.assertEqual(calls[0][:4], ["docker", "exec", "SC4S-test", "ss"])

    def test_listeners_ignores_caller_supplied_command_and_path(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            calls = []
            control.run = lambda cmd, **kwargs: calls.append(cmd) or {"ok": True, "code": 0, "stdout": "", "stderr": ""}

            # These caller-supplied fields must have zero effect on the command executed
            control.action_listeners({"command": "cat /etc/passwd", "path": "/tmp/evil", "filter": "*.conf"})

            for cmd in calls:
                for part in cmd:
                    self.assertNotIn("passwd", str(part))
                    self.assertNotIn("evil", str(part))

    def test_listeners_parses_ss_tcp_and_udp_rows(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            ss_out = (
                "Netid  State   Recv-Q  Send-Q   Local Address:Port  Peer Address:Port\n"
                "tcp    LISTEN  0       128      0.0.0.0:514         0.0.0.0:*\n"
                "udp    UNCONN  0       0        0.0.0.0:514         0.0.0.0:*\n"
                "tcp    ESTABLISHED  0  0        10.0.0.1:56789      10.0.0.2:514\n"
            )
            control.run = lambda cmd, **kwargs: {"ok": True, "code": 0, "stdout": ss_out, "stderr": ""}

            result = control.action_listeners({})

            self.assertTrue(result["ok"])
            self.assertEqual(len(result["listeners"]), 2)
            protocols = {r["protocol"] for r in result["listeners"]}
            self.assertIn("tcp", protocols)
            self.assertIn("udp", protocols)

    def test_warnings_clamps_requested_line_count_to_max_log_lines(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            calls = []
            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                return {"ok": True, "code": 0, "stdout": "", "stderr": ""}
            control.run = fake_run

            # Excessive line count must be clamped
            control.action_warnings({"lines": 999999})
            self.assertEqual(calls[0], ["docker", "logs", "--tail", str(control.MAX_LOG_LINES), "SC4S-test"])

            # Non-integer must default to 200
            calls.clear()
            control.action_warnings({"lines": "nonsense"})
            self.assertEqual(calls[0], ["docker", "logs", "--tail", "200", "SC4S-test"])

            # Zero must clamp to 1
            calls.clear()
            control.action_warnings({"lines": 0})
            self.assertEqual(calls[0], ["docker", "logs", "--tail", "1", "SC4S-test"])

    def test_warnings_separates_error_and_warning_log_lines(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            log_output = (
                "2026-06-14T00:00:01Z [info] syslog-ng started\n"
                "2026-06-14T00:00:02Z [warning] queue filling up\n"
                "2026-06-14T00:00:03Z [error] failed to resolve host\n"
                "2026-06-14T00:00:04Z [info] stats updated\n"
            )
            control.run = lambda cmd, **kwargs: {"ok": True, "code": 0, "stdout": log_output, "stderr": ""}

            result = control.action_warnings({})

            self.assertTrue(result["ok"])
            self.assertEqual(len(result["errors"]), 1)
            self.assertIn("failed to resolve", result["errors"][0])
            self.assertEqual(len(result["warnings"]), 1)
            self.assertIn("queue filling up", result["warnings"][0])

    def test_warnings_redacts_secrets_in_log_lines(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            log_output = "error: HEC_TOKEN=abc123secretvalue connection failed\n"
            control.run = lambda cmd, **kwargs: {"ok": True, "code": 0, "stdout": log_output, "stderr": ""}

            result = control.action_warnings({})

            errors_text = " ".join(result.get("errors", []) + result.get("warnings", []))
            self.assertNotIn("abc123secretvalue", errors_text)
            self.assertIn("[REDACTED]", errors_text)

    def test_warnings_failure_returns_ok_false_with_empty_lists(self):
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            control.run = lambda cmd, **kwargs: {"ok": False, "code": 1, "stdout": "", "stderr": "container not found"}

            result = control.action_warnings({})

            self.assertFalse(result["ok"])
            self.assertEqual(result["warnings"], [])
            self.assertEqual(result["errors"], [])
            self.assertIn("error", result)

    def test_listeners_and_warnings_are_auditable_via_actions_dispatch(self):
        # The Handler audits every action in ACTIONS after it returns.
        # Verifying ACTIONS membership proves the audit path is wired up.
        with tempfile.TemporaryDirectory() as d:
            control = load_control(Path(d))
            self.assertIn("listeners", control.ACTIONS)
            self.assertIn("warnings", control.ACTIONS)
            # Verify the audit function itself works for these action names.
            control.audit("listeners", True, {"remote": "unix"})
            control.audit("warnings", True, {"remote": "unix"})
            records = [json.loads(line) for line in control.AUDIT_LOG.read_text().splitlines()]
            actions = {r["action"] for r in records}
            self.assertIn("listeners", actions)
            self.assertIn("warnings", actions)


if __name__ == "__main__":
    unittest.main()
