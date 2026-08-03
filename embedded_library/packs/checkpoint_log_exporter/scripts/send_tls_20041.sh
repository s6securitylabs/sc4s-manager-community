#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20041}"
EVENT_FILE="${3:-$(dirname "$0")/../test-events/checkpoint_log_exporter_test_events.txt}"
while IFS= read -r event; do
  [[ -z "$event" ]] && continue
  len=${#event}
  printf '%s %s' "$len" "$event" | openssl s_client -quiet -connect "${HOST}:${PORT}" -servername "${HOST}" >/dev/null
  printf 'sent checkpoint_log_exporter fixture to %s:%s\n' "${HOST}" "${PORT}"
done < "$EVENT_FILE"
