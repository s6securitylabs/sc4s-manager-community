#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20074}"
FIXTURE="${3:-$(dirname "$0")/../test-events/proxmox_test_events.txt}"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  printf '<134>1 %s pve-node-a proxmox-fixture - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line" | nc -w 2 "$HOST" "$PORT"
done < "$FIXTURE"
