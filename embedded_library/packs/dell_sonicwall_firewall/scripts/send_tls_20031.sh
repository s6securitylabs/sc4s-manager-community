#!/usr/bin/env bash
set -euo pipefail

HOST=${1:-127.0.0.1}
PORT=${2:-20031}
MARKER=${3:-SC4S_DELL_SONICWALL_FIREWALL_TEST}
EVENT_FILE="$(dirname "$0")/../test-events/dell_sonicwall_firewall_test_events.txt"

while IFS= read -r payload; do
  [[ -z "$payload" ]] && continue
  payload="${payload/SC4S_DELL_SONICWALL_FIREWALL_TEST/${MARKER}}"
  msg="<134>1 $(date -u +%Y-%m-%dT%H:%M:%SZ) sonicwall.example.test SonicWall - - [sc4s@47450 profile=\"dell_sonicwall_firewall\" marker=\"${MARKER}\"] ${payload}"
  frame="${#msg} ${msg}"
  printf '%s' "$frame" | openssl s_client -quiet -connect "${HOST}:${PORT}" -servername "${HOST}" >/dev/null
  sleep 0.1
done < "$EVENT_FILE"
