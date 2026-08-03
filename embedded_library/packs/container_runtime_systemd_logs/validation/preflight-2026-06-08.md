# Docker/container runtime and systemd service preflight — 2026-06-08

This is command-grounded blocker evidence only. It proves the local scheduled-worker host did not have the intended SC4S TEST listener or local Splunk TEST ports available. It is not replay/read-back validation and must not promote trust or quality.

## Commands

```text
2026-06-08T10:51:45Z
$ ss -ltn sport = :20080
State Recv-Q Send-Q Local Address:Port Peer Address:Port
$ python3 - <<PY (TCP connect 127.0.0.1:20080, 8089, 8000)
127.0.0.1:20080 connect failed: ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8089 connect failed: ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8000 connect failed: ConnectionRefusedError: [Errno 111] Connection refused
```

## Interpretation

- Required container runtime TCP listener `127.0.0.1:20080` was absent.
- Local Splunk management/search and web ports `8089` and `8000` refused TCP connections.
- Fixture replay, SC4S/syslog-ng counter checks, HEC delivery, indexed read-back, and field verification were not run.
- Next unblock path: provision a non-production Docker/containerd/systemd testbed with the dedicated listener, send the fixture set through `scripts/send_tcp_20080.sh`, then query Splunk for `SC4S_CONTAINER_RUNTIME_SYSTEMD_TEST_` markers and verify sourcetype/source-mode separation plus container/service identity fields.
