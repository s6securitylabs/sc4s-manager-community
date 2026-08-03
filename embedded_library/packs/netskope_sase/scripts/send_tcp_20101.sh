#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20101}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVENT_FILE="${SCRIPT_DIR}/../test-events/netskope_sase_test_events.txt"
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  printf '%s
' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$EVENT_FILE"
