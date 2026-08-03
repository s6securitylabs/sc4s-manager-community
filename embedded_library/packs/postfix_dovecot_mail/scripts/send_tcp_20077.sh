#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20077}"
FIXTURE="${3:-$(cd "$(dirname "$0")/.." && pwd)/test-events/postfix_dovecot_mail_test_events.txt}"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  printf '<14>1 %s mail-relay.example.test postfix_dovecot_mail - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line"
done < "$FIXTURE" | nc "$HOST" "$PORT"
