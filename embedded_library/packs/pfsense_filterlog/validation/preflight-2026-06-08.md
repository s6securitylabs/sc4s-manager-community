# pfSense Filterlog validation preflight — 2026-06-08

Status: blocked; local listener/Splunk TEST services unavailable. This is preflight evidence only, not replay/read-back validation.

## Required preflight
- SC4S TEST listener: TLS/RFC5425 TCP listener on 127.0.0.1:20030 for `PFSENSE_FILTERLOG` / `pfsense_filterlog`.
- Replay helper: `scripts/send_tls_20030.sh [host] [port] [marker_prefix]`.
- Fixture set: `pfsense_filterlog_headerless_csv`, 3 line-delimited headerless CSV events wrapped by the helper as RFC5424/RFC5425.
- Marker prefix: `SC4S_PFSENSE_FILTERLOG_TEST` in RFC5424 structured data; payload fixture tracker markers are `1770001001`, `1770001002`, and `1770001003`.
- Splunk TEST: SC4S/HEC can write to `netfw`; search role can read `netfw`.

## Observed result
- `ss -ltn 'sport = :20030'` returned only the header row; `/dev/tcp/127.0.0.1/20030` was refused or timed out.
- `ss -ltn 'sport = :8089'` and `ss -ltn 'sport = :8000'` returned only the header row; `/dev/tcp` checks to both Splunk TEST ports were refused or timed out.

## Not run
- Fixture replay over TLS/RFC5425.
- SC4S/syslog-ng counter checks.
- HEC delivery confirmation.
- Splunk indexed read-back.

## Intended read-back SPL
```spl
index=netfw ("SC4S_PFSENSE_FILTERLOG_TEST" OR signature_id IN (1770001001,1770001002,1770001003) OR tracker IN (1770001001,1770001002,1770001003)) earliest=-2h | table _time index sourcetype source host vendor product vendor_product action direction src src_ip src_interface dest dest_ip dest_port transport protocol signature signature_id tracker interface rule reason marker _raw
```
