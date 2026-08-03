# GitHub audit/security local preflight — 2026-06-13

This is command-grounded blocked-preflight evidence only. It is not SC4S replay, HEC delivery, indexed Splunk read-back, or validation evidence.

## Intended route

- Pack: `github_audit_security`
- Listener: TCP `20086` for line-delimited GitHub audit/security JSON relay records
- Expected index: `gitops`
- Fixture markers: `SC4S_GITHUB_AUDIT_SECURITY_TEST_*`

## Local command results

The hourly run checked the local repository host for the intended listener and Splunk TEST endpoints. The local testbed was not running here:

```text
$ ss -ltn 'sport = :20086'
State Recv-Q Send-Q Local Address:Port Peer Address:Port
$ timeout 2 bash -lc '</dev/tcp/127.0.0.1/20086' && echo 'tcp 20086 reachable' || echo 'tcp 20086 refused/unreachable'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20086: Connection refused
tcp 20086 refused/unreachable
$ timeout 2 bash -lc '</dev/tcp/127.0.0.1/8089' && echo 'splunk 8089 reachable' || echo 'splunk 8089 refused/unreachable'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
splunk 8089 refused/unreachable
$ timeout 2 bash -lc '</dev/tcp/127.0.0.1/8000' && echo 'splunk 8000 reachable' || echo 'splunk 8000 refused/unreachable'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
splunk 8000 refused/unreachable
```

## Blocker

Replay/read-back is blocked at the `listener` layer because this repo runtime does not have a GitHub audit listener or Splunk TEST search path available. Promote neither `quality_status` nor `trust_level` from this evidence.
