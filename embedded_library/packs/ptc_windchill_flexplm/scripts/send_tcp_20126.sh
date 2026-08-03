#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20126}"
FIXTURE="${3:-$(dirname "$0")/../test-events/windchill_exploitation.log}"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  printf '<134>1 %s windchill-app ptc-windchill-fixture - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line" | nc -w 2 "$HOST" "$PORT"
done < "$FIXTURE"
