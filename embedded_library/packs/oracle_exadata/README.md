# Oracle Exadata engineered systems logs pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_exadata`.

This pack is a full catalogue/pack definition, not a validated parser implementation. It is intentionally `catalogued` and `unverified` until exact emitted source shapes, safe fixtures, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_exadata_cell_alert` — Storage cell alerts
  - Sourcetype target: `oracle:exadata:cell:alert`
  - Source shape: CellCLI alert history/export, cell alert files
  - Status: Blocked until exact CellCLI/export/file shape, severity vocabulary, and timezone policy exist.
- `oracle_exadata_cell_syslog` — Storage cell syslog
  - Sourcetype target: `oracle:exadata:cell:syslog`
  - Source shape: cell syslog/rsyslog relay
  - Status: Blocked until representative cell syslog lines and component names exist.
- `oracle_exadata_dbnode_syslog` — DB node Oracle Linux syslog
  - Sourcetype target: `oracle:exadata:dbnode:syslog`
  - Source shape: Oracle Linux syslog/journald/auditd with Exadata metadata
  - Status: Use Linux packs for Linux parsing; Exadata-specific metadata requires examples.
- `oracle_exadata_ilom` — ILOM / service processor logs
  - Sourcetype target: `oracle:exadata:ilom`
  - Source shape: ILOM syslog/SNMP/hardware event export
  - Status: Blocked until generation-specific ILOM event examples exist.
- `oracle_exadata_switch_syslog` — RoCE/InfiniBand switch logs
  - Sourcetype target: `oracle:exadata:switch:syslog`
  - Source shape: switch syslog/SNMP relay
  - Status: Blocked until switch generation/vendor and emitted logs are known.
- `oracle_exadata_exawatcher` — ExaWatcher / OSWatcher telemetry
  - Sourcetype target: `oracle:exadata:exawatcher`
  - Source shape: metric/report bundle outputs
  - Status: Manager/SecHub report target only unless line-oriented relay exists.
- `oracle_exadata_exachk` — EXAchk / ORAchk findings
  - Sourcetype target: `oracle:exadata:exachk`
  - Source shape: report XML/JSON/HTML/text
  - Status: Blocked until redistributable report schema/sample exists.
- `oracle_exadata_asr` — Auto Service Request events
  - Sourcetype target: `oracle:exadata:asr`
  - Source shape: ASR API/email/export relay
  - Status: Blocked until actual event/export shape exists.
- `oracle_exadata_oci_audit` — Exadata Cloud OCI Audit
  - Sourcetype target: `oracle:exadata:oci:audit`
  - Source shape: OCI Audit/Logging JSON for Exadata service actions
  - Status: Use generic OCI Audit until Exadata-specific payload examples exist.

## 2026-07-03 source-shape evidence pass

`docs/research/oracle-official-exadata-log-source-shape-evidence-20260703.md` records an Oracle-official evidence pass classifying each variant. Summary:

- **Relayable / could support a future conservative fixture-backed alpha slice:** cell + DB node OS syslog (native rsyslog RFC3164/5424 via `syslogconf`/`syslogInput`), and OCI Audit / Exadata Database Service on Cloud@Customer events (CloudEvents 0.1 JSON, RFC3339 UTC).
- **Strong-partial:** storage cell ALERTHISTORY — attributes and timestamp formats are documented, but delivery is SMTP/SNMP-trap/file-tail with no native single-line syslog wire format, so a fixture must declare its delivery-channel assumption.
- **Blocked / catalogue-only:** ILOM (fields known, wire shape undocumented), RoCE/IB switch (generation-dependent, no Exadata logging-host format), ASR (SNMP trap, not syslog; closed onward leg), ExaWatcher/OSWatcher (bzip2 diagnostic archives, not a stream), EXAchk/ORAchk (periodic report bundles, not a stream).

Routing stays disabled: documented shape evidence alone does not promote trust, and no live SC4S TEST -> HEC -> Splunk TEST read-back was captured. Overlap notes: OS syslog largely overlaps `packs/linux_os_syslog`; OCI Audit overlaps `packs/oracle_oci`.

## Splunk onboarding examples (disabled, example-only)

Conservative Splunk-side onboarding scaffolding is shipped for the onboardable variants. It does **not** promote trust or enable routing, and it ships **no** props.conf/transforms.conf parsing (no fixtures or replay/read-back exist yet).

- `splunk/default/inputs.conf.example` — disabled, placeholder input stanzas for cell ALERTHISTORY (file-tail channel), cell OS syslog (UF fallback), DB-node OS syslog (UF fallback), and OCI Audit staged JSON drop, plus operator-awareness notes for ILOM, RoCE/IB switch, ExaWatcher, EXAchk, and ASR (which are not `inputs.conf` sources). Uses `oracle:exadata:*` sourcetypes and `index=oracle`.
- `docs/collection/oracle_exadata_splunk_onboarding.md` — per-variant collection channel, official/community add-on prior art, a conservative collection model, and the evidence gaps to close before writing parsing or changing evidence posture.

Preferred paths: relay cell/DB-node rsyslog to the SC4S listener rather than tailing files; pull OCI Audit as CloudEvents JSON via OCI Logging/Service Connector; point ILOM/switch syslog at SC4S. Enable any stanza only after local source-shape and replay/read-back validation.


## Ingestion and collection notes

This is currently a **catalogue/source-definition pack**, not a deployable parser pack. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `oracle`, sourcetype(s) `oracle:exadata:cell:alert`, `oracle:exadata:cell:syslog`, `oracle:exadata:dbnode:syslog`, `oracle:exadata:ilom`, and 5 more declared sourcetype(s), credential/checkpoint ownership, and any safe ingestion-time transformations.

## Safety / evidence stance

- Source-shape acquisition checklist: `validation/source-shape-acquisition-plan-2026-06-20.md`. This checklist is a blocker-removal plan only, not validation evidence.
- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- No SC4S listener/parser artifacts are shipped for this definition yet.
- `routing_enabled` is false; Manager/SecHub should treat this as catalogue/source-planning coverage, not a deployable parser pack.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.
