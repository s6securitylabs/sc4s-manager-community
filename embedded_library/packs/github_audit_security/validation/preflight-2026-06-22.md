# github_audit_security listener preflight — 2026-06-22

This command-grounded preflight was captured after moving the pack's intended SC4S TEST listener port away from a duplicate reserved port. It is blocker evidence only; it is not replay/read-back validation.

Expected listener: TCP `20112` for the pack-specific JSON relay.

```bash
$ ss -ltn 'sport = :20112'
State Recv-Q Send-Q Local Address:Port Peer Address:Port
# exit=0
```

```text
127.0.0.1:20112 ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8089 ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8000 reachable
```

Blocked layer: `listener`. Replay was not attempted because the pack-specific SC4S TEST listener is not reachable on this host; Splunk TEST management/web ports are also not reachable here.
