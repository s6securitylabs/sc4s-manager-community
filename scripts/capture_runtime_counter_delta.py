#!/usr/bin/env python3
"""Capture before/after runtime counter evidence around a marker event.

Dry-run mode (--dry-run) uses fixture JSON files only and never hits live
SC4S or sends any events. Live mode requires a running SC4S Manager instance.

Usage:
  # Dry-run (CI safe):
  python3 scripts/capture_runtime_counter_delta.py \\
      --dry-run \\
      --before-fixture tests/fixtures/runtime_state_before.json \\
      --after-fixture tests/fixtures/runtime_state_after.json \\
      --evidence-out /tmp/counter-delta.json

  # Live (requires running SC4S Manager):
  python3 scripts/capture_runtime_counter_delta.py \\
      --api-url http://127.0.0.1:8090 \\
      --marker-command "logger -n 127.0.0.1 -P 514 -t SC4S_MARKER 'TEST_EVENT'" \\
      --evidence-out docs/acceptance/counter-delta-TIMESTAMP.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def fetch_runtime_state(api_url: str, token: str | None = None) -> dict[str, Any]:
    url = api_url.rstrip("/") + "/api/runtime/state"
    req = urllib.request.Request(url)
    if token:
        req.add_header("X-SC4S-Manager-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"ok": False, "error": str(e), "generated_at": None, "counters": [], "warnings": []}


def counter_map(state: dict[str, Any]) -> dict[str, int]:
    """Build a flat {name:metric → value} map from a runtime state."""
    return {
        f"{c['name']}:{c['metric']}": int(c.get("value", 0))
        for c in state.get("counters", [])
    }


def compute_delta(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return rows where the counter value changed between snapshots."""
    b_map = counter_map(before)
    a_map = counter_map(after)
    all_keys = sorted(set(b_map) | set(a_map))
    deltas = []
    for key in all_keys:
        b_val = b_map.get(key, 0)
        a_val = a_map.get(key, 0)
        diff = a_val - b_val
        if diff != 0:
            name, _, metric = key.partition(":")
            deltas.append({
                "counter": name,
                "metric": metric,
                "before": b_val,
                "after": a_val,
                "delta": diff,
            })
    return deltas


def redact_url(url: str) -> str:
    """Strip credentials and tokens from URLs."""
    import re
    return re.sub(r"(token|key|secret|password|auth)=[^&\s]+", r"\1=[REDACTED]", url, flags=re.I)


def build_evidence(
    before: dict[str, Any],
    after: dict[str, Any],
    marker_command: str | None,
    api_url: str,
    dry_run: bool,
    elapsed_s: float,
) -> dict[str, Any]:
    deltas = compute_delta(before, after)
    return {
        "ok": bool(before.get("ok") and after.get("ok")),
        "dry_run": dry_run,
        "api_url": redact_url(api_url),
        "marker_command": marker_command or "dry-run/fixture",
        "before": {
            "generated_at": before.get("generated_at"),
            "sc4s_ok": before.get("ok"),
            "counter_count": len(before.get("counters", [])),
        },
        "after": {
            "generated_at": after.get("generated_at"),
            "sc4s_ok": after.get("ok"),
            "counter_count": len(after.get("counters", [])),
        },
        "delta": deltas,
        "delta_count": len(deltas),
        "elapsed_s": round(elapsed_s, 2),
        "evidence_note": (
            "Counter delta evidence only. Splunk readback and marker search are "
            "required to prove end-to-end ingestion."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture runtime counter delta evidence")
    parser.add_argument("--api-url", default="http://127.0.0.1:8090", help="SC4S Manager API URL")
    parser.add_argument("--api-token", default="", help="X-SC4S-Manager-Token for local auth")
    parser.add_argument("--marker-command", default="", help="Shell command to send marker event (live mode)")
    parser.add_argument("--wait-s", type=float, default=5.0, help="Seconds to wait after marker before after-snapshot")
    parser.add_argument("--dry-run", action="store_true", help="Use fixture JSON, do not call live API or send events")
    parser.add_argument("--before-fixture", default="", help="Path to before-state fixture JSON (dry-run)")
    parser.add_argument("--after-fixture", default="", help="Path to after-state fixture JSON (dry-run)")
    parser.add_argument("--evidence-out", default="", help="Path to write evidence JSON")
    args = parser.parse_args()

    t0 = time.monotonic()

    if args.dry_run:
        if not args.before_fixture or not args.after_fixture:
            print("ERROR: --dry-run requires --before-fixture and --after-fixture", file=sys.stderr)
            return 2
        before = json.loads(Path(args.before_fixture).read_text())
        after = json.loads(Path(args.after_fixture).read_text())
        marker_cmd = None
    else:
        token = args.api_token or None
        print(f"GET before-snapshot from {args.api_url}/api/runtime/state …")
        before = fetch_runtime_state(args.api_url, token)
        if not before.get("ok"):
            print(f"WARNING: before-snapshot not ok: {before.get('error', 'unknown')}", file=sys.stderr)

        if args.marker_command:
            print(f"Sending marker: {args.marker_command}")
            result = subprocess.run(args.marker_command, shell=True, timeout=30)
            if result.returncode != 0:
                print(f"WARNING: marker command exited {result.returncode}", file=sys.stderr)
        else:
            print("WARNING: no --marker-command supplied; taking immediate after-snapshot", file=sys.stderr)

        if args.wait_s > 0:
            print(f"Waiting {args.wait_s}s for SC4S to process …")
            time.sleep(args.wait_s)

        print(f"GET after-snapshot from {args.api_url}/api/runtime/state …")
        after = fetch_runtime_state(args.api_url, token)
        if not after.get("ok"):
            print(f"WARNING: after-snapshot not ok: {after.get('error', 'unknown')}", file=sys.stderr)
        marker_cmd = args.marker_command or None

    elapsed = time.monotonic() - t0
    evidence = build_evidence(before, after, marker_cmd, args.api_url, args.dry_run, elapsed)

    output = json.dumps(evidence, indent=2, sort_keys=True)
    if args.evidence_out:
        out_path = Path(args.evidence_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n")
        print(f"Evidence written to {args.evidence_out}")
    else:
        print(output)

    if evidence["delta_count"] > 0:
        print(f"\nDelta: {evidence['delta_count']} counter(s) changed")
        for row in evidence["delta"]:
            print(f"  {row['counter']}:{row['metric']}  {row['before']} → {row['after']}  (Δ{row['delta']:+d})")
    else:
        print("\nNo counter changes detected (SC4S may need time to update stats)")

    return 0 if evidence["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
