# Dell PowerScale OneFS audit logging preflight evidence — 2026-06-08

Status: blocked preflight only; not replay/read-back validation.

## Scope
- Profile: `dell_powerscale_onefs`
- Fixture set: `dell_powerscale_onefs_json_smoke`
- Fixture count: 2
- Marker prefix: `SC4S_DELL_POWERSCALE_TEST_`
- Replay script: `scripts/send_tls_20092.sh`
- Expected listener: TLS/RFC5425 on `127.0.0.1:20092` (`rfc5425_octet_counted_json_payload`)
- Expected Splunk index: `infraops`

## Commands run locally
```bash
ss -ltn 'sport = :20092'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/20092'
ss -ltn 'sport = :8089'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/8089'
ss -ltn 'sport = :8000'
timeout 2 bash -lc '</dev/tcp/127.0.0.1/8000'
```

## Observed result
- No listening TCP socket was present for profile port `20092`.
- TCP connect to `127.0.0.1:20092` failed/refused or timed out.
- TCP connects to local Splunk TEST ports `8089` and `8000` failed/refused or timed out.
- Because the SC4S listener and Splunk TEST endpoint were absent, the replay helper was not run and no HEC delivery, syslog-ng counter, or indexed read-back evidence was produced.

## Required read-back SPL when a testbed is available
```spl
index=infraops "SC4S_DELL_POWERSCALE_TEST_" earliest=-2h | table _time index sourcetype source vendor product protocol topic eventType detailType clientIPAddr userID userSID actor object marker _raw
```

Expected count: `2` events.

Must verify: event count, index, sourcetype, source, vendor, product, protocol/config family, eventType/detailType, client/user context where present, timestamp.
