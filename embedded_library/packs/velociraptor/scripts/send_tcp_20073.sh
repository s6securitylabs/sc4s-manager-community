#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20073}"
EVENT_FILE="${3:-$(dirname "$0")/../test-events/velociraptor_test_events.jsonl}"
while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  printf '<134>1 %s sc4s-velociraptor-test velociraptor - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$payload" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
