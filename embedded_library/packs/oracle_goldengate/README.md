# Oracle GoldenGate logs pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_goldengate`.

This pack is a full catalogue/pack definition, not a validated parser implementation. It is intentionally `catalogued` and `unverified` until exact emitted source shapes, safe fixtures, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_goldengate_error_log` — GoldenGate ggserr.log
  - Sourcetype target: `oracle:goldengate:error`
  - Source shape: classic ggserr.log
  - Status: Blocked until exact classic/microservices log examples exist.
- `oracle_goldengate_extract_report` — Extract report files
  - Sourcetype target: `oracle:goldengate:extract:report`
  - Source shape: Extract reports
  - Status: Blocked; reports may be multiline and not continuous syslog.
- `oracle_goldengate_replicat_report` — Replicat report files
  - Sourcetype target: `oracle:goldengate:replicat:report`
  - Source shape: Replicat reports
  - Status: Blocked until report schema/boundary exists.
- `oracle_goldengate_discard_file` — Discard files
  - Sourcetype target: `oracle:goldengate:discard`
  - Source shape: discard files
  - Status: Blocked and sensitive; do not fixture row values without sanitisation.
- `oracle_goldengate_manager_log` — Manager process logs
  - Sourcetype target: `oracle:goldengate:manager`
  - Source shape: Manager logs
  - Status: Blocked until exact process/admin examples exist.
- `oracle_goldengate_microservices_admin` — Microservices admin/service logs
  - Sourcetype target: `oracle:goldengate:microservices:admin`
  - Source shape: REST/admin/service logs
  - Status: Blocked until JSON/text/API shape exists.

## Ingestion and collection notes

This is currently a **catalogue/source-definition pack**, not a deployable parser pack. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `infraops`, sourcetype(s) `oracle:goldengate:error`, `oracle:goldengate:extract:report`, `oracle:goldengate:replicat:report`, `oracle:goldengate:discard`, and 2 more declared sourcetype(s), credential/checkpoint ownership, and any safe ingestion-time transformations.

## Safety / evidence stance

- Source-shape acquisition checklist: `validation/source-shape-acquisition-plan-2026-06-20.md`. This checklist is a blocker-removal plan only, not validation evidence.
- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- No SC4S listener/parser artifacts are shipped for this definition yet.
- `routing_enabled` is false; Manager/SecHub should treat this as catalogue/source-planning coverage, not a deployable parser pack.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.
