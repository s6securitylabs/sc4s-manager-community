#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20063}"
EVENT_FILE="${3:-$(dirname "$0")/../test-events/windows_eventlog_test_events.txt}"
while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  printf '<134>1 %s sc4s-windows-eventlog-test windows-eventlog - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$payload" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
