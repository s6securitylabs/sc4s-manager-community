#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.pack_validation import (
    default_validation_evidence_dir,
    format_validation_text,
    validate_packs_bundle,
)
from sc4s_manager.packs import load_packs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SC4S Manager packs and emit evidence bundles.")
    parser.add_argument("--pack-id", help="Validate a single pack by id.")
    parser.add_argument(
        "--packs-root",
        default=str(ROOT / "packs"),
        help="Packs root directory. Default: %(default)s",
    )
    parser.add_argument(
        "--evidence-dir",
        default=os.environ.get("SC4S_MANAGER_VALIDATION_EVIDENCE_DIR") or str(default_validation_evidence_dir()),
        help="Directory for JSON/Markdown evidence bundles. Default: %(default)s",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Stdout format. Default: %(default)s",
    )
    parser.add_argument(
        "--syslog-ng-validate-cmd",
        default=os.environ.get("SC4S_MANAGER_SYSLOG_NG_VALIDATE_CMD"),
        help="Optional external runtime syntax command. Supports {pack_dir}, {pack_id}, and {files_json} placeholders.",
    )
    parser.add_argument("--release-mode", action="store_true", help="Require runtime syslog-ng, event injection, and Splunk read-back proof.")
    parser.add_argument(
        "--runtime-root",
        default=os.environ.get("SC4S_MANAGER_RUNTIME_ROOT"),
        help="Optional staging/install root for export artifacts before runtime validation.",
    )
    parser.add_argument(
        "--runtime-send-cmd",
        default=os.environ.get("SC4S_MANAGER_RUNTIME_SEND_CMD"),
        help="Optional external event-injection command. Supports {pack_dir}, {runtime_root}, {pack_id}, {event_set_id}, {payload_path}, {marker}, {listener_host}, {transport}, {port}, {source_id}, and {event_count} placeholders.",
    )
    parser.add_argument(
        "--splunk-search-cmd",
        default=os.environ.get("SC4S_MANAGER_SPLUNK_SEARCH_CMD"),
        help="Optional external Splunk search command. Supports {pack_id}, {family_id}, {search_name}, {search}, {marker}, and {runtime_root} placeholders.",
    )
    parser.add_argument(
        "--listener-host",
        default=os.environ.get("SC4S_MANAGER_LISTENER_HOST"),
        help="Optional SC4S listener host passed into runtime-send command templates.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packs = load_packs(args.packs_root)
    if not packs:
        print("no packs found", file=sys.stderr)
        return 1

    bundle = validate_packs_bundle(
        packs,
        pack_id=args.pack_id,
        evidence_dir=args.evidence_dir,
        syslog_ng_validate_cmd=args.syslog_ng_validate_cmd,
        release_mode=args.release_mode,
        runtime_root=args.runtime_root,
        runtime_send_cmd=args.runtime_send_cmd,
        splunk_search_cmd=args.splunk_search_cmd,
        listener_host=args.listener_host,
    )
    if args.format == "json":
        print(json.dumps(bundle, indent=2, sort_keys=True))
    else:
        print(format_validation_text(bundle))
    return 0 if bundle["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
