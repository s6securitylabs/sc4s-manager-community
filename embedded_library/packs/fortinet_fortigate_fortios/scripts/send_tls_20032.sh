#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20032}"
FIXTURE="${3:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/fortinet_fortigate_fortios_test_events.txt}"
while IFS= read -r payload; do
  [[ -z "$payload" ]] && continue
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  msg="<134>1 ${ts} fortigate-example FortiGate - - - ${payload}"
  printf '%s %s' "${#msg}" "$msg"
done < "$FIXTURE" | openssl s_client -quiet -connect "${HOST}:${PORT}"
