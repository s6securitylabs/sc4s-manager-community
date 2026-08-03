# NetApp ONTAP

Curated SecHub Resources SC4S pack for NetApp ONTAP EMS/audit syslog.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tls` listener on port `20093` with source tag `NETAPP_ONTAP`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `infraops` and sourcetype(s) `ontap:ems`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Evidence and scope

- Upstream SC4S ONTAP documentation and parser inventory.
- Upstream parser notes that ONTAP messages are not distinctive and should be identified by known hosts or a dedicated listener/port.
- Upstream parser shape for legacy ONTAP EMS records: program/host prefix, hex identifiers, severity token, and an embedded timestamp such as `Jun 05 2026 09:40:01 +00:00`.
- Public sourcetype conventions: `ontap:ems`, `netapp:ontap:ems`, and `netapp:ontap:audit` depending on `SC4S_NETAPP_ONTAP_NEW_FORMAT`.

This pack remains **curated / unverified** until real ONTAP events are replayed through SC4S and read back from Splunk.

## Transport and boundary

- Recommended: TLS/RFC5425 or TCP syslog on a dedicated listener because ONTAP payloads are not uniquely identifiable.
- Fixture shape: one BSD-style syslog event per line.
- Event boundary: physical line / syslog datagram.
- Multiline: not expected.
- Timestamp policy: parse embedded ONTAP timestamp when present; otherwise use syslog header/receiver time.

## Event families

- `ems_legacy` -> `ontap:ems`

The pack documents the newer-format sourcetypes but does not state full new-format audit/EMS parsing without real samples.

## Test events

Markers:

- `SC4S_NETAPP_ONTAP_TEST_EMS_NOTICE_001`
- `SC4S_NETAPP_ONTAP_TEST_EMS_ERROR_002`

Fixtures use example hostnames and no customer data.

## Dashboard scope

The included `netapp_ontap_overview` Splunk dashboard is a conservative onboarding and first-triage view for the fixture-backed ONTAP EMS legacy syslog smoke shape. It covers event arrival, severity distribution, error/notice counters, ONTAP node and event-ID coverage, host/source onboarding, and recent raw EMS context.

Dashboard panels intentionally use only fields present in the synthetic-equivalent fixtures and exposed by the Splunk props: `ontap_node`, `ontap_event_id`, `ontap_sequence`, `severity`, `signature`, `signature_id`, `marker`, plus Splunk `host`, `source`, `sourcetype`, and `_raw`. The dashboard does **not** statement new-format ONTAP audit/EMS coverage, complete ONTAP event catalogue coverage, real appliance field validation, collector health, or SC4S/Splunk replay/read-back validation.

## Validation harness status

Pack-aware replay/read-back is blocked until a SC4S TEST route and Splunk TEST read-back path are available:

```spl
index=infraops "SC4S_NETAPP_ONTAP_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product ontap_node ontap_event_id ontap_sequence severity signature signature_id _raw
```

Latest local preflight evidence: `validation/preflight-2026-06-07.md`. The preflight found no TCP/TLS listener on `127.0.0.1:20093` and no reachable local Splunk management/web ports, so no fixture replay, indexed read-back, trust promotion, or quality promotion was performed.

### Disposable E2E harness

A runnable Docker/Compose harness is available at `scripts/e2e_docker_compose.sh` for a permitted disposable SC4S TEST -> Splunk TEST lab:

```bash
packs/netapp_ontap/scripts/e2e_docker_compose.sh plan
packs/netapp_ontap/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/netapp_ontap/compose.yaml`, starts Splunk/SC4S containers, creates `index=infraops`, replays both ONTAP EMS legacy fixtures through TLS/RFC5425 TCP `20093`, and runs summary/detail read-back SPL for `ontap:ems`. It now requires a live `syslog-ng` process, usable control socket, and listening TCP/20093 route before replay; TLS send errors are fatal; Splunk searches run as the `splunk` user; and the run fails unless exactly two fixture markers are indexed. It is a lab-execution path only until run and evidence is retained; the harness itself is not replay/read-back validation and does not prove real ONTAP appliance/source-version emission, host/source identification strategy, new-format ONTAP audit/EMS records, collector wrapper behavior, HEC delivery, Splunk indexed read-back, production readiness, or trust/quality promotion.

## Known limitations

- Needs host/source or dedicated-port identification to avoid overmatching unrelated syslog.
- New-format ONTAP audit/EMS events require real sample confirmation before validated promotion.
- No drop/reduction rules are included.
