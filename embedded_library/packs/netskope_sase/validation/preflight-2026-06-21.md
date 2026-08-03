# Netskope SASE replay/read-back preflight — 2026-06-21

This is command-grounded blocker evidence only. It is not SC4S/Splunk replay/read-back validation and must not promote trust.

## Commands run

```text
Sun Jun 21 11:45:57 PM UTC 2026

Listener check
State Recv-Q Send-Q Local Address:Port Peer Address:Port

TCP connect
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20101: Connection refused
connection refused or timed out

Splunk management/web/HEC checks
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
8089 refused or timed out
8000 connected
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8088: Connection refused
8088 refused or timed out
```

## Verdict

Replay/read-back is blocked at the listener and Splunk management/HEC layers: no Netskope SC4S TEST listener was present on TCP 20101, Splunk management 8089 refused, and HEC 8088 refused. Splunk Web 8000 accepted a TCP connection, but that is not sufficient for authenticated search/read-back.
