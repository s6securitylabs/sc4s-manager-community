#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20112}"
FILE="${3:-$(dirname "$0")/../test-events/github_audit_security_test_events.txt}"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  printf '%s
' "$line" | nc -w 2 "$HOST" "$PORT"
done < "$FILE"
