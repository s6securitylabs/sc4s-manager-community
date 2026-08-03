#!/usr/bin/env bash
set -euo pipefail
HOST="${SC4S_TEST_HOST:-127.0.0.1}"
PORT="${SC4S_TEST_PORT:-20062}"
FILE="${1:-$(dirname "$0")/../test-events/cisco_ios_syslog_test_events.txt}"
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  printf '%s
' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$FILE"
