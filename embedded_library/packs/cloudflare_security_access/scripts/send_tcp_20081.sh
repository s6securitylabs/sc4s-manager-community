#!/usr/bin/env bash
set -euo pipefail
HOST="${SC4S_TEST_HOST:-127.0.0.1}"
PORT="${SC4S_TEST_PORT:-20081}"
EVENT_FILE="${1:-$(dirname "$0")/../test-events/cloudflare_security_access_test_events.jsonl}"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  printf '<134>1 2026-06-08T12:00:00Z cloudflare-relay.example.test cloudflare-logpush - - - %s\n' "$line"
done < "$EVENT_FILE" | nc "$HOST" "$PORT"
