#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20079}"
FIXTURE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events"
FIXTURE="$FIXTURE_DIR/sql_database_logs_test_events.txt"
while IFS= read -r line; do
  ts="$(date -u +%Y-%m-%dT%H:%M:%S.%6NZ)"
  msg="<134>1 ${ts} sql-db-relay.example.test sql_database_logs - - - ${line}"
  printf '%s\n' "$msg" | nc -w 2 "$HOST" "$PORT"
done < "$FIXTURE"
