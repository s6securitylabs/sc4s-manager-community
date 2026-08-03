#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20070}"
EVENT_FILE="${3:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/jfrog_platform_test_events.txt}"
while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '<134>1 %s sc4s-jfrog-platform-test jfrog-platform - - - %s\n' "$ts" "$payload" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
