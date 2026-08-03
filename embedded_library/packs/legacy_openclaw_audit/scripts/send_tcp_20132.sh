#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20132}"
FILE="${3:-$(dirname "$0")/../test-events/legacy_openclaw_audit_test_events.txt}"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  printf '%s\n' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$FILE"
