#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20111}"
EVENT_FILE="${3:-$(dirname "$0")/../test-events/google_cloud_workspace_audit_test_events.txt}"
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  printf '%s
' "$line" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
