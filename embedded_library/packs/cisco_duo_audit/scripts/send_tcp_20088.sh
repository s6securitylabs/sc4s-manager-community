#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20088}"
FILE="${3:-$(dirname "$0")/../test-events/cisco_duo_audit_test_events.txt}"
python3 - "$HOST" "$PORT" "$FILE" <<'PY'
import socket
import sys
from pathlib import Path

host = sys.argv[1]
port = int(sys.argv[2])
fixture_path = Path(sys.argv[3])

sent = 0
with fixture_path.open("r", encoding="utf-8") as handle:
    for raw_line in handle:
        line = raw_line.rstrip("\n")
        if not line:
            continue
        payload = (line + "\n").encode("utf-8")
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.settimeout(5)
            sock.sendall(payload)
        sent += 1
        print(f"sent cisco_duo_audit fixture to {host}:{port}")

if sent == 0:
    raise SystemExit(f"no cisco_duo_audit fixture events found in {fixture_path}")
PY
