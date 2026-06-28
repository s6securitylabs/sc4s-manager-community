"""TDD tests for runtime_state helpers and build_runtime_state."""
import importlib.util
import json
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RS_PATH = ROOT / "src" / "sc4s_manager" / "runtime_state.py"


def load_rs() -> Any:
    spec = importlib.util.spec_from_file_location("sc4s_manager_runtime_state_test", RS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SAMPLE_STATS_CSV = """\
SourceName;SourceId;SourceInstance;State;Type;Number
source.s_DEFAULT;tcp,0.0.0.0,514;0;a;processed;1234
source.s_DEFAULT;tcp,0.0.0.0,514;0;a;dropped;5
dst.d_hec_DEFAULT;d_hec_DEFAULT;0;a;written;1000
dst.d_hec_DEFAULT;d_hec_DEFAULT;0;a;dropped;2
dst.d_hec_DEFAULT;d_hec_DEFAULT;0;a;queued;10
filter.f_cisco_asa;f_cisco_asa;0;a;matched;50
parser.p_cisco_asa;p_cisco_asa;0;a;processed;50
"""

SAMPLE_SS_OUTPUT = """\
Netid  State   Recv-Q  Send-Q   Local Address:Port    Peer Address:Port
tcp    LISTEN  0       128      0.0.0.0:514            0.0.0.0:*
tcp    LISTEN  0       128      0.0.0.0:8090           0.0.0.0:*
udp    UNCONN  0       0        0.0.0.0:514            0.0.0.0:*
tcp    ESTABLISHED  0  0        10.0.0.1:56789         10.0.0.2:514
"""


class TestParseMetricsToCounters(unittest.TestCase):
    def setUp(self):
        self.rs = load_rs()

    def test_parses_source_processed_row(self):
        counters = self.rs.parse_metrics_to_counters(SAMPLE_STATS_CSV)
        src = [c for c in counters if c["name"] == "source.s_DEFAULT" and c["metric"] == "processed"]
        self.assertEqual(len(src), 1)
        self.assertEqual(src[0]["value"], 1234)
        self.assertEqual(src[0]["component"], "source")

    def test_parses_source_dropped_row(self):
        counters = self.rs.parse_metrics_to_counters(SAMPLE_STATS_CSV)
        src = [c for c in counters if c["name"] == "source.s_DEFAULT" and c["metric"] == "dropped"]
        self.assertEqual(src[0]["value"], 5)

    def test_parses_destination_written_row(self):
        counters = self.rs.parse_metrics_to_counters(SAMPLE_STATS_CSV)
        dst = [c for c in counters if c["name"] == "dst.d_hec_DEFAULT" and c["metric"] == "written"]
        self.assertEqual(dst[0]["value"], 1000)
        self.assertEqual(dst[0]["component"], "destination")

    def test_parses_destination_queued_row(self):
        counters = self.rs.parse_metrics_to_counters(SAMPLE_STATS_CSV)
        dst = [c for c in counters if c["name"] == "dst.d_hec_DEFAULT" and c["metric"] == "queued"]
        self.assertEqual(dst[0]["value"], 10)

    def test_classifies_filter_as_parser_component(self):
        counters = self.rs.parse_metrics_to_counters(SAMPLE_STATS_CSV)
        filt = [c for c in counters if c["name"] == "filter.f_cisco_asa"]
        self.assertTrue(len(filt) > 0)
        self.assertEqual(filt[0]["component"], "parser")

    def test_classifies_parser_as_parser_component(self):
        counters = self.rs.parse_metrics_to_counters(SAMPLE_STATS_CSV)
        parser = [c for c in counters if c["name"] == "parser.p_cisco_asa"]
        self.assertEqual(parser[0]["component"], "parser")

    def test_empty_csv_returns_empty_list(self):
        self.assertEqual(self.rs.parse_metrics_to_counters(""), [])
        self.assertEqual(self.rs.parse_metrics_to_counters("   "), [])

    def test_malformed_number_falls_back_to_zero(self):
        bad = "SourceName;SourceId;SourceInstance;State;Type;Number\nsource.s_foo;foo;0;a;processed;notanumber\n"
        counters = self.rs.parse_metrics_to_counters(bad)
        self.assertEqual(len(counters), 1)
        self.assertEqual(counters[0]["value"], 0)

    def test_hec_token_value_never_appears_in_output(self):
        # Even if somehow a secret value appears in a row, the parser does not
        # add env values; this test documents the boundary explicitly.
        counters = self.rs.parse_metrics_to_counters(SAMPLE_STATS_CSV)
        serialised = json.dumps(counters)
        self.assertNotIn("TOKEN", serialised)
        self.assertNotIn("SECRET", serialised)


class TestClassifyCounterComponent(unittest.TestCase):
    def setUp(self):
        self.rs = load_rs()

    def test_source_prefix_variants(self):
        self.assertEqual(self.rs.classify_counter_component("source.s_DEFAULT"), "source")
        self.assertEqual(self.rs.classify_counter_component("src.udp_514"), "source")
        self.assertEqual(self.rs.classify_counter_component("s_CISCO"), "source")

    def test_destination_prefix_variants(self):
        self.assertEqual(self.rs.classify_counter_component("dst.d_hec_DEFAULT"), "destination")
        self.assertEqual(self.rs.classify_counter_component("d_hec_PROD"), "destination")
        self.assertEqual(self.rs.classify_counter_component("destination.syslog"), "destination")

    def test_parser_and_filter_prefix_variants(self):
        self.assertEqual(self.rs.classify_counter_component("filter.f_cisco"), "parser")
        self.assertEqual(self.rs.classify_counter_component("f_syslog"), "parser")
        self.assertEqual(self.rs.classify_counter_component("parser.p_foo"), "parser")
        self.assertEqual(self.rs.classify_counter_component("p_bar"), "parser")

    def test_unknown_prefix_returns_unknown(self):
        self.assertEqual(self.rs.classify_counter_component("global.something"), "unknown")
        self.assertEqual(self.rs.classify_counter_component("internal.stats"), "unknown")


class TestParseListenersFromSs(unittest.TestCase):
    def setUp(self):
        self.rs = load_rs()

    def test_parses_tcp_listen_row(self):
        rows = self.rs.parse_listeners_from_ss(SAMPLE_SS_OUTPUT)
        tcp_514 = [r for r in rows if r["protocol"] == "tcp" and r["port"] == 514]
        self.assertEqual(len(tcp_514), 1)
        self.assertEqual(tcp_514[0]["bind"], "0.0.0.0")

    def test_parses_udp_unconn_row(self):
        rows = self.rs.parse_listeners_from_ss(SAMPLE_SS_OUTPUT)
        udp_514 = [r for r in rows if r["protocol"] == "udp" and r["port"] == 514]
        self.assertEqual(len(udp_514), 1)

    def test_excludes_established_connections(self):
        rows = self.rs.parse_listeners_from_ss(SAMPLE_SS_OUTPUT)
        # Only LISTEN and UNCONN rows survive; ESTABLISHED is excluded
        self.assertEqual(len(rows), 3)  # tcp:514, tcp:8090, udp:514

    def test_empty_output_returns_empty_list(self):
        self.assertEqual(self.rs.parse_listeners_from_ss(""), [])

    def test_ignores_header_lines(self):
        header_only = "Netid  State   Recv-Q  Send-Q   Local Address:Port    Peer Address:Port\n"
        self.assertEqual(self.rs.parse_listeners_from_ss(header_only), [])


class TestBuildRuntimeState(unittest.TestCase):
    def setUp(self):
        self.rs = load_rs()
        self.base_status = {
            "ok": True,
            "status": {
                "running": True,
                "status": "running",
                "health": "healthy",
                "image": "ghcr.io/splunk/sc4s:3.43.0",
                "image_version": "3.43.0",
            },
        }
        self.base_metrics = {
            "ok": True,
            "stdout": SAMPLE_STATS_CSV,
        }
        self.base_listeners = {
            "ok": True,
            "listeners": [
                {"protocol": "tcp", "port": 514, "bind": "0.0.0.0"},
                {"protocol": "udp", "port": 514, "bind": "0.0.0.0"},
            ],
        }
        self.base_warnings_resp = {
            "ok": True,
            "warnings": [],
            "errors": [],
            "line_count": 0,
        }
        self.base_env = {
            "SC4S_LISTEN_DEFAULT_TCP_PORT": "514",
            "SC4S_LISTEN_DEFAULT_UDP_PORT": "514",
            "SC4S_DEST_SPLUNK_HEC_DEFAULT_URL": "https://splunk.example.com:8088",
            "SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN": "super-secret-hec-token-value",
        }

    def _build(self, **overrides) -> dict:
        kwargs = dict(
            control_status=self.base_status,
            control_metrics=self.base_metrics,
            control_listeners=self.base_listeners,
            control_warnings=self.base_warnings_resp,
            env=self.base_env,
            app_version="0.1.0",
            supported_sc4s_version="3.43.0",
            generated_at="2026-06-14T00:00:00Z",
        )
        kwargs.update(overrides)
        return self.rs.build_runtime_state(**kwargs)

    def test_state_has_all_required_top_level_keys(self):
        state = self._build()
        required = {
            "ok", "generated_at", "manager", "control_daemon", "sc4s",
            "listeners", "counters", "destinations", "warnings", "redaction",
        }
        missing = required - state.keys()
        self.assertEqual(missing, set(), f"Missing keys: {missing}")

    def test_control_daemon_failure_sets_ok_false_without_raising(self):
        state = self._build(
            control_status={"ok": False, "error": "socket not found"},
            control_metrics={"ok": False, "error": "socket not found"},
            control_listeners={"ok": False},
            control_warnings={"ok": False},
        )
        self.assertFalse(state["ok"])
        self.assertFalse(state["control_daemon"]["ok"])
        self.assertIn("error", state["control_daemon"])
        self.assertIn("socket not found", state["control_daemon"]["error"])

    def test_hec_token_value_is_absent_from_output(self):
        state = self._build()
        serialised = json.dumps(state)
        self.assertNotIn("super-secret-hec-token-value", serialised)

    def test_redaction_secrets_present_true_when_token_key_in_env(self):
        state = self._build()
        self.assertTrue(state["redaction"]["secrets_present"])

    def test_redaction_secrets_present_false_when_no_secret_keys(self):
        state = self._build(env={"SC4S_DEST_SPLUNK_HEC_DEFAULT_URL": "https://example.com"})
        self.assertFalse(state["redaction"]["secrets_present"])

    def test_version_drift_triggers_warning_and_flag(self):
        drifted = {
            "ok": True,
            "status": {**self.base_status["status"], "image_version": "3.40.0"},
        }
        state = self._build(control_status=drifted)
        self.assertTrue(state["sc4s"]["version_drift"])
        drift_w = [w for w in state["warnings"] if w["code"] == "version_drift"]
        self.assertEqual(len(drift_w), 1)
        self.assertIn("3.40.0", drift_w[0]["message"])
        self.assertIn("3.43.0", drift_w[0]["message"])

    def test_matched_version_produces_no_version_drift_warning(self):
        state = self._build()
        drift_w = [w for w in state["warnings"] if w["code"] == "version_drift"]
        self.assertEqual(drift_w, [])
        self.assertFalse(state["sc4s"]["version_drift"])

    def test_overall_ok_true_when_running_and_no_errors(self):
        state = self._build()
        self.assertTrue(state["ok"])

    def test_overall_ok_false_when_sc4s_not_running(self):
        stopped = {
            "ok": True,
            "status": {**self.base_status["status"], "running": False, "status": "exited"},
        }
        state = self._build(control_status=stopped)
        self.assertFalse(state["ok"])

    def test_listeners_show_desired_and_live(self):
        state = self._build()
        tcp_514 = next(
            (l for l in state["listeners"] if l["protocol"] == "tcp" and l["port"] == 514),
            None,
        )
        self.assertIsNotNone(tcp_514)
        self.assertTrue(tcp_514["desired"])
        self.assertTrue(tcp_514["live"])

    def test_desired_port_without_live_listener_produces_warning(self):
        # No live listeners at all
        state = self._build(control_listeners={"ok": True, "listeners": []})
        listener_w = [w for w in state["warnings"] if w["code"] == "listener_not_live"]
        self.assertGreater(len(listener_w), 0)
        for w in listener_w:
            self.assertIn("port", w["message"].lower())

    def test_destination_summary_aggregates_written_and_dropped(self):
        state = self._build()
        dests = state["destinations"]
        self.assertGreater(len(dests), 0)
        hec_dest = next(
            (d for d in dests if "hec" in d["id"].lower() or "DEFAULT" in d["id"]),
            None,
        )
        self.assertIsNotNone(hec_dest)
        self.assertEqual(hec_dest["written"], 1000)
        self.assertEqual(hec_dest["dropped"], 2)
        self.assertEqual(hec_dest["queued"], 10)

    def test_sc4s_log_errors_appear_as_error_severity_warnings(self):
        warnings_resp = {
            "ok": True,
            "warnings": [],
            "errors": ["Error: syslog-ng failed to parse message from 10.0.0.1"],
            "line_count": 1,
        }
        state = self._build(control_warnings=warnings_resp)
        log_errors = [w for w in state["warnings"] if w["code"] == "sc4s_log_error"]
        self.assertEqual(len(log_errors), 1)
        self.assertEqual(log_errors[0]["severity"], "error")

    def test_sc4s_log_warnings_appear_as_warning_severity(self):
        warnings_resp = {
            "ok": True,
            "warnings": ["Warning: stats queue filling up"],
            "errors": [],
            "line_count": 1,
        }
        state = self._build(control_warnings=warnings_resp)
        log_w = [w for w in state["warnings"] if w["code"] == "sc4s_log_warning"]
        self.assertEqual(len(log_w), 1)
        self.assertEqual(log_w[0]["severity"], "warning")

    def test_log_error_makes_overall_ok_false(self):
        warnings_resp = {
            "ok": True,
            "warnings": [],
            "errors": ["Fatal: syslog-ng crashed"],
            "line_count": 1,
        }
        state = self._build(control_warnings=warnings_resp)
        self.assertFalse(state["ok"])

    def test_generated_at_is_preserved_in_output(self):
        state = self._build()
        self.assertEqual(state["generated_at"], "2026-06-14T00:00:00Z")

    def test_manager_version_is_set(self):
        state = self._build()
        self.assertEqual(state["manager"]["version"], "0.1.0")

    def test_counters_list_populated_from_metrics(self):
        state = self._build()
        self.assertGreater(len(state["counters"]), 0)
        # Verify each counter has required fields
        for c in state["counters"]:
            self.assertIn("name", c)
            self.assertIn("component", c)
            self.assertIn("metric", c)
            self.assertIn("value", c)
            self.assertIn(c["component"], {"source", "parser", "destination", "unknown"})

    def test_no_desired_ports_produces_no_listener_entries(self):
        state = self._build(env={})
        # With no port env vars, no desired listeners → only live ones should appear
        desired_only = [l for l in state["listeners"] if l["desired"]]
        self.assertEqual(desired_only, [])

    def test_live_listeners_without_desired_appear_as_undesired(self):
        # Live listener on port 9999 not in env → desired=False, live=True
        state = self._build(
            env={},  # no desired ports
            control_listeners={
                "ok": True,
                "listeners": [{"protocol": "tcp", "port": 9999, "bind": "0.0.0.0"}],
            },
        )
        tcp_9999 = next((l for l in state["listeners"] if l["port"] == 9999), None)
        self.assertIsNotNone(tcp_9999)
        self.assertFalse(tcp_9999["desired"])
        self.assertTrue(tcp_9999["live"])


if __name__ == "__main__":
    unittest.main()
