# Linux auditd relay preflight — 2026-06-07

Command-grounded local preflight for the initial linux_auditd profile. This is blocked-preflight evidence only; it is not SC4S replay, HEC delivery, Splunk indexed read-back, validation, or trust promotion evidence.

## Listener check: TCP 20064
```
State Recv-Q Send-Q Local Address:Port Peer Address:Port
tcp_connect_127.0.0.1_20064=blocked: ConnectionRefusedError: [Errno 111] Connection refused
```

## Splunk TEST reachability
```
tcp_connect_127.0.0.1_8089=blocked: ConnectionRefusedError: [Errno 111] Connection refused
tcp_connect_127.0.0.1_8000=blocked: ConnectionRefusedError: [Errno 111] Connection refused
```

## Result

Blocked at listener/testbed layer: no TCP listener on 127.0.0.1:20064 and no local Splunk TEST management/web reachability on 8089/8000. Fixture replay and Splunk read-back were not attempted.
