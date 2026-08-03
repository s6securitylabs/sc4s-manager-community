# Microsoft Cloud / M365 Event Hub profile preflight - 2026-06-07

Purpose: command-grounded local preflight for the profile-aware SC4S TEST -> Splunk TEST route. This is blocker evidence only; it is **not** fixture replay, SC4S/syslog-ng counter proof, HEC delivery, or Splunk indexed read-back validation.

## Listener check: TCP 20061

Command: `ss -ltn sport = :20061`

```text
State Recv-Q Send-Q Local Address:Port Peer Address:Port
```

Command: `timeout 3 bash -c '</dev/tcp/127.0.0.1/20061'`

```text
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20061: Connection refused
exit=1
```

## Splunk TEST reachability

Command: `timeout 3 bash -c '</dev/tcp/127.0.0.1/8089'`

```text
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
exit=1
```

Command: `timeout 3 bash -c '</dev/tcp/127.0.0.1/8000'`

```text
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
exit=1
```

## Result

Blocked at the listener/testbed layer. No local TCP listener is bound on `127.0.0.1:20061`, and local Splunk TEST management/web ports `8089` and `8000` refuse TCP connections. Fixture replay and indexed read-back were not attempted because the route is unavailable.
