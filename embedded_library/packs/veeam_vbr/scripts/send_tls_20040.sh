#!/usr/bin/env bash
set -euo pipefail

HOST="${SC4S_HOST:-127.0.0.1}"
PORT="${SC4S_LISTEN_VEEAM_VBR_TLS_PORT:-20040}"
EVENT_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/veeam_vbr_test_events.txt"

while IFS= read -r line; do
  [[ -z "${line}" ]] && continue
  frame="${#line} ${line}"
  printf '%s' "${frame}" | openssl s_client -quiet -connect "${HOST}:${PORT}" -servername "${HOST}" >/dev/null
  sleep 0.1
done < "${EVENT_FILE}"
