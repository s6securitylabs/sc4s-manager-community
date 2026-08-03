# Oracle Enterprise Manager Cloud Control logs pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_oem`.

This pack is a full catalogue/pack definition, not a validated parser implementation. It is intentionally `catalogued` and `unverified` until exact emitted source shapes, safe fixtures, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_oem_oms_audit` — OMS/admin/user audit
  - Sourcetype target: `oracle:oem:oms:audit`
  - Source shape: OMS audit repository/export/file/API
  - Status: Blocked until exact source shape and actor/source/target semantics exist.
- `oracle_oem_job_execution` — OEM job execution
  - Sourcetype target: `oracle:oem:job`
  - Source shape: job execution logs/exports
  - Status: Blocked until job export/event shape and parameter policy exist.
- `oracle_oem_incident_event` — OEM incidents/alerts/events
  - Sourcetype target: `oracle:oem:incident`
  - Source shape: incident/alert/rule/metric exports
  - Status: Blocked until lifecycle/status shape exists.
- `oracle_oem_agent_log` — OEM Agent logs
  - Sourcetype target: `oracle:oem:agent`
  - Source shape: agent logs
  - Status: Blocked until agent log examples and multiline policy exist.
- `oracle_oem_weblogic_underlay` — OEM WebLogic underlay
  - Sourcetype target: `oracle:oem:weblogic`
  - Source shape: WebLogic logs under OMS
  - Status: Partial only via generic WebLogic where format matches; not OEM validation.

## Ingestion and collection notes

This is currently a **catalogue/source-definition pack**, not a deployable parser pack. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `infraops`, sourcetype(s) `oracle:oem:oms:audit`, `oracle:oem:job`, `oracle:oem:incident`, `oracle:oem:agent`, and 1 more declared sourcetype(s), credential/checkpoint ownership, and any safe ingestion-time transformations.

## Safety / evidence stance

- Source-shape acquisition checklist: `validation/source-shape-acquisition-plan-2026-06-20.md`. This checklist is a blocker-removal plan only, not validation evidence.
- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- No SC4S listener/parser artifacts are shipped for this definition yet.
- `routing_enabled` is false; Manager/SecHub should treat this as catalogue/source-planning coverage, not a deployable parser pack.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.
