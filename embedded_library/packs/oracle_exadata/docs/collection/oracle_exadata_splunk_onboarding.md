# Oracle Exadata engineered systems — Splunk onboarding research and collection guidance — 2026-07-07

## Attribution and access notes

This note is derived from public Oracle product documentation and public Splunkbase metadata. It records SecHub analysis and conservative deployment guidance only. No Oracle product samples, Splunk TA files, proprietary SPL, or dashboard XML are copied. Per-variant source-shape facts are carried over from `docs/research/oracle-official-exadata-log-source-shape-evidence-20260703.md` (Oracle-official evidence pass, access date 2026-07-03); the Splunkbase observations below were reviewed from public listing metadata.

This note does **not** promote `quality_status`, `trust_level`, or any `validated`/`verified` label. The pack remains a catalogue/source-definition (`generic_log_source_definition`) with `routing_enabled: false` until exact emitted records plus replay/read-back evidence exist.

## Scope

Oracle Exadata is an engineered system, not one log source. Splunk onboarding must be planned per telemetry variant, because the collection channel differs sharply between them:

| Variant (sourcetype) | Documented shape | Splunk collection channel | Onboardable now? |
| --- | --- | --- | --- |
| `oracle:exadata:cell:syslog` | RFC3164/5424 syslog | Native rsyslog relay (`syslogconf`/`syslogInput`) → SC4S; UF file monitor as fallback | Yes (syslog); overlaps `linux_os_syslog` |
| `oracle:exadata:dbnode:syslog` | RFC3164/5424 syslog | Native rsyslog relay → SC4S; UF file monitor as fallback | Yes (syslog); overlaps `linux_os_syslog`/`linux_auditd` |
| `oracle:exadata:cell:alert` | ALERTHISTORY object, multiline, ISO8601/legacy ts | SMTP / SNMP trap / cell+MS alert-log file tail | Strong-partial; declare channel first |
| `oracle:exadata:oci:audit` | CloudEvents 0.1 JSON, 1 record/event, RFC3339 UTC | OCI Logging + Service Connector, or OCI Audit API pull | Yes (JSON); overlaps `oracle_oci` |
| `oracle:exadata:ilom` | Class/Type/Severity/Description fields | ILOM remote syslog or SNMP trap | Blocked; wire format undocumented |
| `oracle:exadata:switch:syslog` | NX-OS (X8M+) or Sun/ILOM (pre-X8M) | Switch syslog/SNMP; Exadata sets up no logging host | Blocked; generation-dependent |
| `oracle:exadata:exawatcher` | bzip2 diagnostic archive bundles | File/archive pull + offline extract | Catalogue-only; not a stream |
| `oracle:exadata:exachk` | Periodic HTML/JSON/XML report bundle | Batch file pull; parse JSON | Catalogue-only; not a stream |
| `oracle:exadata:asr` | SNMP trap varbinds (SUN-HW-TRAP-MIB) | SNMP trap to ASR Manager; closed onward leg | Blocked; not a syslog/file source |

## Official Oracle source evidence

The per-variant Oracle references, documented attributes, delivery channels, and timestamp formats are recorded in `docs/research/oracle-official-exadata-log-source-shape-evidence-20260703.md` (representative Oracle doc URLs, access date 2026-07-03). Key implications for Splunk collection:

- **Cell / DB node OS syslog.** Oracle Linux with rsyslog produces standard RFC3164/RFC5424. Exadata System Software exposes `syslogconf` (extend syslog forwarding to a remote `syslogd`) and `syslogInput` (since 22.1, forward additional local logs), with encrypted transfer since 19.3.0. Prefer relaying to the SecHub SC4S listener over a forwarder file monitor. The incremental Exadata-specific parser value over generic Linux syslog is cell/component identity and cell-service program tags — still unproven without a captured sample.
- **Cell ALERTHISTORY.** Attributes and timestamp formats are documented, but there is no native single-line syslog emission of the alert object; delivery is SMTP, SNMP trap (MIB shipped on the cell), or file tail of the cell/MS alert logs. Any fixture/parser must declare which channel it assumes.
- **OCI Audit / Exadata C@C.** CloudEvents 0.1 envelope, one JSON record per event, `eventTime` RFC3339 UTC. Prefer OCI Logging + Service Connector or the OCI Audit API. Overlaps generic OCI audit; the Exadata-specific angle is the `com.oraclecloud.databaseservice.*` eventType vocabulary.
- **ILOM / switch / ASR / ExaWatcher / EXAchk.** Blocked or catalogue-only for the reasons in the evidence note: undocumented wire format (ILOM), no Exadata logging-host format (switch), out-of-band SNMP with a closed leg (ASR), and diagnostic archives / periodic report bundles rather than event streams (ExaWatcher, EXAchk).

