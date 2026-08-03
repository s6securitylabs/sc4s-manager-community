#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20095}"
EVENT_FILE="${3:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/microsoft_defender_for_cloud_test_events.txt}"
if ! command -v nc >/dev/null 2>&1; then
  echo "nc is required to send TCP fixtures" >&2
  exit 2
fi
while IFS= read -r line; do
  [ -n "$line" ] || continue
  printf '%s
' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$EVENT_FILE"
