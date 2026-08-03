# Cisco ASA Firewall SecHub Resources Pack

Conservative pack for Cisco ASA/FTD `%ASA-` / `%FTD-` syslog messages.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tcp` listener on port `20042` with source tag `CISCO_ASA`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netfw` and sourcetype(s) `cisco:asa`.

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Evidence and selection

This pack was selected from the generated upstream SC4S catalogue because Cisco ASA is a high-impact firewall/VPN source that was not yet present in `packs/*`. Public evidence scanned for this run:

- Upstream SC4S `v3.43.0` (`5206370a6e9e5a2f3389b82291f68f86fc91c337`) source documentation: `docs/sources/vendor/Cisco/cisco_asa.md`, which documents ASA/FTD sourcetypes and recommends TCP/IP logging setup.
- Upstream SC4S `v3.43.0` Lite addon: `package/lite/etc/addons/cisco/app-cisco-cisco_asa.conf`, which routes messages starting with `%ASA-` and `%FTD-` to `cisco:asa` with `index=netfw`, `vendor=cisco`, and `product=asa`.
- Cisco product logging configuration guide linked from the upstream SC4S source page; used as vendor confirmation of syslog logging configuration, not as full emitted-event coverage.
- Elastic/Filebeat Cisco ASA public test logs at `x-pack/filebeat/module/cisco/asa/test/asa.log`, used only as public example-event shape evidence for common translation/connection messages. Current public sample source contains hundreds of `%ASA-*` lines, including `%ASA-6-305011`, `%ASA-6-302013`, and `%ASA-6-302014` examples.
- GitHub code search for `%ASA-6-302013`, `%ASA-6-302014`, and `%ASA-4-106023` returns multiple public repositories with ASA examples, parsers, or SOC training scenarios. Treat these as source-shape discovery inputs only; do not vendor third-party samples unless licence/provenance is reviewed and the events are sanitised or rewritten as synthetic-equivalent fixtures.

Fixtures in this repository are synthetic-equivalent, not redistributed vendor/customer logs. They preserve common Cisco ASA message grammar while replacing addresses and hosts with documentation-safe values.

## Quality and trust

- `quality_status`: `curated`
- `trust_level`: `unverified`
- Relationship to upstream: `extends_upstream`

Do not promote this pack to `validated` or `field_validated` until real ASA/FTD replay through SC4S and Splunk read-back evidence confirms event counts, sourcetype, source, fields, timestamps, and no unwanted drops.

## Transport and event boundaries

The fixtures are one BSD/RFC3164-style syslog event per line:

```text
Oct 10 2018 12:34:56 firewall-a CiscoASA[999]: %ASA-6-302013: ...
```

- Event boundary: one physical line.
- Envelope: BSD/RFC3164-style syslog header in fixtures.
- Payload format: Cisco ASA custom message text beginning with `%ASA-` or `%FTD-`.
- Timestamp policy: fixtures include month/day/year/time but no timezone; configure source timezone handling for production. The pack keeps quality conservative until real timestamp read-back is captured.
- Recommended transport: TCP syslog on a dedicated onboarding listener; UDP/514 is documented as legacy/lab-compatible only.

## Artifacts

