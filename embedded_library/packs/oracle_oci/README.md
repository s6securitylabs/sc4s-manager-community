# Oracle Cloud Infrastructure audit and logging pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_oci`.

This pack is a full catalogue/pack definition, not a validated parser implementation. It is intentionally `catalogued` and `unverified` until exact emitted source shapes, safe fixtures, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_oci_audit` — OCI Audit control-plane events
  - Sourcetype target: `oracle:oci:audit`
  - Source shape: OCI Audit API, Service Connector Hub, Object Storage/Streaming/collector JSON relay
  - Status: Public OCI Audit schema supports source definition; service-specific data payload parsing remains blocked until examples exist.
- `oracle_oci_logging` — OCI Logging generic envelope
  - Sourcetype target: `oracle:oci:logging`
  - Source shape: OCI Logging record envelope or collector JSON relay
  - Status: Generic envelope only; source-specific logs blocked until exact payload examples.
- `oracle_oci_vcn_flow` — VCN Flow Logs
  - Sourcetype target: `oracle:oci:vcn:flow`
  - Source shape: OCI VCN flow log records
  - Status: Blocked until exact VCN flow record shape/version selected.
- `oracle_oci_waf` — OCI WAF logs
  - Sourcetype target: `oracle:oci:waf`
  - Source shape: WAF log/event payloads
  - Status: Blocked until exact WAF payload examples exist.
- `oracle_oci_cloud_guard` — Cloud Guard detector/problem events
  - Sourcetype target: `oracle:oci:cloudguard`
  - Source shape: Cloud Guard findings/problems
  - Status: Blocked until detector/problem schema examples exist.
- `oracle_oci_bastion` — OCI Bastion session/control events
  - Sourcetype target: `oracle:oci:bastion`
  - Source shape: Bastion session/control audit
  - Status: Blocked until exact session/control event examples exist.
- `oracle_oci_object_storage` — Object Storage activity
  - Sourcetype target: `oracle:oci:objectstorage`
  - Source shape: Object/bucket activity logs/audit
  - Status: Blocked until source shape confirmed.
- `oracle_oci_load_balancer` — Load Balancer logs
  - Sourcetype target: `oracle:oci:loadbalancer`
  - Source shape: load balancer access/security records
  - Status: Blocked until access/security format examples exist.

## Ingestion and collection notes

This is currently a **catalogue/source-definition pack**, not a deployable parser pack. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `main`, sourcetype(s) `oracle:oci:audit`, `oracle:oci:logging`, `oracle:oci:vcn:flow`, `oracle:oci:waf`, and 4 more declared sourcetype(s), credential/checkpoint ownership, and any safe ingestion-time transformations.

## Source-shape acquisition plan

A concrete acquisition checklist is now recorded in `validation/source-shape-acquisition-plan-2026-06-20.md`. It documents the acceptable evidence needed before authoring OCI fixtures for Audit, Logging, VCN Flow, WAF, Cloud Guard, Bastion, Object Storage, or Load Balancer variants; it also records that a previously guessed VCN flow-log documentation URL returned HTTP 404 from this runtime.

Use that plan as a blocker-removal checklist only. It is not replay/read-back evidence and does not make this pack deployable.

## Safety / evidence stance

- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- No SC4S listener/parser artifacts are shipped for this definition yet.
- `routing_enabled` is false; Manager/SecHub should treat this as catalogue/source-planning coverage, not a deployable parser pack.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.
