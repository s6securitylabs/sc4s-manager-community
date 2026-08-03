#!/usr/bin/env bash
set -euo pipefail
host="${1:-127.0.0.1}"
port="${2:-20094}"
fixture="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/qnap_nas_test_events.txt"
while IFS= read -r line; do
  printf '%s
' "$line" | nc "$host" "$port"
done < "$fixture"
