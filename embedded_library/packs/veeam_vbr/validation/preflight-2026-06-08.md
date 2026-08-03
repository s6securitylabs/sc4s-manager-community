# Veeam Backup & Replication local replay preflight — 2026-06-08

This is command-grounded blocker evidence only. It is not replay/read-back validation and must not promote trust or quality labels.

## Commands

```text
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-06-08T02:00:59Z

$ ss -ltn sport = :20040
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ timeout 2 bash -lc '</dev/tcp/127.0.0.1/20040' && echo TCP_20040_OPEN || echo TCP_20040_REFUSED
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20040: Connection refused
TCP_20040_REFUSED

$ timeout 2 bash -lc '</dev/tcp/127.0.0.1/8089' && echo TCP_8089_OPEN || echo TCP_8089_REFUSED
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
TCP_8089_REFUSED

$ timeout 2 bash -lc '</dev/tcp/127.0.0.1/8000' && echo TCP_8000_OPEN || echo TCP_8000_REFUSED
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
TCP_8000_REFUSED
```

## Result

Blocked at the listener/testbed layer: no local Veeam VBR TLS listener on `127.0.0.1:20040`, and local Splunk TEST management/web ports were not reachable. Fixture replay, SC4S/syslog-ng counter checks, HEC delivery, and Splunk indexed read-back were not run.
