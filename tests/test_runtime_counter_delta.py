"""Tests for capture_runtime_counter_delta.py — dry-run only (no live SC4S)."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "capture_runtime_counter_delta.py"
FIXTURES = ROOT / "tests" / "fixtures"


def load_script() -> Any:
    spec = importlib.util.spec_from_file_location("capture_runtime_counter_delta_test", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BEFORE_STATE = {
    "ok": True,
    "generated_at": "2026-06-14T00:00:00Z",
    "counters": [
        {"name": "source.s_DEFAULT", "component": "source", "metric": "processed", "value": 1000},
        {"name": "dst.d_hec_DEFAULT", "component": "destination", "metric": "written", "value": 950},
        {"name": "dst.d_hec_DEFAULT", "component": "destination", "metric": "dropped", "value": 2},
    ],
    "warnings": [],
}

AFTER_STATE = {
    "ok": True,
    "generated_at": "2026-06-14T00:00:10Z",
    "counters": [
        {"name": "source.s_DEFAULT", "component": "source", "metric": "processed", "value": 1003},
        {"name": "dst.d_hec_DEFAULT", "component": "destination", "metric": "written", "value": 953},
        {"name": "dst.d_hec_DEFAULT", "component": "destination", "metric": "dropped", "value": 2},
    ],
    "warnings": [],
}


class TestCounterMap(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_builds_flat_key_value_map(self):
        m = self.script.counter_map(BEFORE_STATE)
        self.assertEqual(m["source.s_DEFAULT:processed"], 1000)
        self.assertEqual(m["dst.d_hec_DEFAULT:written"], 950)

    def test_empty_counters_returns_empty_map(self):
        m = self.script.counter_map({"ok": True, "counters": []})
        self.assertEqual(m, {})

    def test_missing_counters_key_returns_empty_map(self):
        m = self.script.counter_map({"ok": True})
        self.assertEqual(m, {})


class TestComputeDelta(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_detects_positive_delta_in_processed_counter(self):
        deltas = self.script.compute_delta(BEFORE_STATE, AFTER_STATE)
        proc = next((d for d in deltas if d["counter"] == "source.s_DEFAULT" and d["metric"] == "processed"), None)
        self.assertIsNotNone(proc)
        self.assertEqual(proc["before"], 1000)
        self.assertEqual(proc["after"], 1003)
        self.assertEqual(proc["delta"], 3)

    def test_detects_positive_delta_in_written_counter(self):
        deltas = self.script.compute_delta(BEFORE_STATE, AFTER_STATE)
        written = next((d for d in deltas if d["counter"] == "dst.d_hec_DEFAULT" and d["metric"] == "written"), None)
        self.assertIsNotNone(written)
        self.assertEqual(written["delta"], 3)

    def test_unchanged_counters_not_in_delta(self):
        deltas = self.script.compute_delta(BEFORE_STATE, AFTER_STATE)
        dropped = [d for d in deltas if d["counter"] == "dst.d_hec_DEFAULT" and d["metric"] == "dropped"]
        # dropped stayed at 2 → should not appear in delta
        self.assertEqual(dropped, [])

    def test_no_changes_returns_empty_delta(self):
        deltas = self.script.compute_delta(BEFORE_STATE, BEFORE_STATE)
        self.assertEqual(deltas, [])

    def test_new_counter_in_after_appears_as_positive_delta(self):
        after_with_new = {
            **AFTER_STATE,
            "counters": AFTER_STATE["counters"] + [
                {"name": "source.s_CISCO", "component": "source", "metric": "processed", "value": 5},
            ],
        }
        deltas = self.script.compute_delta(BEFORE_STATE, after_with_new)
        new = next((d for d in deltas if d["counter"] == "source.s_CISCO"), None)
        self.assertIsNotNone(new)
        self.assertEqual(new["before"], 0)
        self.assertEqual(new["after"], 5)

    def test_counter_disappearing_in_after_appears_as_negative_delta(self):
        after_without = {
            **BEFORE_STATE,
            "counters": [c for c in BEFORE_STATE["counters"] if c["metric"] != "dropped"],
        }
        deltas = self.script.compute_delta(BEFORE_STATE, after_without)
        gone = next((d for d in deltas if d["metric"] == "dropped"), None)
        self.assertIsNotNone(gone)
        self.assertEqual(gone["delta"], -2)


class TestBuildEvidence(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_evidence_has_required_fields(self):
        ev = self.script.build_evidence(
            before=BEFORE_STATE,
            after=AFTER_STATE,
            marker_command=None,
            api_url="http://127.0.0.1:8090",
            dry_run=True,
            elapsed_s=0.5,
        )
        required = {"ok", "dry_run", "api_url", "marker_command", "before", "after", "delta", "delta_count", "elapsed_s", "evidence_note"}
        missing = required - ev.keys()
        self.assertEqual(missing, set(), f"Missing keys: {missing}")

    def test_dry_run_flag_preserved_in_evidence(self):
        ev = self.script.build_evidence(BEFORE_STATE, AFTER_STATE, None, "http://localhost:8090", True, 0.1)
        self.assertTrue(ev["dry_run"])

    def test_api_url_with_token_is_redacted(self):
        ev = self.script.build_evidence(
            BEFORE_STATE, AFTER_STATE, None,
            "http://localhost:8090?token=supersecret123", True, 0.1,
        )
        self.assertNotIn("supersecret123", ev["api_url"])
        self.assertIn("[REDACTED]", ev["api_url"])

    def test_delta_count_matches_delta_list_length(self):
        ev = self.script.build_evidence(BEFORE_STATE, AFTER_STATE, None, "http://localhost", True, 0.1)
        self.assertEqual(ev["delta_count"], len(ev["delta"]))

    def test_ok_true_when_both_snapshots_ok(self):
        ev = self.script.build_evidence(BEFORE_STATE, AFTER_STATE, None, "http://localhost", True, 0.1)
        self.assertTrue(ev["ok"])

    def test_ok_false_when_before_snapshot_not_ok(self):
        bad_before = {**BEFORE_STATE, "ok": False}
        ev = self.script.build_evidence(bad_before, AFTER_STATE, None, "http://localhost", True, 0.1)
        self.assertFalse(ev["ok"])

    def test_evidence_note_present_and_non_trivial(self):
        ev = self.script.build_evidence(BEFORE_STATE, AFTER_STATE, None, "http://localhost", True, 0.1)
        self.assertIn("Splunk", ev["evidence_note"])
        self.assertGreater(len(ev["evidence_note"]), 20)


class TestDryRunScript(unittest.TestCase):
    """Integration-level dry-run: call the script via its main() with fixture files."""

    def test_dry_run_with_fixtures_produces_valid_evidence_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "evidence.json"
            saved_argv = sys.argv[:]
            try:
                sys.argv = [
                    "capture_runtime_counter_delta.py",
                    "--dry-run",
                    "--before-fixture", str(FIXTURES / "runtime_state_before.json"),
                    "--after-fixture", str(FIXTURES / "runtime_state_after.json"),
                    "--evidence-out", str(out),
                ]
                script = load_script()
                rc = script.main()
            finally:
                sys.argv = saved_argv

            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())
            ev = json.loads(out.read_text())
            self.assertTrue(ev["ok"])
            self.assertTrue(ev["dry_run"])
            self.assertGreater(ev["delta_count"], 0)
            # processed and written should have changed (+3 each in fixtures)
            proc_delta = next(
                (d for d in ev["delta"] if d["counter"] == "source.s_DEFAULT" and d["metric"] == "processed"),
                None,
            )
            self.assertIsNotNone(proc_delta)
            self.assertEqual(proc_delta["delta"], 3)

    def test_dry_run_fails_without_fixtures(self):
        saved_argv = sys.argv[:]
        try:
            sys.argv = ["capture_runtime_counter_delta.py", "--dry-run"]
            script = load_script()
            rc = script.main()
        finally:
            sys.argv = saved_argv
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
