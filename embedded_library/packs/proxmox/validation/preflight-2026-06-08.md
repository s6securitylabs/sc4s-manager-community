# Proxmox local validation preflight — 2026-06-08

This is command-grounded blocked-preflight evidence only. It is not SC4S replay, HEC delivery, Splunk indexed read-back, S6 verification, or field validation.

## Expected route

- Listener: TCP `127.0.0.1:20074` / source tag `PROXMOX`.
- Expected index: `infraops`.
- Fixture marker prefix: `SC4S_PROXMOX_TEST_`.
- Required Splunk TEST capabilities: management/search access on local test ports and read access to `infraops`.

## Commands

### `ss -ltn 'sport = :20074'`

Exit/status: `0`

```text
State Recv-Q Send-Q Local Address:Port Peer Address:Port
```

### `python socket connect 127.0.0.1:20074`

Exit/status: `1`

```text
TCP connect failed: ConnectionRefusedError: [Errno 111] Connection refused
```

### `python socket connect 127.0.0.1:8089`

Exit/status: `1`

```text
TCP connect failed: ConnectionRefusedError: [Errno 111] Connection refused
```

### `python socket connect 127.0.0.1:8000`

Exit/status: `1`

```text
TCP connect failed: ConnectionRefusedError: [Errno 111] Connection refused
```

## Result

Blocked at `listener`: no dedicated Proxmox TCP listener was reachable on this host, and local Splunk TEST ports were unavailable. Do not promote trust or quality from this evidence.
