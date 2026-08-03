#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20100}"
EVENT_FILE="${3:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/atlassian_cloud_audit_test_events.txt}"

if ! command -v nc >/dev/null 2>&1; then
  echo "nc is required to send fixture events" >&2
  exit 1
fi

while IFS= read -r line; do
  [ -z "$line" ] && continue
  printf '%s\n' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$EVENT_FILE"
