#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20061}"
EVENT_FILE="${3:-$(dirname "$0")/../test-events/microsoft_cloud_m365_eventhub_test_events.txt}"
while IFS= read -r payload; do
  [ -z "$payload" ] && continue
  printf '<134>1 %s sc4s-microsoft-cloud-test cribl - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$payload" | nc "$HOST" "$PORT"
done < "$EVENT_FILE"
