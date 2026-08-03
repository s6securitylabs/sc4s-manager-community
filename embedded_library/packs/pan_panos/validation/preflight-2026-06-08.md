# Palo Alto Networks PAN-OS validation preflight — 2026-06-08

Status: blocked; local listener/Splunk TEST services unavailable. This is preflight evidence only, not replay/read-back validation.

## Required preflight
- SC4S TEST listener: TLS/RFC5425 TCP listener on 127.0.0.1:6514 for `PAN_PANOS` / `pan_panos`.
- Replay helper: `scripts/send_tls_6514.sh [host] [port] [fixture_file]`.
- Fixture set: `panos_csv_single_line`, 15 line-delimited PAN-OS CSV fixture events wrapped by the helper as RFC5424/RFC5425.
- Marker prefix: `SC4S-PAN-` (fixtures include family markers such as `SC4S-PAN-TRAFFIC-MARKER`).
- Splunk TEST: SC4S/HEC can write to `netfw`; search role can read `netfw`.

## Observed result
- `ss -ltn 'sport = :6514'` returned only the header row; `/dev/tcp/127.0.0.1/6514` was refused or timed out.
- `ss -ltn 'sport = :8089'` and `ss -ltn 'sport = :8000'` returned only the header row; `/dev/tcp` checks to both Splunk TEST ports were refused or timed out.

## Not run
- Fixture replay over TLS/RFC5425.
- SC4S/syslog-ng counter checks.
- HEC delivery confirmation.
- Splunk indexed read-back.

## Intended read-back SPL
```spl
index=netfw "SC4S-PAN-" earliest=-2h | table _time index sourcetype source host vendor product vendor_product _raw
```
