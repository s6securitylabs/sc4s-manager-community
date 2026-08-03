# HashiCorp Vault audit local preflight — 2026-06-13

This command-grounded preflight checked only whether a local SC4S/Splunk TEST route was available for replay/read-back. It is blocked-preflight evidence, not validation.

## Commands

```text
timestamp_utc=2026-06-13T16:07:31Z
$ ss -ltn sport = :20084
State Recv-Q Send-Q Local Address:Port Peer Address:Port
$ timeout 3 bash -c "</dev/tcp/127.0.0.1/20084"
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20084: Connection refused
$ timeout 3 bash -c "</dev/tcp/127.0.0.1/8089"
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
$ timeout 3 bash -c "</dev/tcp/127.0.0.1/8000"
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
```

## Result

Blocked at listener/testbed layer: no local TCP listener was available on 127.0.0.1:20084 and local Splunk TEST management/web ports were not reachable from this repository run. Fixture replay, SC4S parser counters, HEC delivery, indexed Splunk search, and read-back field verification were not performed.
