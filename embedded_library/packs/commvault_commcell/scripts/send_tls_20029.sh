#!/usr/bin/env bash
set -euo pipefail
SC4S_HOST="${1:-127.0.0.1}"
SC4S_PORT="${2:-20029}"
MARKER="${MARKER:-COMMVAULT_PROFILE_TEST_$(date -u +%Y%m%dT%H%M%SZ)}"
EPOCH="$(date -u +%s)"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${TMPDIR:-/tmp}/commvault_profile_send.$$"
trap 'rm -f "$OUT"' EXIT

sed -e "s/<MARKER>/${MARKER}/g" -e "s/<EPOCH>/${EPOCH}/g" "$DIR/../test-events/commvault_test_events.txt" |
while IFS= read -r event; do
  # The fixture file stores headerless application payloads. The default profile
  # listener is TLS/RFC5425, so wrap each payload in an RFC5424 syslog message and
  # add the RFC5425 octet-count prefix before sending over openssl.
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  syslog_msg="<134>1 ${ts} commvault-profile-fixture commvault - - - ${event}"
  len="$(LC_ALL=C printf '%s' "$syslog_msg" | wc -c | tr -d '[:space:]')"
  printf '%s %s' "$len" "$syslog_msg" | timeout 5 openssl s_client -connect "${SC4S_HOST}:${SC4S_PORT}" -quiet >"$OUT" 2>&1 || rc=$?
  rc=${rc:-0}
  if [ "$rc" != "0" ] && [ "$rc" != "124" ]; then
    echo "send failed rc=$rc"
    cat "$OUT"
    exit "$rc"
  fi
  unset rc
  sleep 1
done
echo "$MARKER"
