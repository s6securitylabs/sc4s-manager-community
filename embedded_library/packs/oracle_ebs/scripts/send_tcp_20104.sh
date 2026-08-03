#!/usr/bin/env bash
set -euo pipefail
TARGET_HOST="${1:-127.0.0.1}"
TARGET_PORT="${2:-20104}"
FIXTURE_FILE="${3:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/oracle_ebs_security_json_relay.txt}"
if [[ ! -f "$FIXTURE_FILE" ]]; then
  echo "fixture file not found: $FIXTURE_FILE" >&2
  exit 2
fi
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  printf '%s\n' "$line" | nc -w2 "$TARGET_HOST" "$TARGET_PORT"
done < "$FIXTURE_FILE"
