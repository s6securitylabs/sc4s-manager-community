# CrowdStrike Falcon local validation preflight — 2026-06-08

Profile: `crowdstrike_falcon` / CrowdStrike Falcon FDR JSON relay.

This is command-grounded blocked-preflight evidence only. It is **not** replay/read-back validation and must not promote trust or quality labels.

## Commands

Run from `/home/jarvis/work/sechub-resources` at `2026-06-08T07:02:52Z`:

```text
$ ss -ltn sport = :20076
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ python3 tcp_connect_probe.py
127.0.0.1:20076 ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8089 ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8000 ConnectionRefusedError: [Errno 111] Connection refused
```

## Result

- Dedicated CrowdStrike Falcon TCP listener `127.0.0.1:20076` was not present.
- Local Splunk management/search prerequisites on `127.0.0.1:8089` and `127.0.0.1:8000` were not reachable.
- Fixture replay, SC4S/syslog-ng counters, HEC delivery, and Splunk indexed read-back were not attempted.

## Blocker layer

`listener` is the primary blocker. Splunk TEST reachability is also unavailable and must be checked again after a testbed is provisioned.
