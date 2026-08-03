# Windows Event Log relay profile preflight — 2026-06-07

## Commands

```text
$ ss -ltn sport = :20063
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ timeout 2 bash -lc "</dev/tcp/127.0.0.1/20063"
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20063: Connection refused

$ timeout 2 bash -lc "</dev/tcp/127.0.0.1/8089"
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused

$ timeout 2 bash -lc "</dev/tcp/127.0.0.1/8000"
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
```

## Result

No local SC4S TEST listener was reachable on TCP 20063, and local Splunk management/web ports refused TCP connections. Fixture replay, HEC delivery, indexed Splunk read-back, and profile validation promotion were not performed.
