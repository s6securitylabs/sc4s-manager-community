#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20071}"
EVENT_FILE="${3:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/windows_sysmon_test_events.txt}"
while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '<134>1 %s sc4s-windows-sysmon-test windows-sysmon - - - %s
' "$ts" "$payload" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
