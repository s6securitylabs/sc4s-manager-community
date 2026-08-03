#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20078}"
FIXTURE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events"
FIXTURE="${FIXTURE_DIR}/vpn_daemon_logs_test_events.txt"
if ! command -v nc >/dev/null 2>&1; then
  echo "nc is required to send TCP fixtures" >&2
  exit 1
fi
while IFS= read -r line; do
  printf '%s
' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$FIXTURE"
