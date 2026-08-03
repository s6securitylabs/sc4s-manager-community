# Oracle Database source-shape acquisition plan — 2026-06-20

## Purpose

This note turns the current Oracle Database catalogue-only blocker into a concrete evidence-acquisition checklist. It is not validation evidence, does not contain Oracle event samples, and must not be used to promote `quality_status`, `trust_level`, `review_status`, or downloadability.

The `oracle_database` pack remains routing-disabled and catalogue-only until one variant has exact emitted-record evidence, safe fixtures, and replay/read-back or collector read-back.

## Acceptable evidence for fixture authoring

For a selected Oracle Database variant, collect one of the following before writing parser fixtures:

1. **Sanitized lab export from a known Oracle Database version**
   - Record database version, CDB/PDB mode, audit configuration, timezone settings, and collector/export command.
   - Preserve one row/record boundary exactly as emitted by the export or collector.
   - Sanitize users, hosts, IPs, SQL text/binds, service names, database names, paths, and business object values while preserving field names, delimiters, nulls, quoting, arrays, and timestamp format.
2. **Vendor-certified or documented exact emitted example**
   - Must show a complete record, not just a column dictionary.
   - Must include redistribution/licence posture or be summarized into synthetic-equivalent rows without copying restricted sample text.
3. **Collector output with raw source row retained**
   - JSON/CSV/syslog/CEF/HEC wrappers are acceptable only when the collector envelope and the embedded Oracle row are both captured.
   - The fixture must state whether SC4S sees the collector wrapper, the raw Oracle row, or both.

Column references such as `UNIFIED_AUDIT_TRAIL` or `V$DIAG_ALERT_EXT` are sufficient for field planning, but not by themselves sufficient for parser fixtures because they do not prove export serialization, record boundaries, timestamp rendering, null handling, or collector envelope.

## Variant-specific unblock checklist

### `oracle_database_unified_audit`

Minimum capture:

- Oracle Database version and audit policy scope.
- Export/query shape for at least successful privileged action, failed logon or denied action, and object access where policy allows.
- Required fields to preserve when present: `EVENT_TIMESTAMP`, database user, proxy user, OS user, action name/code, object schema/name, system privilege, return code, client host/IP, service/module/program, CDB/PDB/container context, and SQL text/binds handling policy.
- Timestamp timezone behavior for `EVENT_TIMESTAMP` and any collector-added time.

### `oracle_database_traditional_audit`

Minimum capture:

- Selected source mode: `DBA_AUDIT_TRAIL`/`SYS.AUD$` export or OS audit file.
- At least one success and one failure/return-code row.
- Field/null/quoting behavior for user, action, object, privilege, client/program/module, terminal, and timestamp.
- Explicit statement whether SYSDBA/OS audit records are in the same stream or a separate variant.

### `oracle_database_fga`

Minimum capture:

- FGA policy definition and one emitted audit row for the policy.
- Sanitized SQL/predicate/bind handling that preserves structure without exposing business data.
- Object, policy, user/client, timestamp, and statement context fields.

### `oracle_database_listener`

Minimum capture:

- Exact `listener.log` or ADR listener text/XML lines from standalone plus RAC/SCAN/TCPS if those are stated.
- At least one successful connect and one failed/refused/error case.
- Event boundary, multiline behavior, timestamp timezone, client address/service/SID/connect-data shape, and result/status token.

### `oracle_database_alert_adr`

Minimum capture:

- Chosen source mode: raw alert log text, ADR `log.xml`, or `V$DIAG_ALERT_EXT` export.
- At least one ORA/error/incident-style message and one non-error lifecycle/operational message if both are in scope.
- Multiline boundaries for raw alert logs, XML element boundaries for ADR XML, or row serialization for view exports.
- Severity/message type/component/incident/problem-key preservation where present.

### `oracle_database_rac_grid_asm`

Minimum capture:

- Exact Clusterware/CRS/CSS/OHASD/ASM/SCAN listener source file or export mode.
- At least one resource/service state transition and one error/failure/quorum/fencing-style event if stated.
- Node, cluster, resource, disk group, service, timestamp, severity, and state/result tokens.

## Minimum implementation gate after evidence arrives

Before this source definition becomes a deployable pack, update all of the following together:

- Replace placeholder fixture rows with sanitized/synthetic-equivalent records for the selected variant only.
- Add SC4S/parser or collector-relay artifacts only for the proven envelope.
- Update `source_delivery`, `pack_variants`, `event_families`, `test_event_sets`, `validation_harness`, README, artifact hashes, and known limitations.
- Keep trust conservative (`catalogued` or `curated`, `unverified`) until replay/read-back or production-equivalent evidence passes.
- Run focused marker/family/hash checks and `scripts/run_ci.sh`.

## Rejected shortcuts

Do not unblock fixtures from any of these alone:

- Oracle table/view column dictionaries without an emitted export format.
- Upstream parser presence or generic SIEM field mappings.
- Screenshots or blog prose that omit full record boundaries.
- Invented JSON wrappers around Oracle columns.
- CI/schema success, placeholder test events, or blocked preflight notes.
