#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-20097}"
FIXTURE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/sophos_firewall_test_events.txt"

while IFS= read -r payload; do
  [[ -z "${payload}" ]] && continue
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  msg="<134>1 ${ts} sophos-fw-test SFOS - - - ${payload}"
  len=${#msg}
  printf '%s %s' "${len}" "${msg}"
done < "${FIXTURE}" | openssl s_client -quiet -connect "${HOST}:${PORT}" -servername sophos-firewall-test
