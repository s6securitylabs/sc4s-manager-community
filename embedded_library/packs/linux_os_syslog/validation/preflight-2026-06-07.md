# Linux common OS syslog replay/read-back preflight — 2026-06-07

This is command-grounded blocked-preflight evidence only. It is not replay/read-back validation and must not promote trust or quality labels.

## Commands and output

```text
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-06-07T20:57:45Z

$ ss -ltn sport = :20065
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ timeout 2 bash -c '</dev/tcp/127.0.0.1/20065'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20065: Connection refused

$ timeout 2 bash -c '</dev/tcp/127.0.0.1/8089'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused

$ timeout 2 bash -c '</dev/tcp/127.0.0.1/8000'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
```

## Result

- Blocked layer: `listener`.
- No TCP listener was available on `127.0.0.1:20065` for the dedicated Linux common OS syslog route.
- Local Splunk TEST management/web ports `8089` and `8000` also refused TCP connections.
- Fixture replay, SC4S/syslog-ng counter checks, HEC delivery, indexed Splunk read-back, and Manager apply were not run.
