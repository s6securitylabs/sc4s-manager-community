#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20083}"
EVENT_FILE="${3:-$(dirname "$0")/../test-events/zeek_json_logs_test_events.txt}"
while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  printf '<13>1 %s zeek-fixture zeek-json - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$payload" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
