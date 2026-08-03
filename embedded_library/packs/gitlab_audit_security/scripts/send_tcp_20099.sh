#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20099}"
EVENT_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/gitlab_audit_security_test_events.txt"
while IFS= read -r line; do
  printf '%s\n' "$line" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
