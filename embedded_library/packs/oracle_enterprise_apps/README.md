# Oracle enterprise application logs pack definition

Conservative SecHub Resources / Manager / SecHub source definition for `oracle_enterprise_apps`.

This pack is a full catalogue/pack definition, not a validated parser implementation. It is intentionally `catalogued` and `unverified` until exact emitted source shapes, safe fixtures, and replay/read-back evidence exist.

## Source-family coverage
- `oracle_peoplesoft_signon_audit` — PeopleSoft signon/authentication audit
  - Sourcetype target: `oracle:peoplesoft:signon:audit`
  - Source shape: PSPTLOGINAUDIT / PSACCESSLOG database tables (DB export)
  - Status: Catalogue-only — DB tables, not emitted logs; PSPTLOGINAUDIT is volatile. Needs collector export schema + read-back.
- `oracle_peoplesoft_security_audit` — PeopleSoft security audit
  - Sourcetype target: `oracle:peoplesoft:security:audit`
  - Source shape: PSAUDIT / record / DB-level trigger audit tables (DB export)
  - Status: Catalogue-only — DB tables/triggers, not emitted logs. Needs collector export schema + read-back.
- `oracle_peoplesoft_appserver` — PeopleSoft application server logs
  - Sourcetype target: `oracle:peoplesoft:appserver`
  - Source shape: APPSRV.LOG server-process log + Tuxedo ULOG (file tail)
  - Status: Promotable-with-sample — documented single-line grammar; needs a sanitised sample to lock separator/timestamp before a parser.
- `oracle_peoplesoft_process_scheduler` — PeopleSoft process scheduler
  - Sourcetype target: `oracle:peoplesoft:process_scheduler`
  - Source shape: SCHDLR.LOG server-process log (file tail)
  - Status: Promotable-with-sample — same server-process framework; confirm layout with a fixture. Failure status lives in DB tables.
- `oracle_peoplesoft_integration_broker` — PeopleSoft Integration Broker
  - Sourcetype target: `oracle:peoplesoft:integration_broker`
  - Source shape: IB dispatcher logs (file tail) + gateway msgLog/errorLog.html
  - Status: Dispatcher logs fold into the app-server grammar; gateway HTML logs blocked (undocumented grammar).
- `oracle_jde_security_server` — JD Edwards Security Server
  - Sourcetype target: `oracle:jde:security_server`
  - Source shape: JDE Security Server/kernel logs
  - Status: Blocked until auth/security event examples exist.
- `oracle_jde_enterprise_server` — JD Edwards Enterprise Server
  - Sourcetype target: `oracle:jde:enterprise_server`
  - Source shape: Enterprise Server/kernel logs
  - Status: Blocked until component/kernel examples exist.
- `oracle_jde_html_server` — JD Edwards HTML server
  - Sourcetype target: `oracle:jde:html_server`
  - Source shape: HTML server/web-tier logs
  - Status: Blocked; partial coverage only via generic web/WebLogic/OHS if format matches.
- `oracle_jde_batch_jobs` — JD Edwards batch jobs
  - Sourcetype target: `oracle:jde:batch_jobs`
  - Source shape: batch/job execution logs
  - Status: Blocked until job/export shape and parameter redaction exist.
- `oracle_siebel_audit_trail` — Siebel Audit Trail
  - Sourcetype target: `oracle:siebel:audit_trail`
  - Source shape: Siebel audit trail table/export
  - Status: Blocked until audit trail shape and sensitive value handling exist.
- `oracle_siebel_component_log` — Siebel component/Object Manager logs
  - Sourcetype target: `oracle:siebel:component`
  - Source shape: component logs
  - Status: Blocked until component log examples exist.
- `oracle_siebel_gateway` — Siebel Gateway/name server logs
  - Sourcetype target: `oracle:siebel:gateway`
  - Source shape: gateway/name server logs
  - Status: Blocked until lifecycle/admin examples exist.
- `oracle_siebel_web_swse` — Siebel SWSE/web logs
  - Sourcetype target: `oracle:siebel:web`
  - Source shape: SWSE/web logs
  - Status: Blocked; partial coverage only via generic web pack if format matches.

## 2026-07-03 PeopleSoft source-shape evidence pass

`docs/research/oracle-official-peoplesoft-log-source-shape-evidence-20260703.md` records an Oracle-official evidence pass for the PeopleSoft family. Summary:

- **Promotable-with-sample (file-tail, documented single-line grammar; no native syslog):** `oracle:peoplesoft:appserver` (APPSRV.LOG, strongest) and `oracle:peoplesoft:process_scheduler` (SCHDLR.LOG), with Tuxedo ULOG as an app-server companion and Integration Broker dispatcher logs folding into the same server-process grammar. A real sanitised sample is still required to lock the configurable field separator and confirm placeholder/timestamp behaviour.
- **Catalogue-only (database tables, DB export — not logs):** `oracle:peoplesoft:signon:audit` (PSPTLOGINAUDIT/PSACCESSLOG; PSPTLOGINAUDIT is volatile — success clears failure rows) and `oracle:peoplesoft:security:audit` (PSAUDIT / record / DB-level trigger audit). The Integration Broker **gateway** msgLog/errorLog.html sub-source stays blocked (HTML, undocumented per-entry grammar).
- **Redirect, don't duplicate:** PIA web-tier logs → `packs/oracle_weblogic` / `packs/oracle_ohs`.
- **Scope:** PeopleSoft stays inside this pack (no standalone pack). JD Edwards and Siebel follow the same pattern — file-tailable operational logs, DB-table-based security/audit — and remain catalogue-only here; Oracle Enterprise Manager has its own `packs/oracle_oem`.

Routing stays disabled and trust stays `unverified`: the server-process grammar is documented well enough to draft a parser, but no sanitised sample or live SC4S TEST -> HEC -> Splunk TEST read-back has been captured.

## Ingestion and collection notes

This is currently a **catalogue/source-definition pack**, not a deployable parser pack. Ingestion normally depends on the source family: API/table exports, audit/report jobs, application log files, database views, object-store drops, or ZIP/TGZ/CSV/JSON exports gathered by a collector. Before promoting this to a runtime pack, capture the exact emitted record shape, export envelope, record boundary, timestamp policy, and field dictionary.

Use a collector or staging process to unpack archives, split multi-record files, preserve raw rows/records, and attach source metadata. Do not invent SC4S routing, dashboards, or parser behavior until source-shape evidence and representative test events exist. Candidate data should remain conservative/catalogued and unverified until replay/read-back or equivalent evidence is captured.

When this source is implemented as an operational pack, document the chosen pull/push path, index target `main`, sourcetype(s) `oracle:peoplesoft:signon:audit`, `oracle:peoplesoft:security:audit`, `oracle:peoplesoft:appserver`, `oracle:peoplesoft:process_scheduler`, and 9 more declared sourcetype(s), credential/checkpoint ownership, and any safe ingestion-time transformations.

## Safety / evidence stance

- Source-shape acquisition checklist: `validation/source-shape-acquisition-plan-2026-06-20.md`. This checklist is a blocker-removal plan only, not validation evidence.
- No real Oracle tenant, user, host, OCID, APPS schema, customer, employee, financial, SQL bind, request parameter, or proprietary sample data is included.
- No SC4S listener/parser artifacts are shipped for this definition yet.
- `routing_enabled` is false; Manager/SecHub should treat this as catalogue/source-planning coverage, not a deployable parser pack.
- Promotion requires exact source-shape evidence plus replay/read-back or collector read-back evidence for the selected variant.
