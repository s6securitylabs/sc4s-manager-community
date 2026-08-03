# Commvault CommCell preflight evidence — 2026-06-08

Status: blocked preflight only; not replay/read-back validation.

## Scope
- Profile: `commvault_commcell`
- Fixture set: `commvault_headerless_single_line`
- Fixture count: 3
- Marker prefix: `COMMVAULT_PROFILE_TEST_`
- Replay script: `scripts/send_tls_20029.sh`
- Expected listener: TLS/RFC5425 on `127.0.0.1:20029` (`rfc5425_octet_counted_headerless_payload_wrapped`)
- Expected Splunk index: `commvault`

## Commands run locally
```bash
ss -ltn 'sport = :20029'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/20029'
ss -ltn 'sport = :8089'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/8089'
ss -ltn 'sport = :8000'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/8000'
```

## Observed result
- No listening TCP socket was present for profile port `20029`.
- TCP connect to `127.0.0.1:20029` failed/refused or timed out.
- TCP connects to local Splunk TEST ports `8089` and `8000` failed/refused or timed out.
- Because the SC4S listener and Splunk TEST endpoint were absent, the replay helper was not run and no HEC delivery, syslog-ng counter, or indexed read-back evidence was produced.

## Required read-back SPL when a testbed is available
```spl
index=commvault "COMMVAULT_PROFILE_TEST_" earliest=-2h | table _time index sourcetype source vendor product cv_event_type action signature_id signature severity user dest process process_id app message Opid Eventid Alertid marker _raw
```

Expected count: `3` events.

Must verify: event count, index, sourcetype, source, vendor, product, Commvault family/action, family identifier, severity, user/dest/process context, timestamp.
