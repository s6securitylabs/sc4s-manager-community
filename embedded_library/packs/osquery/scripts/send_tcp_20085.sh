#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-20085}"
FIXTURE="${3:-$(cd "$(dirname "$0")/.." && pwd)/test-events/osquery_test_events.txt}"

while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '<134>1 %s osquery-test.example.test osquery - - - %s\n' "$ts" "$payload"
done < "$FIXTURE" | nc "$HOST" "$PORT"
