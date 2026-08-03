# Oracle Exadata log source-shape evidence — 2026-07-03

Attribution:
- Primary source: Oracle official product documentation for Oracle Exadata Database Machine, Exadata System Software, Oracle ILOM, Autonomous Health Framework (EXAchk/ORAchk), Oracle ASR, and Oracle Cloud Infrastructure (OCI) Audit / Exadata Database Service on Cloud@Customer.
- Author/organisation: Oracle Corporation (documentation); analysis and derived source-shape mapping by S6 (SecHub Resources).
- Access date: 2026-07-03.
- Licence/terms: Oracle documentation is copyrighted. This note summarises facts (attribute names, delivery channels, event boundaries) and quotes nothing verbatim beyond short field/format tokens needed to support the technical point. No Oracle sample logs, tables, or screenshots are copied.

Use in this pack: source-shape reference and blocker triage only. It does **not** promote `quality_status`, `trust_level`, or any `validated`/`verified` label. The pack remains a catalogue/source-definition (`generic_log_source_definition`) with routing disabled until exact emitted records plus replay/read-back evidence exist.

## Purpose

Decide, per Exadata telemetry source, whether the emitted source shape is publicly documented well enough to justify a conservative synthetic-equivalent fixture and a deployable SC4S/Splunk alpha slice, versus which variants must stay catalogue-only with explicit blockers.

## Per-source verdicts

| Source | Line-oriented / relayable shape | Collection path | Verdict |
| --- | --- | --- | --- |
| Storage cell / DB node OS syslog | YES — RFC3164/RFC5424 | Native rsyslog relay (`syslogconf`, `syslogInput`) | Strong; syslog-capable |
| Exadata Cloud@Customer / OCI Audit | YES — CloudEvents 0.1 JSON, one record per event | OCI Audit API / Logging / Service Connector | Strong; JSON-capable |
| Storage cell ALERTHISTORY alerts | PARTIAL — structured object, multiline body; no documented native syslog wire line | SNMP trap / SMTP / cell+MS alert-log file tail | Strong-partial; channel must be chosen explicitly |
| ILOM / service processor | PARTIAL — fields known (Class/Type/Severity/Description), wire format undocumented | ILOM syslog forward / SNMP trap | Blocked pending wire-shape sample |
| RoCE / InfiniBand switch | PARTIAL — Cisco NX-OS (X8M+) or Sun/ILOM (pre-X8M); Exadata docs set up no logging host | Switch syslog / SNMP → ASR | Blocked; generation-dependent, no Exadata-specific format evidence |
| Auto Service Request (ASR) | PARTIAL — SNMP trap varbinds (SUN-HW-TRAP-MIB), not syslog; ASR→Oracle leg is closed API/email | SNMP trap to ASR Manager | Blocked; out-of-band SNMP, not a line stream |
| ExaWatcher / OSWatcher | NO — bzip2 diagnostic archive bundles, timestamp in filename | File/archive pull, offline extract | Catalogue-only; not an event stream |
| EXAchk / ORAchk (AHF) | NO/PARTIAL — periodic HTML/JSON/XML report bundle (zip) per run | Batch file pull; parse JSON | Catalogue-only; batch report, not stream |

## Key documented facts

