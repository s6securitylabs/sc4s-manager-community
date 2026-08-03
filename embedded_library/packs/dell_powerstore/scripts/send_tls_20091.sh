#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20091}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  len=${#line}
  printf '%s %s
' "$len" "$line" | openssl s_client -quiet -connect "${HOST}:${PORT}" 2>/dev/null || true
done < "${DIR}/test-events/dell_powerstore_test_events.txt"
