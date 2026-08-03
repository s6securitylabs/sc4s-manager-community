# Cloudflare local replay preflight — 2026-06-08

Purpose: command-grounded local preflight for the intended SC4S TEST -> Splunk TEST replay path. This is not replay/read-back validation.

## Commands
```text
2026-06-08T13:41:35Z
$ ss -ltn sport = :20081
State Recv-Q Send-Q Local Address:Port Peer Address:Port
$ timeout 3 bash -lc "</dev/tcp/127.0.0.1/20081"
$ timeout 3 bash -lc "</dev/tcp/127.0.0.1/8089"
$ timeout 3 bash -lc "</dev/tcp/127.0.0.1/8000"
```

## Result

No local TCP listener was available on 127.0.0.1:20081 and local Splunk TEST management/web ports refused connections. Fixture replay, SC4S parser counters, HEC delivery, and indexed Splunk read-back were not run.
