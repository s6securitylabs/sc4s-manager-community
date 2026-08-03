#!/usr/bin/env bash
set -euo pipefail

HOST=${1:-127.0.0.1}
PORT=${2:-20051}
EVENT_FILE=${3:-"$(dirname "$0")/../test-events/vmware_vsphere_test_events.txt"}

while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  if [[ "$line" =~ ^\<[0-9]+\>1\  ]]; then
    msg="$line"
  else
    msg="<134>1 $(date -u +%Y-%m-%dT%H:%M:%SZ) vmware-vsphere-fixture.example.test SC4S - - ${line}"
  fi
  printf '%s %s' "${#msg}" "$msg" | openssl s_client -quiet -connect "${HOST}:${PORT}" >/dev/null 2>&1 || true
  printf '\n'
done < "$EVENT_FILE"
