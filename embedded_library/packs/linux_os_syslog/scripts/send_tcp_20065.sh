#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20065}"
FIXTURE="${3:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/linux_os_syslog_test_events.txt}"
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  printf '<134>1 %s linux-os-syslog-test linux_os_syslog - - - %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line"
done < "$FIXTURE" | nc "$HOST" "$PORT"
