#!/usr/bin/env bash
set -euo pipefail

HOST=${SC4S_HOST:-127.0.0.1}
PORT=${SC4S_PORT:-20050}
EVENT_FILE=${1:-"$(dirname "$0")/../test-events/f5_bigip_test_events.txt"}

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required to send TLS/RFC5425 fixtures" >&2
  exit 1
fi

python3 - "$EVENT_FILE" <<'PY' | openssl s_client -quiet -connect "${HOST}:${PORT}" -ign_eof
import sys
from pathlib import Path
for line in Path(sys.argv[1]).read_text().splitlines():
    if not line.strip():
        continue
    payload = line.rstrip('\n')
    print(f"{len(payload)} {payload}")
PY
