# Suricata EVE JSON local preflight — 2026-06-13

Purpose: command-grounded local preflight for the intended SC4S TEST -> Splunk TEST replay/read-back path. This is not replay/read-back validation.

## Listener check: TCP 20082
```
State Recv-Q Send-Q Local Address:Port Peer Address:Port
```

## TCP connect check: 127.0.0.1:20082
```
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20082: Connection refused
connect failed/refused or timed out
```

## Splunk TEST management/web reachability
```
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
8089 connect failed/refused or timed out
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
8000 connect failed/refused or timed out
```

Result: blocked at listener/testbed layer; fixture replay, SC4S/syslog-ng counters, HEC delivery, and Splunk indexed read-back were not run.