## Splunk TA coverage and prior art

- There is **no single Splunk-built "Add-on for Oracle Exadata"** that covers all variants. Onboarding is assembled from component add-ons plus this SecHub source definition.
- For the OS-syslog variants, generic Linux syslog handling (and this repo's `packs/linux_os_syslog` / `packs/linux_auditd`) is the realistic parser base; Exadata adds host/cell identity, not a new syslog grammar.
- For OCI Audit, the OCI-side add-on / Service Connector path and this repo's `packs/oracle_oci` are the realistic base; Exadata adds the `databaseservice` eventType vocabulary.
- Prefer an official/community add-on for a component where one exists and is compatible. Do not vendor add-on content or assume parser compatibility; add an explicit, tested sourcetype bridge if a customer already runs a component add-on with different sourcetypes.
- Splunk docs pages were not fetched for this note; operators should inspect any installed add-on locally to map exact sourcetypes, inputs, props, and CIM coverage before choosing SecHub sourcetypes.

## Conservative collection model

1. **Prefer syslog relay for OS logs.** Relay cell and DB-node rsyslog to the SecHub SC4S listener (`ORACLE_EXADATA`, tcp/20105) rather than tailing `/var/log/messages` with a forwarder. Use the file-monitor stanzas only where a Universal Forwarder already runs on the node and relay is unavailable.
2. **Decide the cell-alert channel before building anything.** File-tail, SMTP-derived, and SNMP-trap-derived records are different shapes. The `inputs.conf.example` file-tail stanza assumes the cell/MS alert-log path; confirm the exact path for the installed release and treat records as multiline.
3. **Pull OCI Audit as JSON, one record per event.** Use OCI Logging + a Service Connector or the OCI Audit API via a site-owned collector with checkpoints; stage one JSON object per line if writing to a file drop. Prefer `packs/oracle_oci` until Exadata `databaseservice` payload examples and read-back exist.
4. **Treat ILOM and switches as syslog/SNMP forward targets, not files.** Point ILOM/NX-OS syslog forwarding at SC4S and capture a sanitized sample before writing a parser; there is no forwarder file path.
5. **ExaWatcher / EXAchk / ASR need collectors, not monitors.** A batch/archive extractor (ExaWatcher), a batch/API JSON pull (EXAchk/ORAchk AHF), and an SNMP-trap collector (ASR) are required respectively; none is an `inputs.conf` file source.
6. **No default lossy filtering, no invented parsing.** No props.conf field extractions are shipped for this pack because no fixtures or replay/read-back exist. Preserve raw records and source timestamps; masking must be opt-in and evidence-backed. Exadata logs may carry hostnames, OCIDs, users, and tenant identifiers — sample capture requires sanitisation.

## Implemented SecHub artifacts

- `splunk/default/inputs.conf.example` adds disabled, placeholder stanzas for the onboardable variants: cell ALERTHISTORY (file-tail channel), cell OS syslog (UF fallback), DB-node OS syslog (UF fallback), and OCI Audit staged JSON drop, plus operator-awareness notes for ILOM, switch, ExaWatcher, EXAchk, and ASR (which are not `inputs.conf` sources). The example uses SecHub `oracle:exadata:*` sourcetypes and `index=oracle`.
- No props.conf/transforms.conf parsing is shipped. Index-time and search-time extractions are deliberately withheld until a representative sanitised sample and replay/read-back exist for the chosen variant, consistent with the pack's `routing_enabled: false` / `quality_status: catalogued` posture.

## Evidence gaps before promotion

- Obtain a real sanitised sample for the chosen variant (cell OS syslog, cell ALERTHISTORY file-tail, or OCI `databaseservice` audit) and make the explicit delivery-channel/envelope decision.
- Confirm the exact cell/MS alert-log path, release, and timezone policy on the target Exadata System Software version.
- Run Splunk ingestion/read-back for each enabled stanza: event count, index, source, sourcetype, host, timestamp, line breaking, multiline/JSON handling, and sensitive-field handling.
- Only after the above, write index-time/search-time props for the validated variant and, where useful, CIM field aliases — then re-evaluate `routing_enabled`, `quality_status`, and `trust_level`.
