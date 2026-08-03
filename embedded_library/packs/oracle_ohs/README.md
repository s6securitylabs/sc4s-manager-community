# Oracle HTTP Server logs pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_ohs`.

This pack is a full catalogue/pack definition, not a validated parser implementation. It is intentionally `catalogued` and `unverified` until exact emitted source shapes, safe fixtures, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_ohs_access_common` — Common Log Format access events
  - Sourcetype target: `oracle:ohs:access:common`
  - Source shape: OHS access log common format
  - Status: Can align with generic web access requirements once LogFormat is selected.
- `oracle_ohs_access_combined` — Combined Log Format access events
  - Sourcetype target: `oracle:ohs:access:combined`
  - Source shape: OHS access log combined format
  - Status: Can align with generic web access requirements once LogFormat is selected.
- `oracle_ohs_error` — OHS error logs
  - Sourcetype target: `oracle:ohs:error`
  - Source shape: OHS error log files
  - Status: Blocked until exact OHS/version error examples exist.
- `oracle_ohs_ebs_forms_reports` — EBS/Forms/Reports OHS component logs
  - Sourcetype target: `oracle:ohs:oracle_apps`
  - Source shape: OHS/WebLogic proxy/Forms/Reports component logs
  - Status: Blocked until source paths/component metadata and examples exist.

## Ingestion and collection notes

This is currently a **catalogue/source-definition pack**, not a deployable parser pack. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `netops`, sourcetype(s) `oracle:ohs:access:common`, `oracle:ohs:access:combined`, `oracle:ohs:error`, `oracle:ohs:oracle_apps`, credential/checkpoint ownership, and any safe ingestion-time transformations.

## Safety / evidence stance

- Source-shape acquisition checklist: `validation/source-shape-acquisition-plan-2026-06-20.md`. This checklist is a blocker-removal plan only, not validation evidence.
- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- No SC4S listener/parser artifacts are shipped for this definition yet.
- `routing_enabled` is false; Manager/SecHub should treat this as catalogue/source-planning coverage, not a deployable parser pack.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.
