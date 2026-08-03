# Oracle Identity and Directory logs pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_identity`.

This pack is a full catalogue/pack definition, not a validated parser implementation. It is intentionally `catalogued` and `unverified` until exact emitted source shapes, safe fixtures, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_oam_audit` — Oracle Access Manager audit
  - Sourcetype target: `oracle:identity:oam:audit`
  - Source shape: OAM authn/authz/session/admin audit
  - Status: Blocked until exact OAM file/table/syslog/export shape and audit level exist.
- `oracle_oam_webgate` — OAM WebGate enforcement/access logs
  - Sourcetype target: `oracle:identity:oam:webgate`
  - Source shape: WebGate access/enforcement logs
  - Status: Blocked until exact format and protected-resource fields exist.
- `oracle_oig_audit` — Oracle Identity Governance audit
  - Sourcetype target: `oracle:identity:oig:audit`
  - Source shape: OIG provisioning/admin/reconciliation audit/export
  - Status: Blocked until exact export/log shape and actor/target semantics exist.
- `oracle_oid_access` — Oracle Internet Directory LDAP access
  - Sourcetype target: `oracle:directory:oid:access`
  - Source shape: OID access logs
  - Status: Blocked until bind/search/modify result examples exist.
- `oracle_oid_audit` — OID audit/admin logs
  - Sourcetype target: `oracle:directory:oid:audit`
  - Source shape: OID audit logs
  - Status: Blocked until admin/change audit examples exist.
- `oracle_oud_access` — Oracle Unified Directory LDAP access
  - Sourcetype target: `oracle:directory:oud:access`
  - Source shape: OUD access logs
  - Status: Blocked until exact OUD access records exist.
- `oracle_oud_audit` — OUD audit/admin logs
  - Sourcetype target: `oracle:directory:oud:audit`
  - Source shape: OUD audit/admin logs
  - Status: Blocked until audit/admin examples exist.

## Ingestion and collection notes

This is currently a **catalogue/source-definition pack**, not a deployable parser pack. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `netauth`, sourcetype(s) `oracle:identity:oam:audit`, `oracle:identity:oam:webgate`, `oracle:identity:oig:audit`, `oracle:directory:oid:access`, and 3 more declared sourcetype(s), credential/checkpoint ownership, and any safe ingestion-time transformations.

## Safety / evidence stance

- Source-shape acquisition checklist: `validation/source-shape-acquisition-plan-2026-06-20.md`. This checklist is a blocker-removal plan only, not validation evidence.
- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- No SC4S listener/parser artifacts are shipped for this definition yet.
- `routing_enabled` is false; Manager/SecHub should treat this as catalogue/source-planning coverage, not a deployable parser pack.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.
