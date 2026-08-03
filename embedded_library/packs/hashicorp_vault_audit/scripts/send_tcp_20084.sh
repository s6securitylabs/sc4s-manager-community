#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-20084}"
FIXTURE="${3:-$(cd "$(dirname "$0")/.." && pwd)/test-events/hashicorp_vault_audit_test_events.txt}"

while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '<134>1 %s vault-test.example.test vault-audit - - - %s\n' "$ts" "$payload"
done < "$FIXTURE" | nc "$HOST" "$PORT"
