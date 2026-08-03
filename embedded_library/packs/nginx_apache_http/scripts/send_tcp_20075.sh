#!/usr/bin/env bash
set -euo pipefail
HOST="${SC4S_TEST_HOST:-127.0.0.1}"
PORT="${SC4S_TEST_PORT:-20075}"
FIXTURE="${1:-$(dirname "$0")/../test-events/nginx_apache_http_test_events.txt}"
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  printf '<134>1 %s sc4s-nginx-apache-http fixture - - - %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line"
done < "$FIXTURE" | nc "$HOST" "$PORT"
