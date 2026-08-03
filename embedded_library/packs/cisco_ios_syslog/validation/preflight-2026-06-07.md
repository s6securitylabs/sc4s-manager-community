# Cisco IOS / IOS-XE preflight — 2026-06-07

Status: blocked / not validated.

This profile is curated from upstream SC4S documentation/parser evidence and synthetic-equivalent fixtures. The local route preflight below confirms that this host does not currently expose the intended Cisco IOS SC4S TEST listener or local Splunk TEST endpoints, so no profile-aware replay, syslog-ng counter review, HEC confirmation, or Splunk indexed read-back was performed.

## Intended validation route

- Profile: `cisco_ios_syslog`
- Listener: TCP line-delimited syslog on `127.0.0.1:20062`
- Expected index: `netops`
- Fixture set: `cisco_ios_syslog_bsd`
- Expected markers/events: 6 `SC4S_CISCO_IOS_TEST_*` events
- Read-back requirement: Splunk search must prove event count, index, sourcetype, source, host/fromhost, timestamp handling, raw preservation, Cisco token fields, selected search-time fields, eventtypes/tags, and no unintended drops.

## Command evidence

Captured: `2026-06-07T11:26:18Z`

```text
$ ss -ltn 'sport = :20062'
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/20062' && echo CONNECT_OK || echo CONNECT_FAILED:$?
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20062: Connection refused
CONNECT_FAILED:1

$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8089' && echo CONNECT_OK || echo CONNECT_FAILED:$?
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
CONNECT_FAILED:1

$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8000' && echo CONNECT_OK || echo CONNECT_FAILED:$?
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
CONNECT_FAILED:1
```

## Blocker

`listener`: no TCP listener accepted connections on `127.0.0.1:20062`; local Splunk TEST management/web ports `127.0.0.1:8089` and `127.0.0.1:8000` also refused connections. Quality remains `curated`; trust remains `unverified`.
