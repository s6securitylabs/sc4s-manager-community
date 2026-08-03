#!/usr/bin/env bash
set -euo pipefail
HOST=${1:-127.0.0.1}
PORT=${2:-6514}
FILE=${3:-$(dirname "$0")/../test-events/pan_panos_test_events.txt}

# RFC5425/TLS syslog uses octet-counted frames: <length> SP <RFC5424 message>.
# Keep one TLS session open and frame each fixture explicitly so replay matches the
# profile's recommended tls_rfc5425 transport instead of line-delimited TCP.
{
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    frame=$(printf '<134>1 %s pan-fw-a PAN-OS - - - %s' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line")
    printf '%s %s' "${#frame}" "$frame"
  done < "$FILE"
} | openssl s_client -quiet -connect "${HOST}:${PORT}" 2>/dev/null