- **OS syslog (cell + DB node):** Oracle Linux with rsyslog produces standard RFC3164/RFC5424 syslog. Exadata System Software exposes forwarding attributes `syslogconf` (extends syslog rules to forward to a remote `syslogd`) and `syslogInput` (since Exadata System Software 22.1, forwards additional local logs to remote log servers); encrypted log transfer since 19.3.0. One line per event; host/cell identity carried in the syslog hostname; timestamps follow syslog defaults (host timezone unless RFC5424 configured). This is the cleanest SC4S-friendly path, but it overlaps with generic Linux syslog handling — Exadata-specific value is confined to cell/component identity and cell-service program tags, which still need a captured sample to lock.
- **Cell ALERTHISTORY:** documented attributes include `name`, `alertSequenceID`, `alertType` (Stateful/Stateless), `severity` (critical/warning/info/clear), `alertMessage`, `alertShortName`, `beginTime`, `endTime`, `examinedBy`, `notificationState`, `metricObjectName`, `alertAction`, `ageInMinutes`. Timestamp formats seen in docs: ISO8601 with offset (e.g. `2012-09-10T13:22:38-07:00`) and a legacy `Sat May 18 10:14:16 PDT 2009` form. Delivery is via SMTP and/or SNMP trap (MIB shipped on the cell), or file tail of the cell/MS alert logs — there is **no documented native "emit this alert object as a single syslog line" path**. A fixture must therefore declare its delivery-channel assumption (file-tail record vs SNMP-trap-derived record).
- **OCI Audit / Exadata C@C:** CloudEvents 0.1 envelope — `cloudEventsVersion`, `eventID`, `eventType` (`com.oraclecloud.databaseservice.<resource><action>[.begin|.end]`), `source`, `eventTime` (RFC3339, UTC `Z`), `data` with `compartmentId`, `resourceName`, `resourceId`, and for audit-type events `identity` (`principalName`, `authType`, `ipAddress`, `userAgent`), `request`, `response`, `stateChange`. One JSON record per event. Overlaps with the existing generic OCI audit coverage (`packs/oracle_oci`); the Exadata-specific angle is the `databaseservice` eventType vocabulary.
- **ILOM:** syslog forwarding carries the local event-log fields (Class, Type, Severity, Description, date/time), but the exact wire format (RFC3164 vs 5424, program/tag, timestamp precision/timezone) is not published. Fields known, shape unknown.
- **Switches:** X8M and later use Cisco Nexus 9336C-FX2 (NX-OS); the Exadata configuration procedure sets up management/NTP/SSH/CoPP but no logging host, so any parser would rely on generic NX-OS syslog assumptions, not Exadata evidence. Pre-X8M uses Sun/Oracle InfiniBand switches managed via ILOM.
- **ASR:** SNMP traps (SUN-HW-TRAP-MIB varbinds such as `sunHwTrapSuspectComponentName`, `sunHwTrapFaultClass`, `sunHwTrapFaultMessageID`, `sunHwTrapFaultUUID`) to an ASR Manager; structured but not a syslog line, and the onward leg to Oracle is closed.
- **ExaWatcher/OSWatcher:** per-server sampling of OS tools and `cellsrvstat` written as bzip2 archives under `/opt/oracle.ExaWatcher/archive/...`, extracted with `GetExaWatcherResults.sh`. Diagnostic bundle, not an onboardable stream.
- **EXAchk/ORAchk (AHF):** each run produces a report bundle (HTML primary, optional JSON/XML) named `exachk_<host>_<db>_<date>_<timestamp>.html`; batch health report, no line-oriented event stream.

## Representative sources (access date 2026-07-03)

- Storage cell attributes/timestamps: `https://docs.oracle.com/en/engineered-systems/exadata-database-machine/sagug/list-alerthistory.html`
- Cell alert notification (SMTP/SNMP, MIB, no syslog of alert object): `https://docs.oracle.com/en/engineered-systems/exadata-database-machine/sagug/receiving-alert-notifications.html`
- Cell syslog forwarding attributes (`syslogconf`/`syslogInput`, encryption/release): `https://docs.oracle.com/en/engineered-systems/exadata-database-machine/sagug/alter-cell-syslog-attributes.html`
- Exadata security guide (rsyslog centralization): `https://docs.oracle.com/en/engineered-systems/exadata-database-machine/dbmsq/maintaining-secure-environment.html`
- ILOM syslog event logging (field set, not wire format): `https://docs.oracle.com/en/servers/management/ilom/5.1.x/admin-guide/configuring-syslog-event-logging.html`
- Cisco Nexus 9336C switch config (no logging host in procedure): `https://docs.oracle.com/en/engineered-systems/exadata-database-machine/dbmin/configuring-cisco-nexus-9336c-switch.html`
- ExaWatcher archive model: `https://docs.oracle.com/en/engineered-systems/exadata-database-machine/sagug/exawatcher.html`
- AHF/EXAchk report output formats: `https://docs.oracle.com/en/engineered-systems/health-diagnostics/exachk/oexug/understanding-and-managing-reports-and-output.html`
- OCI Audit JSON schema (CloudEvents, RFC3339/UTC): `https://docs.oracle.com/en-us/iaas/Content/Audit/Reference/logeventreference.htm`
- Exadata Database Service on Cloud@Customer events: `https://docs.oracle.com/en-us/iaas/exadata/doc/ecc-customer-events.html`

## Recommendation and current disposition

Two variants (**OS syslog cell/DB node**, **OCI Audit / C@C events**) have sufficient public evidence for a future conservative fixture-backed alpha slice, and one (**cell ALERTHISTORY**) is a strong-partial requiring an explicit delivery-channel choice. However:

- OS syslog largely overlaps generic Linux syslog (`packs/linux_os_syslog`); the incremental Exadata-specific parser value is cell/component identity that still needs a captured sample.
- OCI Audit overlaps generic OCI audit (`packs/oracle_oci`).

Given no live SC4S TEST → HEC → Splunk TEST read-back has been captured in this run, this pack is **kept catalogue-only with routing disabled**, and the variant blockers below are updated to reflect the evidence above. Promotion to a deployable alpha slice requires: (1) a real sanitised sample for the chosen variant, (2) an explicit delivery-channel/envelope decision, and (3) replay/read-back evidence. The five NO/blocked variants remain catalogue entries with the stated blockers.
