# Oracle Database audit, listener, and diagnostic logs pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_database`.

This pack is a full catalogue/pack definition, not a validated parser implementation. It is intentionally `catalogued` and `unverified` until exact emitted source shapes, safe fixtures, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_database_unified_audit` — Unified Audit Trail row/export events
  - Sourcetype target: `oracle:database:unified_audit`
  - Source shape: database_table_query, collector JSON/CSV row export; SC4S only when relayed one row per event
  - Status: Preserve event timestamp, DB user, proxy/OS user, policy, action, object, privilege, return code, client host/IP, module, service, CDB/PDB context. Blocked for parser validation until a selected collector/export envelope is captured.
- `oracle_database_traditional_audit` — Traditional audit / SYS.AUD$ / DBA_AUDIT_TRAIL
  - Sourcetype target: `oracle:database:traditional_audit`
  - Source shape: database table/export rows or OS audit files
  - Status: Blocked until version-specific exported row/file shape exists.
- `oracle_database_fga` — Fine-Grained Auditing
  - Sourcetype target: `oracle:database:fga`
  - Source shape: FGA table/view/export rows
  - Status: Blocked until exact FGA row/export shape and safe SQL/context handling exist.
- `oracle_database_listener` — Oracle Net listener / ADR listener logs
  - Sourcetype target: `oracle:database:listener`
  - Source shape: listener.log, ADR listener text/XML, RAC/SCAN variants
  - Status: Blocked until exact standalone/RAC/SCAN/TCPS/failure examples exist.
- `oracle_database_alert_adr` — ADR alert / V$DIAG_ALERT_EXT diagnostics
  - Sourcetype target: `oracle:database:adr:alert`
  - Source shape: ADR view row export, alert log text/XML candidates
  - Status: Actionable for row-schema planning; raw text/XML fixtures blocked until boundaries are proven.
- `oracle_database_rac_grid_asm` — RAC / Grid Infrastructure / ASM logs
  - Sourcetype target: `oracle:database:rac_grid_asm`
  - Source shape: CRS/CSS/OHASD/ASM/SCAN listener logs
  - Status: Blocked on exact emitted examples.

## Ingestion and collection notes

This is currently a **catalogue/source-definition pack**, not a deployable parser pack. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `infraops` (the SC4S relay default; the Splunk universal-forwarder examples in `splunk/default/inputs.conf.example` target a dedicated `oracle` index instead — pick one local index story before onboarding), sourcetype(s) `oracle:database:unified_audit`, `oracle:database:traditional_audit`, `oracle:database:fga`, `oracle:database:listener`, and 2 more declared sourcetype(s), credential/checkpoint ownership, and any safe ingestion-time transformations.

## Source-shape acquisition gate

`validation/source-shape-acquisition-plan-2026-06-20.md` is the current unblock checklist for this pack. It defines acceptable evidence for fixture authoring, variant-specific minimum captures, and shortcuts that must not be treated as source evidence. In short: Oracle table/view dictionaries are useful for field planning, but fixture/parser work still needs exact emitted/exported record shape, boundaries, timestamp rendering, null/quoting behavior, and collector envelope proof.

## Safety / evidence stance

- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- No SC4S listener/parser artifacts are exported for this source-definition pack yet.
- `routing_enabled` is false; Manager/SecHub should treat this as catalogue/source-planning coverage, not a deployable parser pack.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.

## 2026-07-01 fixture-backed alpha slice

This pack now includes narrow source-shape fixture slices for Oracle traditional audit-file records (`test-events/oracle_database_audit_file.txt`) and Unified Audit syslog-style records (`test-events/oracle_database_unified_audit_syslog.txt`). The fixtures are synthetic-equivalent records derived from public source-shape evidence; they are not real Oracle estate logs and no SC4S/Splunk parser artifacts are exported while this remains a source-definition pack.

Status remains **Alpha source-shape / unverified** for these fixture slices and **catalogue-only** for the other Database variants. No live Oracle DB, SC4S replay, HEC delivery, or Splunk indexed read-back has passed. This is not Beta and has no operational trust claim.

## 2026-07-02 demo-lab acquisition path

`validation/demo-lab-data-acquisition-plan-2026-07-02.md` records the current free/developer lab-data options. The preferred path is Oracle Database Free/XE in a disposable Docker or Vagrant lab, generating and sanitising our own Unified Audit, listener, and ADR/alert records. This remains an acquisition plan only; generated lab records and replay/read-back evidence are still required before any validation or trust promotion.

## 2026-07-06 Splunk onboarding guidance

`docs/collection/oracle_database_splunk_onboarding.md` and `splunk/default/inputs.conf.example` add conservative, disabled Splunk collection scaffolding for Oracle Database Server audit, listener, ADR alert, and RAC/Grid/ASM candidates. The guidance prefers the official Splunk Add-on for Oracle Database and Splunk DB Connect/Oracle JDBC where available; the SecHub inputs example is a placeholder/path-inventory artifact only and does not promote this pack to deployable or validated status.
