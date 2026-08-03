#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20080}"
FIXTURE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/container_runtime_systemd_logs_test_events.txt"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  printf '<13>1 2026-06-08T10:00:00Z container-runtime-test sechub-resources - - - %s\n' "$line" | nc "$HOST" "$PORT"
done < "$FIXTURE"
