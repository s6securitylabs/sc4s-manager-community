#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-20042}"
PROFILE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVENT_FILE="${PROFILE_DIR}/test-events/cisco_asa_test_events.txt"

if ! command -v nc >/dev/null 2>&1; then
  echo "nc is required to send TCP fixtures" >&2
  exit 1
fi

while IFS= read -r line || [[ -n "$line" ]]; do
  printf '%s\n' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$EVENT_FILE"
