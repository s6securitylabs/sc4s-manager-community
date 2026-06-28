#!/usr/bin/env bash
set -euo pipefail
HOST=${1:-127.0.0.1}
PORT=${2:-6514}
FILE=${3:-$(dirname "$0")/../test-events/pan_panos_test_events.txt}
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  printf '<134>1 %s pan-fw-a PAN-OS - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line" | openssl s_client -quiet -connect "${HOST}:${PORT}" 2>/dev/null || true
done < "$FILE"