- `sc4s/app_parsers/syslog/app-cisco_asa.conf` routes dedicated-listener and RFC-parsed network-source messages with strict `%ASA|%FTD-<severity>-<message_id>:` tokens to `cisco:asa` / `netfw`, guarded so already-identified sources are not overwritten.
- `sc4s/env.example` provides a dedicated TCP listener example.
- `splunk/default/props.conf` extracts Cisco facility/severity/message ID, preserves the raw `%ASA`/`%FTD` prefix family as `cisco_facility` for source-mode triage, preserves the post-header vendor payload as `cisco_message` for read-back auditability, preserves fixture-backed Cisco message verbs in `vendor_raw_action`, normalizes `action` to `allowed`/`blocked`/`teardown`, maps numeric Cisco severity to an analyst-friendly `severity_label`, normalizes extracted protocol tokens to uppercase `transport`, and surfaces a small set of common connection, dynamic-translation, and deny/access-group fields including explicit inbound/outbound connection `direction`, ASA source/destination interface names, fixture-backed connection identifiers, NAT original/translated endpoint context, and teardown duration/byte counters.
- `splunk/default/transforms.conf` contains parser notes; no masking/drop/routing transforms are enabled.
- `splunk/default/eventtypes.conf` and `splunk/default/tags.conf` add non-lossy search tags for the base ASA stream, connection builds/teardowns/translations, teardown events with explicit duration/byte metrics, dynamic translations, access-group denies, fixture-backed ICMP deny details, and the narrow `%FTD-6-302015` UDP connection smoke fixture. All ASA eventtypes carry product-family `cisco`/`asa` tags for discovery; access-group denies remain in deny-specific eventtypes rather than the broad connection grouping.
- `splunk/default/data/ui/views/cisco_asa_overview.xml` provides a fixture-backed onboarding and first-triage dashboard for event arrival, message-family coverage, access-group denies, connection build/teardown context, dynamic translation/NAT context, source/destination pairs, source/sourcetype/host coverage, and raw read-back context. Dashboard panels use only fields present in the six fixtures and Splunk props/eventtypes; dashboard availability does not imply replay/read-back validation.
- `test-events/cisco_asa_test_events.txt` contains six synthetic-equivalent smoke fixtures.
- `scripts/send_tcp_20042.sh` sends the fixture file to a line-delimited TCP syslog listener.

## Pack-aware replay/read-back harness

`pack.json` carries a blocked `validation_harness` requirements for the Cisco ASA/FTD pack. It is a runbook/status requirements, not validation evidence: replay is expected to use `scripts/send_tcp_20042.sh` against the dedicated TCP listener on port `20042`, produce six `SC4S_CISCO_ASA_TEST_*` events in `index=netfw`, and verify Splunk read-back for sourcetype/source/host/timestamp/raw preservation plus the normalized ASA fields and eventtypes listed below. The latest local preflight on 2026-06-07 is recorded in `validation/preflight-2026-06-07.md` and was blocked at the listener/testbed layer: `ss` returned only the header row for `127.0.0.1:20042`, `/dev/tcp/127.0.0.1/20042` returned connection refused, and local Splunk TEST ports `8089`/`8000` also refused TCP connections. No fixture replay, SC4S/syslog-ng counter check, HEC delivery, or Splunk indexed read-back was run.

## Fixture semantics

`test-events/cisco_asa_test_events.txt` contains six unique events:

1. `%ASA-6-305011` dynamic TCP translation with marker `SC4S_CISCO_ASA_TEST_TRANSLATION_001`.
2. `%ASA-6-302013` outbound TCP connection with marker `SC4S_CISCO_ASA_TEST_CONN_002`.
3. `%ASA-6-302014` teardown TCP connection with marker `SC4S_CISCO_ASA_TEST_TEARDOWN_003`.
4. `%ASA-4-106023` access-group deny with marker `SC4S_CISCO_ASA_TEST_DENY_004`.
5. `%ASA-4-106023` ICMP access-group deny with marker `SC4S_CISCO_ASA_TEST_DENY_ICMP_005`.
6. `%FTD-6-302015` inbound UDP connection with marker `SC4S_CISCO_ASA_TEST_FTD_UDP_006`, covering the upstream-compatible `%FTD-` prefix route without asserting full Firepower feature coverage.

These are smoke fixtures for routing and basic field extraction only. They are not a complete Cisco ASA syslog message catalog.

## Validation SPL

After replay into a lab SC4S/Splunk pipeline, query for the markers:

```spl
index=netfw ("SC4S_CISCO_ASA_TEST_TRANSLATION_001" OR "SC4S_CISCO_ASA_TEST_CONN_002" OR "SC4S_CISCO_ASA_TEST_TEARDOWN_003" OR "SC4S_CISCO_ASA_TEST_DENY_004" OR "SC4S_CISCO_ASA_TEST_DENY_ICMP_005" OR "SC4S_CISCO_ASA_TEST_FTD_UDP_006") earliest=-2h
| table _time index sourcetype source host vendor product vendor_product cisco_facility cisco_severity severity_label cisco_msg_id cisco_message signature signature_id connection_id action vendor_raw_action direction transport src src_interface src_ip src_port dest dest_interface dest_ip dest_port nat_original_interface nat_original_ip nat_original_port nat_translated_interface nat_translated_ip nat_translated_port duration bytes icmp_type icmp_code access_group eventtype _raw
```

