#!/usr/bin/env bash
set -euo pipefail
TARGET_HOST="${1:-127.0.0.1}"
TARGET_PORT="${2:-20087}"
FIXTURE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/truenas_test_events.txt"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  printf '<134>1 %s %s truenas - - - %s\n' "$(date -u +%FT%TZ)" "$(hostname -s)" "$line" | nc -w2 "$TARGET_HOST" "$TARGET_PORT"
done < "$FIXTURE"
