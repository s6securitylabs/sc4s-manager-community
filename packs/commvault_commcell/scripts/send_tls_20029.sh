#!/usr/bin/env bash
set -euo pipefail
SC4S_HOST="${1:-127.0.0.1}"
SC4S_PORT="${2:-20029}"
MARKER="${MARKER:-COMMVAULT_PROFILE_TEST_$(date -u +%Y%m%dT%H%M%SZ)}"
EPOCH="$(date -u +%s)"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sed -e "s/<MARKER>/${MARKER}/g" -e "s/<EPOCH>/${EPOCH}/g" "$DIR/../test-events/commvault_test_events.txt" |
while IFS= read -r event; do
  printf '%s\n' "$event" | timeout 5 openssl s_client -connect "${SC4S_HOST}:${SC4S_PORT}" -quiet >/tmp/commvault_profile_send.out 2>&1 || rc=$?
  rc=${rc:-0}
  if [ "$rc" != "0" ] && [ "$rc" != "124" ]; then
    echo "send failed rc=$rc"
    cat /tmp/commvault_profile_send.out
    exit "$rc"
  fi
  unset rc
  sleep 1
done
echo "$MARKER"
