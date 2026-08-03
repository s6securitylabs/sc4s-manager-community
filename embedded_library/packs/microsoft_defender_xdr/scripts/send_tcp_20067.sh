#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20067}"
EVENT_FILE="${3:-$(dirname "$0")/../test-events/microsoft_defender_xdr_test_events.txt}"
while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  printf '<134>1 %s sc4s-defender-test defender - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$payload" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
