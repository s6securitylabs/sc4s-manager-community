# Velociraptor local replay/read-back preflight — 2026-06-08

Command-grounded local preflight for the SecHub Resources `velociraptor` profile. This is blocked-preflight evidence only; it is not replay/read-back validation.

## Listener preflight

```
UTC 2026-06-08T04:42:35Z
State Recv-Q Send-Q Local Address:Port Peer Address:Port
127.0.0.1:20073 connection failed: ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8089 connection failed: ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8000 connection failed: ConnectionRefusedError: [Errno 111] Connection refused
```

## Result

- TCP listener `127.0.0.1:20073` was not reachable from this host.
- Local Splunk TEST management/web ports `8089` and `8000` were not reachable from this host.
- Fixture replay, SC4S/syslog-ng parser counters, HEC/index delivery, and Splunk indexed read-back were not attempted.
- Keep `quality_status: curated` and `trust_level: unverified` until real Velociraptor relay replay and Splunk read-back evidence exists.
