#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20064}"
FIXTURE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events"
FIXTURE_FILE="${FIXTURE_DIR}/linux_auditd_test_events.txt"
while IFS= read -r payload; do
  [[ -z "$payload" ]] && continue
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  msg="<13>1 ${ts} linux-auditd-test auditd - - - ${payload}"
  printf '%s\n' "$msg" | nc -w 2 "$HOST" "$PORT"
done < "$FIXTURE_FILE"
