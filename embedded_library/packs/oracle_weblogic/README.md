# Oracle WebLogic Server logs pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_weblogic`.

This pack is a conservative source definition with a narrow fixture-backed server/access relay alpha slice, not a validated parser implementation. It is intentionally `curated` and `unverified` until product-generated source shapes, safe fixtures for the remaining variants, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_weblogic_server` — Server/domain log events
  - Sourcetype target: `oracle:weblogic:server`
  - Source shape: server/domain log file tail or collector relay
  - Status: Fixture-backed alpha relay slice shipped (synthetic-equivalent fixtures only); product-generated samples and replay/read-back still required.
- `oracle_weblogic_access` — HTTP access logs
  - Sourcetype target: `oracle:weblogic:access`
  - Source shape: access log file tail/collector relay
  - Status: Fixture-backed alpha relay slice shipped for common log format; administrator-configured field orders and product-generated samples still required.
- `oracle_weblogic_audit` — Security/audit provider events
  - Sourcetype target: `oracle:weblogic:audit`
  - Source shape: security audit provider/server security events
  - Status: Blocked until exact audit provider output examples exist.
- `oracle_weblogic_node_manager` — Node Manager lifecycle logs
  - Sourcetype target: `oracle:weblogic:nodemanager`
  - Source shape: node manager log files
  - Status: Blocked until exact emitted examples exist.
- `oracle_fusion_middleware` — Fusion Middleware SOA/OSB/BPM diagnostics
  - Sourcetype target: `oracle:fusion_middleware:diagnostic`
  - Source shape: SOA Suite, Service Bus, BPM diagnostic/audit/invocation logs
  - Status: Blocked until exact emitted examples exist.

## Ingestion and collection notes

This is a conservative source-definition pack with a narrow fixture-backed alpha SC4S/Splunk relay slice for server/access logs. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `infraops` (the SC4S relay default; the Splunk universal-forwarder examples in `splunk/default/inputs.conf.example` target a dedicated `oracle` index instead — pick one local index story before onboarding), sourcetype(s) `oracle:weblogic:server`, `oracle:weblogic:access`, `oracle:weblogic:audit`, `oracle:weblogic:nodemanager`, and 1 more declared sourcetype(s), credential/checkpoint ownership, and any safe ingestion-time transformations.

## Source-shape acquisition plan

The 2026-06-20 acquisition plan is recorded at `validation/source-shape-acquisition-plan-2026-06-20.md`. It confirms that public Oracle documentation supports source-shape planning for WebLogic server/domain logs (`####` plus angle-bracket attributes) and HTTP access logs, but it does **not** provide redistributable fixtures or a proven native syslog/SC4S relay envelope. Use that plan as the checklist for lab capture, collector-envelope capture, sanitisation, and replay/read-back requirements before authoring real fixtures.

## Safety / evidence stance

- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- SC4S/Splunk artifacts are shipped only for the alpha server/access relay slice; audit provider, Node Manager, and Fusion Middleware remain catalogue-only.
- `routing_enabled` is true only for the fixture-backed server/access relay slice; Manager/SecHub must not treat this as ready for operational trust or source validation.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.

## 2026-07-01 fixture-backed alpha slice

This pack now includes a narrow WebLogic server/access relay slice for fixture validation: `test-events/oracle_weblogic_server_access.txt`, SC4S routing metadata for TCP/20102, and Splunk search-time extractions for `oracle:weblogic:server` and `oracle:weblogic:access`. The fixtures are synthetic-equivalent records derived from public source-shape evidence; they are not real WebLogic estate logs and not copied from Elastic/Oracle sources.

Status remains **Alpha / unverified** for server/access relay and **catalogue-only** for audit provider, Node Manager, and Fusion Middleware variants. No live WebLogic, SC4S replay, HEC delivery, or Splunk indexed read-back has passed. This is not Beta and has no operational trust claim.

## 2026-07-03 onboarding dashboard

`splunk/default/data/ui/views/oracle_weblogic_server_access_overview.xml` is a Simple XML dashboard scoped only to the fixture-backed `oracle:weblogic:server` and `oracle:weblogic:access` sourcetypes. Panels cover server severity/attention counts, security/authentication subsystem events, managed-server/machine activity, HTTP status distribution, top URIs/clients, fixture-marker onboarding coverage, and a raw drilldown. Every panel reads only fields that the shipped search-time extractions produce from the synthetic-equivalent fixtures. The dashboard is an onboarding/triage aid and SPL-quality reference only; it is not exploit detection, not native WebLogic validation, and not read-back evidence. Security Audit provider, Node Manager, and Fusion Middleware panels are deliberately omitted because those variants remain blocked without source-shape evidence.

## 2026-07-06 Splunk onboarding guidance

`docs/collection/oracle-fmw-weblogic-soa-discoverer-splunk-onboarding.md` and `splunk/default/inputs.conf.example` add disabled, conservative collection examples for WebLogic server/access, audit provider, Node Manager, Fusion Middleware diagnostic/ODL, SOA audit/export handoff, and Discoverer legacy logs. These are operator scaffolds only; only the existing WebLogic server/access alpha slice has local synthetic-equivalent parser/dashboard artifacts, and no FMW lane is promoted without replay/read-back.

## 2026-07-02 demo-lab acquisition path

`validation/demo-lab-data-acquisition-plan-2026-07-02.md` records the current free/developer lab-data options. The preferred path is Oracle WebLogic Server in a disposable Oracle container/domain lab, generating and sanitising our own server/domain and access logs. Public MIT/BSD samples remain useful source-shape evidence, but product-generated replay/read-back is still required before any validation or trust promotion.