Expected until real validation exists:

- 6 events returned.
- `sourcetype=cisco:asa`, `index=netfw`, `vendor=Cisco`, `product=ASA`.
- `severity_label` maps the fixture-backed `%ASA/%FTD` numeric severities, for example severity 4 to `warning` and severity 6 to `informational`.
- `signature` and `signature_id` preserve the fixture-backed Cisco message ID (`cisco_msg_id`) so reviewers can prove the analyst grouping fields match the raw `%ASA/%FTD-<severity>-<message_id>` token during read-back.
- `cisco_facility` preserves the raw prefix family (`ASA` or `FTD`) for analyst triage and to keep the narrow FTD smoke fixture distinguishable without overclaiming Firepower coverage.
- `cisco_message` preserves the vendor message body after the `%ASA/%FTD-<severity>-<message_id>` prefix so reviewers can trace normalized fields back to the payload during read-back without relying only on derived aliases.
- `eventtype=sc4s_cisco_asa_connections` covers fixture-backed connection message IDs only (`302013`, `302014`, and `302015`); NAT translation message `305011` is kept in `sc4s_cisco_asa_dynamic_translations`; `%ASA-4-106023` access-group denies are intentionally excluded and handled by deny-specific eventtypes so blocked traffic is not mislabeled as a connection.
- Connection fixtures expose fixture-backed `connection_id` values plus explicit `direction` values where the ASA payload carries `inbound` or `outbound`; extracted Cisco verbs such as `Built`, `Teardown`, and `Deny` are preserved in `vendor_raw_action` while `action` is normalized to `allowed`, `teardown`, or `blocked`; connection and access-group deny fixtures expose ASA interface context such as `src_interface=outside` and `dest_interface=inside` alongside endpoint IP and port fields where the payload includes ports, with protocol text normalized to uppercase `transport` values such as `TCP`, `UDP`, or `ICMP`.
- The teardown fixture exposes `duration=0:00:10` and `bytes=1234` from the existing `%ASA-6-302014` message text.
- `eventtype=sc4s_cisco_asa_connection_teardown_metrics` identifies teardown records only when fixture-backed duration and byte counters were extracted, preserving a narrow analyst search for connection-close accounting without stating complete ASA accounting coverage.
- `eventtype=sc4s_cisco_asa_denies` identifies the two `%ASA-4-106023` access-group deny fixtures and carries the `block` tag.
- `eventtype=sc4s_cisco_asa_icmp_denies` identifies the ICMP deny fixture only when `transport=ICMP`, `icmp_type`, `icmp_code`, and `access_group` were extracted.
- `eventtype=sc4s_cisco_asa_dynamic_translations` identifies the narrow `%ASA-6-305011` dynamic translation smoke fixture for analyst discovery without asserting complete NAT coverage; the read-back table includes the raw fixture-backed `nat_original_*` and `nat_translated_*` endpoint fields so reviewers can prove NAT/xlate context was preserved rather than hidden behind generic connection aliases.
- `eventtype=sc4s_cisco_asa_ftd_udp_connections` identifies the narrow `%FTD-6-302015` UDP connection smoke fixture without asserting broader Firepower coverage.
- Product-family `cisco` and `asa` tags are attached to every `sc4s_cisco_asa*` eventtype for analyst discovery only; they do not imply complete CIM coverage or validation promotion.
- No events are dropped by the basic/standard presets.
- Timestamp interpretation is reviewed against the source timezone configuration; fixtures include a year but no timezone.

## Known limitations

- No live ASA/FTD replay or Splunk read-back evidence is committed yet.
- Field extraction is intentionally narrow and focused on common connection/translation messages.
- `%FTD-` routing follows upstream SC4S Lite behavior and has a narrow UDP connection smoke fixture, but FTD unified/firepower-specific events may require separate sourcetypes or a future pack.
- No reduction/drop rule is included or default-enabled.
