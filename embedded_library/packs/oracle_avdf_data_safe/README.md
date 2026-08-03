# Oracle Audit Vault, Database Firewall, and Data Safe pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_avdf_data_safe`.

This pack is a full catalogue/pack definition, not a validated parser implementation. It is intentionally `catalogued` and `unverified` until exact emitted source shapes, safe fixtures, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_avdf_audit_event` — AVDF consolidated audit events
  - Sourcetype target: `oracle:avdf:audit`
  - Source shape: AVDF SIEM/export/API audit events
  - Status: Blocked until current SIEM/export/API shape and original-source identity are known.
- `oracle_avdf_database_firewall` — AVDF Database Firewall SQL/network events
  - Sourcetype target: `oracle:avdf:database_firewall`
  - Source shape: DB Firewall events
  - Status: Blocked and sensitive; SQL text requires redaction/synthetic-equivalent handling.
- `oracle_avdf_admin_system_audit` — AVDF admin/system audit
  - Sourcetype target: `oracle:avdf:admin`
  - Source shape: appliance/admin/system audit
  - Status: Blocked until admin/system examples exist.
- `oracle_avdf_alert` — AVDF alerts
  - Sourcetype target: `oracle:avdf:alert`
  - Source shape: AVDF alert export/SIEM events
  - Status: Blocked until alert lifecycle/source DB mapping exists.
- `oracle_data_safe_audit` — Data Safe audit/activity events
  - Sourcetype target: `oracle:data_safe:audit`
  - Source shape: Data Safe API/OCI Audit/report exports
  - Status: Blocked until Data Safe event/API shape and OCI wrapper are known.
- `oracle_data_safe_risk_finding` — Data Safe risk/security findings
  - Sourcetype target: `oracle:data_safe:finding`
  - Source shape: assessment/finding exports
  - Status: Blocked until assessment/finding schema exists.

## Ingestion and collection notes

This is currently a **catalogue/source-definition pack**, not a deployable parser pack. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `main`, sourcetype(s) `oracle:avdf:audit`, `oracle:avdf:database_firewall`, `oracle:avdf:admin`, `oracle:avdf:alert`, and 2 more declared sourcetype(s), credential/checkpoint ownership, and any safe ingestion-time transformations.

## Safety / evidence stance

- Source-shape acquisition checklist: `validation/source-shape-acquisition-plan-2026-06-20.md`. This checklist is a blocker-removal plan only, not validation evidence.
- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- No SC4S listener/parser artifacts are shipped for this definition yet.
- `routing_enabled` is false; Manager/SecHub should treat this as catalogue/source-planning coverage, not a deployable parser pack.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.
