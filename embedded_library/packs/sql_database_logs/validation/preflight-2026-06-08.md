# SQL database logs local replay preflight — 2026-06-08

This is command-grounded blocker evidence only. It is not replay/read-back validation.

## Commands and output

```text
State Recv-Q Send-Q Local Address:Port Peer Address:Port
CONNECT 127.0.0.1:20079 SQL DB TCP listener: blocked/refused (ConnectionRefusedError: [Errno 111] Connection refused)
CONNECT 127.0.0.1:8089 Splunk mgmt: blocked/refused (ConnectionRefusedError: [Errno 111] Connection refused)
CONNECT 127.0.0.1:8000 Splunk web: blocked/refused (ConnectionRefusedError: [Errno 111] Connection refused)
```

## Verdict

Local replay/read-back is blocked at the listener/testbed layer: no dedicated TCP listener on port 20079 was observed, and local Splunk management/web ports refused connections. Fixture replay, SC4S counters, HEC delivery, indexed Splunk read-back, and trust promotion were not performed.
