# Oracle EBS / OLM / APEX / ECC collection evidence for Splunk onboarding — 2026-07-06

- **Title:** Oracle EBS application-family collection evidence for conservative Splunk onboarding
- **Publisher / organisation:** Oracle documentation, Oracle eTRM public table documentation, Splunk public app/docs metadata
- **Original URLs:** listed in `docs/collection/oracle-ebs-app-family-splunk-onboarding.md` and summarized below
- **Publication date:** various Oracle/Splunk documentation dates; exact page dates not consistently available from public pages
- **Access date:** 2026-07-06
- **Licence / terms:** Oracle and Splunk pages are referenced and summarized only. No proprietary documentation bodies, screenshots, Oracle samples, Splunk TA code, dashboards, or app content are copied.

## Purpose

This note records the evidence boundary behind `splunk/default/inputs.conf.example` and `docs/collection/oracle-ebs-app-family-splunk-onboarding.md`. It focuses on EBS-family application sources requested for Splunk onboarding: Oracle E-Business Suite, Oracle Learning Management (OLM), Oracle APEX, and Oracle Enterprise Command Center (ECC).

## Findings

### EBS base security/audit sources

Existing pack research already supports the normalized relay model for Sign-On Audit, AuditTrail, FND/OAF logging, concurrent request metadata, workflow/mailer context, OHS/WebLogic/Forms/OAF adjacency, and advisory-focus EBS modules. The key boundary remains unchanged: public Oracle docs and eTRM pages support source-family planning, but do not provide a universal native EBS emitted log grammar.

Operational implication: keep `oracle:ebs:security:json` as a site-owned normalized JSON relay, not a claim of native EBS parser validation.

### Oracle Learning Management (OLM)

Oracle OLM public docs establish OLM as an EBS application area. Public eTRM pages expose OLM/OTA database tables such as `OTA_DELEGATE_BOOKINGS` and `OTA_EVENTS`. These pages justify planning OLM table/export collection and AuditTrail/FND/concurrent correlation, but they do not prove:

- a universal emitted log line format;
- a standard security-event field dictionary;
- safe joins from learner/enrollment/content records to users/responsibilities;
- PII-safe collection or masking rules.

Operational implication: use DB Connect or a site-owned scheduled export/relay for approved OLM tables, AuditTrail rows, concurrent requests, and workflow context. Keep example file monitors limited to staged JSONL exports, disabled by default.

### Oracle APEX

Oracle APEX documentation for `APEX_ACTIVITY_LOG` states that application logging can be enabled and that the activity view can be queried for current-workspace activity. The documented page includes field-level activity context such as user/session/application/page, elapsed timing, SQL error fields, and a caveat that IP address/user-agent are only retained in selected entries to conserve space. Oracle APEX debug-message docs describe viewing, querying, and purging debug messages and note debug-session retention/age-out behavior.

Operational implication: APEX collection is database/view/export collection, not a generic file-tail source. DB Connect or a controlled scheduled export can be used, but collection scope, checkpoints, app/workspace filtering, retention, and debug sensitivity are local controls.

### Oracle Enterprise Command Center (ECC)

Oracle EBS Enterprise Command Centers administration/diagnostic docs identify installation and diagnostic logging sources including `import.log`, setup log, domain log, Oracle Enterprise Command Center Framework log, data-load tracking, concurrent program logs, and debug log level for data loads. The docs also describe data-load tracking fields such as run/load/application/dataset/status-style context at a functional level.

Operational implication: ECC has enough official evidence to name conservative monitor categories and staged export categories, but not enough to implement a native parser. Exact ECC Server/Framework paths, domain layout, multiline behavior, and line grammar must be captured locally before enabling monitors.

### Splunk TA / ecosystem check

Existing EBS research recorded public metadata checks for Splunkbase Oracle Database, DB Connect, Oracle JDBC, and related Oracle database audit apps. This pass found no public, vendorable Splunk TA content for native EBS/OLM/APEX/ECC application-security parsers that should be copied into SecHub Resources. Splunk DB Connect remains a reasonable collection mechanism reference for Oracle table/view sources; Splunk Add-on for Oracle Database remains adjacent database-audit coverage, not application-family validation.

## Pack changes justified by this evidence

- Add `splunk/default/inputs.conf.example` with disabled, placeholder-only stanzas for:
  - TCP normalized JSON relay on port `20104`;
  - example EBS concurrent/app-tier raw file monitors with redirect notes;
  - ECC import/framework/data-load raw log monitors;
  - APEX activity/debug staged JSONL exports;
  - OLM audit/activity staged JSONL exports.
- Add `docs/collection/oracle-ebs-app-family-splunk-onboarding.md` with operator guidance, official/custom boundaries, source-to-sourcetype planning, and enablement gates.

These changes do **not** promote `trust_level`, `quality_status`, validation, or field validation.

## Remaining blockers

- Source-backed sanitized records for each source mode.
- Exact local paths and glob constraints for EBS/ECC file monitors.
- Approved DB Connect SQL/checkpoint definitions for OLM and APEX.
- Replay/read-back proof showing event count, index, sourcetype, source, host, timestamps, and required fields.
- Licence review before copying any third-party TA/parser/dashboard implementation.
