# Juniper SRX/Junos local replay preflight — 2026-06-22

## Scope

Command-grounded blocker check for the pack-level `validation_harness`. This is **not** replay/read-back validation. No fixture events were sent, no SC4S/syslog-ng counters were checked, no HEC delivery was attempted, and no Splunk indexed read-back was performed.

Expected replay path when a lab is available:

- Listener/source tag: `JUNIPER_SRX_JUNOS`
- Transport: TCP syslog, line-delimited
- Port: `20044`
- Expected index: `netfw`
- Fixture set: `juniper_srx_junos_rfc5424_structured`
- Expected marker prefix: `SC4S_JUNIPER_SRX_TEST_`
- Expected event count: `4`

## Commands and results

```console
$ ss -ltn 'sport = :20044'
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/20044'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20044: Connection refused

$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8089'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused

$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8000'
# exit 0; TCP connect succeeded, but no authenticated Splunk search/read-back was run.
```

## Verdict

Blocked at the source listener and Splunk management/search-auth layers:

- No local TCP syslog listener was bound on `127.0.0.1:20044`.
- Local Splunk management/search endpoint `127.0.0.1:8089` refused the TCP connection.
- Local Splunk Web `127.0.0.1:8000` accepted TCP, but that is not indexed read-back evidence.

Keep `validation_harness.status=blocked`, `quality_status=curated`, and `trust_level=unverified` until replay through the intended route and Splunk indexed read-back evidence are captured.
