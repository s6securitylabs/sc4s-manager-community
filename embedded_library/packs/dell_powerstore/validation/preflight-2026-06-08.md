# Dell PowerStore remote logging preflight evidence — 2026-06-08

Status: blocked preflight only; not replay/read-back validation.

## Scope
- Profile: `dell_powerstore`
- Fixture set: `dell_powerstore_structured_data_smoke`
- Fixture count: 2
- Marker prefix: `SC4S_DELL_POWERSTORE_TEST_`
- Replay script: `scripts/send_tls_20091.sh`
- Expected listener: TLS/RFC5425 on `127.0.0.1:20091` (`rfc5425_octet_counted_powerstore_structured_data`)
- Expected Splunk index: `infraops`

## Commands run locally
```bash
ss -ltn 'sport = :20091'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/20091'
ss -ltn 'sport = :8089'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/8089'
ss -ltn 'sport = :8000'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/8000'
```

## Observed result
- No listening TCP socket was present for profile port `20091`.
- TCP connect to `127.0.0.1:20091` failed/refused or timed out.
- TCP connects to local Splunk TEST ports `8089` and `8000` failed/refused or timed out.
- Because the SC4S listener and Splunk TEST endpoint were absent, the replay helper was not run and no HEC delivery, syslog-ng counter, or indexed read-back evidence was produced.

## Required read-back SPL when a testbed is available
```spl
index=infraops "SC4S_DELL_POWERSTORE_TEST_" earliest=-2h | table _time index sourcetype source vendor product event_code severity event_type alert_raised call_home kb_article message marker _raw
```

Expected count: `2` events.

Must verify: event count, index, sourcetype, source, vendor, product, PowerStore structured-data marker, event code, severity/event_type, message, timestamp.
