#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-20044}"
EVENT_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/juniper_srx_junos_test_events.txt"

while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  printf '%s\n' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$EVENT_FILE"
