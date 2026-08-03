#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20072}"
FIXTURE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/linux_sysmon_test_events.txt"
while IFS= read -r line; do
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '<134>1 %s linux-sysmon-fixture sysmon - - - %s
' "$ts" "$line"
done < "$FIXTURE" | nc "$HOST" "$PORT"
