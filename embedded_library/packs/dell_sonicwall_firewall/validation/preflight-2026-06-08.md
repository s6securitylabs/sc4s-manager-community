# Dell SonicWall Firewall validation preflight — 2026-06-08

Status: blocked; local listener/Splunk TEST services unavailable. This is preflight evidence only, not replay/read-back validation.

## Required preflight
- SC4S TEST listener: TLS/RFC5425 TCP listener on 127.0.0.1:20031 for `DELL_SONICWALL_FIREWALL` / `dell_sonicwall_firewall`.
- Replay helper: `scripts/send_tls_20031.sh [host] [port] [marker_prefix]`.
- Fixture set: `dell_sonicwall_firewall_headerless_kv`, 2 line-delimited headerless key=value events wrapped by the helper as RFC5424/RFC5425.
- Marker prefix: `SC4S_DELL_SONICWALL_FIREWALL_TEST_`.
- Splunk TEST: SC4S/HEC can write to `netfw`; search role can read `netfw`.

## Observed result
- `ss -ltn 'sport = :20031'` returned only the header row; `/dev/tcp/127.0.0.1/20031` was refused or timed out.
- `ss -ltn 'sport = :8089'` and `ss -ltn 'sport = :8000'` returned only the header row; `/dev/tcp` checks to both Splunk TEST ports were refused or timed out.

## Not run
- Fixture replay over TLS/RFC5425.
- SC4S/syslog-ng counter checks.
- HEC delivery confirmation.
- Splunk indexed read-back.

## Intended read-back SPL
```spl
index=netfw "SC4S_DELL_SONICWALL_FIREWALL_TEST_" earliest=-2h | table _time index sourcetype source host vendor product vendor_product src src_port dest dest_port transport action signature signature_id dvc serial id m msg fw sn proto app marker _raw
```
