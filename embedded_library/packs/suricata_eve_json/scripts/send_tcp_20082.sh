#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20082}"
EVENT_FILE="${3:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/suricata_eve_json_test_events.txt}"
while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '<134>1 %s sc4s-suricata-eve-test suricata - - - %s\n' "$ts" "$payload" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
