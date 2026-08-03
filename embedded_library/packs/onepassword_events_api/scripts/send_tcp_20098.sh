#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20098}"
FIXTURE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/onepassword_events_api_test_events.txt"
while IFS= read -r line; do
  printf '%s\n' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$FIXTURE"
