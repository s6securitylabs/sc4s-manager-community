# Check Point Log Exporter

Curated SecHub Resources SC4S pack for Check Point Log Exporter syslog sent in the Splunk/SC4S-recommended RFC5424 structured-data shape.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tls` listener on port `20041` with source tag `CHECKPOINT_LOG_EXPORTER`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netfw` and sourcetype(s) `cp_log:syslog`.

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Evidence and scope

- Upstream SC4S `checkpoint_syslog` parser and Check Point source documentation inventory.
- Upstream SC4S `docs/sources/vendor/Checkpoint/logexporter_5424.md`, which says the recommended SC4S integration is RFC5424/IETF syslog over TCP without frame using a message-body structured-data block beginning with `[sc4s@2620 ...]` and space-delimited `field=value` pairs.
- Public Splunk Add-on sourcetype convention `cp_log:syslog`.

This pack is intentionally **curated / unverified**. It is not lab validated until real Check Point Log Exporter records are replayed through SC4S and read back from Splunk.

## Transport and event boundary

- Recommended transport: TCP RFC5424, line-delimited, normally `514/TCP` unless assigned to a dedicated listener.
- Optional TLS/RFC5425 helper is included for per-source TLS listeners.
- Fixture shape: one RFC5424 event per physical line.
- Event boundary: newline-delimited records for fixtures; production TCP must preserve one RFC5424 event per record.
- Multiline: not expected.
- Timestamp policy: use the RFC5424 header timestamp with timezone/offset when present. The Check Point `time` structured-data field is treated as fallback/reference until local validation confirms semantics.

## Event families

- `log_exporter_syslog` -> `cp_log:syslog`
- `firewall_traffic` -> `cp_log:syslog`
- `ips_protection` -> `cp_log:syslog`
- `audit_activity` -> `cp_log:syslog`
- `email_security` -> `cp_log:syslog`

The upstream parser may route blade/source metadata into more specific source values such as `checkpoint:firewall`, `checkpoint:ids`, or `checkpoint:web`. This pack keeps the sourcetype conservative and adds minimal Splunk knowledge for common action/source/destination/user fields.

## Test events

`test-events/checkpoint_log_exporter_test_events.txt` contains five synthetic-equivalent RFC5424 events with `[sc4s@2620 ...]` structured data. The first two rows preserve the original firewall accept/drop smoke coverage; the added rows are derived from upstream SC4S Check Point parser-test structures under BSD-2-Clause terms and re-synthesised with documentation-safe values for IPS, SmartConsole audit, and email-security source shapes. Marker tokens:

- `SC4S_CHECKPOINT_LOG_EXPORTER_TEST_ACCEPT_001`
- `SC4S_CHECKPOINT_LOG_EXPORTER_TEST_DROP_002`
- `SC4S_CHECKPOINT_LOG_EXPORTER_TEST_IPS_DROP_003`
- `SC4S_CHECKPOINT_LOG_EXPORTER_TEST_AUDIT_LOGIN_004`
- `SC4S_CHECKPOINT_LOG_EXPORTER_TEST_EMAIL_DETECT_005`

The records use RFC5737 documentation addresses and `example.test` identities only. They exercise firewall, IPS, audit/login, and email-security field preservation; they do not prove Check Point gateway, management-server, MTA, or collector delivery behavior.

## Dashboard coverage

`checkpoint_log_exporter_overview.xml` is a conservative onboarding and first-triage dashboard for the fixture-backed `cp_log:syslog` source shape. It covers event arrival, action distribution, accept/drop counters, source/destination pair triage, firewall rule context, user/source summaries, host/source onboarding coverage, and recent raw RFC5424 structured-data events.

Dashboard panels are limited to fields preserved by the fixtures and Splunk props/search-time extraction: `vendor_raw_action`/`action`, `src`, `src_ip`, `s_port`/`src_port`, `dst`, `dest_ip`, `service`/`dest_port`, `proto`/`transport`, `rule_name`, `rule_uid`, `protection_id`, `protection_name`, `attack`, `blade`, `user`/`administrator`, `client_ip`, `hostname`, `marker`, and raw event text. The dashboard does not state full Check Point blade coverage, proprietary Splunk TA parity, gateway/version validation, collector health, API/export coverage, or replay/read-back validation.

## Disposable E2E harness

`pack.json` references `scripts/e2e_docker_compose.sh` as an idempotent Docker/Compose harness for disposable SC4S TEST -> Splunk TEST replay/read-back. Use:

```bash
packs/checkpoint_log_exporter/scripts/e2e_docker_compose.sh plan
packs/checkpoint_log_exporter/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/checkpoint_log_exporter/compose.yaml`, generates or accepts an ephemeral Splunk HEC token at run time, mounts this pack's SC4S parser and Splunk knowledge, creates and verifies index `netfw`, replays all five fixture rows through TLS/RFC5425 listener `20041`, samples SC4S/syslog-ng counters, and runs Splunk read-back SPL for `SC4S_CHECKPOINT_LOG_EXPORTER_TEST_` markers. It fails closed on OpenSSL send errors, a missing `netfw` index, an event-count mismatch, or any marker event whose index, sourcetype, or source differs from `netfw`, `cp_log:syslog`, and `checkpoint_log_exporter`. The disposable SC4S health check also requires a real `syslog-ng` process, usable stats socket, and listening TCP/20041 route before replay proceeds.

The 2026-06-27 disposable lab attempt is retained in `validation/e2e-lab-2026-06-27.md`. It fixed a parser startup path that could crash syslog-ng, then remained blocked because fixture markers still did not read back from Splunk and a later route probe found the intended listener unavailable. This blocked attempt is useful harness evidence only; it is not replay/read-back validation.

A passing harness run would be route-local replay/read-back evidence for the declared synthetic-equivalent Check Point Log Exporter RFC5424 structured-data fixture shapes only. It does not prove a real gateway, management server, MTA, blade/version, collector wrapper, TCP/RFC5424 deployment variant, proprietary Splunk TA deployment, or field-validation scope without retained real product/source-version evidence.

## Known limitations

- Not validated with a real Check Point gateway, management server, or Log Exporter target.
- Blade/version fields vary; current required-field coverage covers core parser shape and common network/security fields only.
- No proprietary Splunk TA knowledge is copied. Splunk artifacts here are clean-room, minimal, and partial.
- No default drop/reduction rules are included.

## Validation

Local repository gate:

```bash
scripts/run_ci.sh
```

Promotion to `validated` requires replay through SC4S and read-back SPL similar to:

```spl
index=netfw "SC4S_CHECKPOINT_LOG_EXPORTER_TEST_" earliest=-2h
| table _time index sourcetype source vendor product vendor_raw_action action signature signature_id src src_ip s_port src_port dst dest_ip service dest_port proto transport user administrator client_ip rule_name rule_uid protection_id protection_name attack blade marker _raw
```
