# Atlassian Cloud audit preflight — 2026-06-21

This is command-grounded blocker evidence for the initial `atlassian_cloud_audit` pack. It is not replay/read-back validation and must not promote trust.

## Intended route

- Listener: TCP line-delimited JSON on `127.0.0.1:20100` / source tag `ATLASSIAN_CLOUD_AUDIT`.
- Expected index: `gitops`.
- Expected sourcetype: `atlassian:cloud:audit:json`.
- Fixture marker prefix: `SC4S_ATLASSIAN_CLOUD_AUDIT_TEST_`.

## Commands run

```text
$ date -u +%F
2026-06-21

$ ss -ltn sport = :20100
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ python3 tcp-connect-preflight
127.0.0.1:20100 BLOCKED ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8089 BLOCKED ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8000 CONNECTED
```

## Blocker

Replay/read-back is blocked at the listener layer and Splunk management/search-auth layer in this repository runtime. The Splunk web port accepted a TCP connection, but there is no authenticated search path captured here and no SC4S listener on the intended pack port.

## Required next evidence

To promote this pack above `curated` / `unverified`, replay all three fixture records or real Atlassian API-relay rows through the intended listener and read them back from Splunk TEST with event count, index, sourcetype, source, timestamps, vendor/product, family, actor, source IP, object/change fields, and raw JSON preserved.
