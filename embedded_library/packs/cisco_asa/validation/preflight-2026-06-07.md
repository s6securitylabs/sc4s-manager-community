# Cisco ASA/FTD profile replay preflight — 2026-06-07

Purpose: concrete local preflight for the profile-aware SC4S TEST -> Splunk TEST replay/read-back route before any quality promotion.

Profile route under test:

- Profile: `cisco_asa`
- Intended listener: TCP line-delimited syslog on `127.0.0.1:20042`
- Send helper: `packs/cisco_asa/scripts/send_tcp_20042.sh`
- Fixture set: `cisco_asa_bsd_syslog`
- Expected markers: six `SC4S_CISCO_ASA_TEST_*` events
- Expected index: `netfw`
- Expected Splunk read-back: source/host/timestamp/raw preservation plus `cisco:asa` sourcetype, Cisco facility/severity/message IDs, connection/action/transport/interface fields, eventtypes, and tags

## Commands and results

```text
$ ss -ltn sport = :20042
State Recv-Q Send-Q Local Address:Port Peer Address:Port
```

Result: no TCP listener was present for the dedicated Cisco ASA SC4S TEST route.

```text
$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/20042'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20042: Connection refused
```

Result: direct TCP connect to the dedicated listener was refused.

```text
$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8089'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
```

Result: local Splunk TEST management/search API reachability was blocked.

```text
$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8000'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
```

Result: local Splunk TEST web/search reachability was blocked.

## Verdict

Blocked at the local listener/testbed layer. Fixture replay was not attempted because the dedicated TCP listener was absent. SC4S/syslog-ng counters, HEC delivery, and Splunk indexed read-back were not available from this host.

This is command-grounded blocker evidence only. It does not validate Cisco ASA/FTD ingestion and must not raise `quality_status`, `quality_score`, `trust_level`, or `is_verified`.
