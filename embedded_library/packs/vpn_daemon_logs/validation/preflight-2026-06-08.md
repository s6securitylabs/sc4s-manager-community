# VPN daemon logs local validation preflight — 2026-06-08

Scope: command-grounded local preflight for the curated `vpn_daemon_logs` profile. This is not replay/read-back validation.

## Listener preflight: TCP 20078
```
State Recv-Q Send-Q Local Address:Port Peer Address:Port
```

## TCP connect preflight: 127.0.0.1:20078
```
connect failed: ConnectionRefusedError: [Errno 111] Connection refused
```

## Splunk management/web preflight

### 127.0.0.1:8089
```
connect failed: ConnectionRefusedError: [Errno 111] Connection refused
```

### 127.0.0.1:8000
```
connect failed: ConnectionRefusedError: [Errno 111] Connection refused
```

## Result

Blocked at listener/Splunk-testbed layer: no local dedicated VPN daemon TCP listener on 20078 and local Splunk TEST management/web ports refused. Fixture replay, SC4S parser counters, HEC delivery, and indexed Splunk read-back were not attempted.
