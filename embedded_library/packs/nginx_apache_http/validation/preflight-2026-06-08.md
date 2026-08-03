# Nginx / Apache HTTP access profile preflight — 2026-06-08

Purpose: command-grounded local preflight for the intended dedicated TCP listener and local Splunk TEST reachability. This is not replay/read-back validation.

## Listener check
```text
timestamp_utc=2026-06-08T06:08:17Z
State Recv-Q Send-Q Local Address:Port Peer Address:Port
nginx/apache TCP listener 127.0.0.1:20075 REFUSED_OR_UNREACHABLE: ConnectionRefusedError: [Errno 111] Connection refused
Splunk management 127.0.0.1:8089 REFUSED_OR_UNREACHABLE: ConnectionRefusedError: [Errno 111] Connection refused
Splunk web 127.0.0.1:8000 REFUSED_OR_UNREACHABLE: ConnectionRefusedError: [Errno 111] Connection refused
```

Result: blocked at listener/testbed layer. No fixture replay, SC4S/syslog-ng counters, HEC delivery, or Splunk indexed read-back were performed.
