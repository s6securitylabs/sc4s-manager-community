# Check Point Log Exporter preflight evidence — 2026-06-08

Status: blocked preflight only; not replay/read-back validation.

## Scope
- Profile: `checkpoint_log_exporter`
- Fixture set: `checkpoint_log_exporter_rfc5424_sdata`
- Fixture count: 2
- Marker prefix: `SC4S_CHECKPOINT_LOG_EXPORTER_TEST_`
- Replay script: `scripts/send_tls_20041.sh`
- Expected listener: TLS/RFC5425 on `127.0.0.1:20041` (`rfc5425_octet_counted_structured_data`)
- Expected Splunk index: `netfw`

## Commands run locally
```bash
ss -ltn 'sport = :20041'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/20041'
ss -ltn 'sport = :8089'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/8089'
ss -ltn 'sport = :8000'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/8000'
```

## Observed result
- No listening TCP socket was present for profile port `20041`.
- TCP connect to `127.0.0.1:20041` failed/refused or timed out.
- TCP connects to local Splunk TEST ports `8089` and `8000` failed/refused or timed out.
- Because the SC4S listener and Splunk TEST endpoint were absent, the replay helper was not run and no HEC delivery, syslog-ng counter, or indexed read-back evidence was produced.

## Required read-back SPL when a testbed is available
```spl
index=netfw "SC4S_CHECKPOINT_LOG_EXPORTER_TEST_" earliest=-2h | table _time index sourcetype source vendor product src dest dest_port transport action signature signature_id rule_uid rule_name blade user marker _raw
```

Expected count: `2` events.

Must verify: event count, index, sourcetype, source, vendor, product, src/dest/dest_port/transport, action, rule/signature fields, user, timestamp.
