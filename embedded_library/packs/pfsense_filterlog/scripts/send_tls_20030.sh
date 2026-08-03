#!/usr/bin/env bash
set -euo pipefail

HOST=${1:-127.0.0.1}
PORT=${2:-20030}
MARKER=${3:-SC4S_PFSENSE_FILTERLOG_TEST}
EVENT_FILE="$(dirname "$0")/../test-events/pfsense_filterlog_test_events.txt"

while IFS= read -r payload; do
  [[ -z "$payload" ]] && continue
  msg="<134>1 $(date -u +%Y-%m-%dT%H:%M:%SZ) pfsense.example.test filterlog - - [sc4s@47450 profile=\"pfsense_filterlog\" marker=\"${MARKER}\"] ${payload}"
  frame="${#msg} ${msg}"
  printf '%s' "$frame" | openssl s_client -quiet -connect "${HOST}:${PORT}" -servername "${HOST}" >/dev/null
  sleep 0.1
done < "$EVENT_FILE"
