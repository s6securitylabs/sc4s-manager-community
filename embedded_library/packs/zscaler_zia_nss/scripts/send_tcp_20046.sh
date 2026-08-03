#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20046}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
while IFS= read -r line; do
  printf '<134>1 %s zia-nss.example.test ZscalerNSS - - - %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line"
done < "$DIR/test-events/zscaler_zia_nss_test_events.txt" | nc "$HOST" "$PORT"
