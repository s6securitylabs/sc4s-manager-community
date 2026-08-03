#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20076}"
EVENT_FILE="${3:-$(dirname "$0")/../test-events/crowdstrike_falcon_test_events.jsonl}"
while IFS= read -r line; do
  printf '%s\n' "$line" | nc -N "$HOST" "$PORT"
done < "$EVENT_FILE"
