#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20102}"
FIXTURE="${3:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/test-events/oracle_weblogic_server_access.txt}"
python3 - "$HOST" "$PORT" "$FIXTURE" <<'PY'
import socket, sys, pathlib
host, port, fixture = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3])
lines = [l.rstrip('
') for l in fixture.read_text().splitlines() if l.strip()]
with socket.create_connection((host, port), timeout=5) as sock:
    for line in lines:
        payload = '<134>1 2026-07-01T00:00:00Z weblogic-relay oracle_weblogic - - - ' + line + '
'
        sock.sendall(payload.encode())
print(f'sent {len(lines)} oracle_weblogic fixture records to {host}:{port}')
PY
