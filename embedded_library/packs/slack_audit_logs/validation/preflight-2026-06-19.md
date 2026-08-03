# Slack audit local preflight — 2026-06-19

This is command-grounded blocked-preflight evidence only. It is not SC4S replay, HEC delivery, indexed Splunk read-back, or validation evidence.

## Intended route

- Pack: `slack_audit_logs`
- Listener: TCP `20096` for line-delimited Slack Audit Logs API JSON relay records
- Expected index: `netauth`
- Expected sourcetype: `slack:audit`
- Fixture markers: `SC4S_SLACK_AUDIT_LOGS_TEST_*`

## Local command results

The autonomous run checked the local repository host for the intended listener and Splunk TEST endpoints:

```text
$ ss -ltn 'sport = :20096'
State Recv-Q Send-Q Local Address:Port Peer Address:Port
$ timeout 2 bash -lc '</dev/tcp/127.0.0.1/20096' && echo 'tcp 20096 reachable' || echo 'tcp 20096 refused/unreachable'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20096: Connection refused
tcp 20096 refused/unreachable
$ timeout 2 bash -lc '</dev/tcp/127.0.0.1/8089' && echo 'splunk 8089 reachable' || echo 'splunk 8089 refused/unreachable'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
splunk 8089 refused/unreachable
$ timeout 2 bash -lc '</dev/tcp/127.0.0.1/8000' && echo 'splunk 8000 reachable' || echo 'splunk 8000 refused/unreachable'
splunk 8000 reachable
```

## Blocker

Replay/read-back is blocked at the `listener` layer because this repo runtime does not have a Slack Audit Logs TCP listener or Splunk management/search path available for fixture replay/read-back. Splunk Web port `8000` accepted a TCP connection, but management/search read-back on `8089` did not. Promote neither `quality_status` nor `trust_level` from this evidence.
