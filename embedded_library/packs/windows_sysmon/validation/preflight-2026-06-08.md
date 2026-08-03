# Windows Sysmon local replay preflight — 2026-06-08

This is command-grounded blocker evidence for the profile-level validation harness. It is not replay/read-back validation and must not promote trust or quality.

## Commands and output

```text
## listener check: ss -ltn sport = :20071
State Recv-Q Send-Q Local Address:Port Peer Address:Port

## tcp connect: 127.0.0.1:20071
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20071: Connection refused
connection refused or timed out

## Splunk management: 127.0.0.1:8089
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
connection refused or timed out

## Splunk web/search: 127.0.0.1:8000
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
connection refused or timed out
```

## Result

Blocked at the listener/testbed layer: no dedicated TCP listener on `127.0.0.1:20071`, and local Splunk TEST management/web ports refused connections. Fixture replay, SC4S/syslog-ng counters, HEC delivery, indexed Splunk read-back, and eventtype/tag verification were not run.
