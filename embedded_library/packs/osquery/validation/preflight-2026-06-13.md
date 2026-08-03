# osquery local preflight — 2026-06-13

This is command-grounded blocked-preflight evidence for the `osquery` pack. It is **not** replay/read-back validation and must not promote trust or quality.

## Intended route

- Listener: TCP syslog / line-delimited JSON relay on `127.0.0.1:20085`.
- Fixture set: `osquery_mixed` (`5` events, marker prefix `SC4S_OSQUERY_TEST_`).
- Expected index: `osnix`.
- Expected sourcetypes: `osquery:results`, `osquery:status`.
- Read-back SPL: `index=osnix "SC4S_OSQUERY_TEST_" earliest=-2h | table _time index sourcetype source vendor product osquery_log_type query_name hostIdentifier action severity status result process_name pid port protocol marker _raw`.

## Command results

```text
127.0.0.1:20085 blocked: ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8089 blocked: ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8000 blocked: ConnectionRefusedError: [Errno 111] Connection refused
```

## Verdict

Blocked at the listener/testbed layer. Fixture replay, SC4S/syslog-ng counters, HEC delivery, Splunk indexing, and Splunk search/read-back were not run in this repository maintenance environment.
