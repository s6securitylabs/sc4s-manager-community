# Oracle Enterprise Manager Cloud Control logs source-shape acquisition plan — 2026-06-20

## Purpose

This note turns the current catalogue-only Oracle blocker into a concrete evidence-acquisition checklist. It is not validation evidence, does not contain Oracle event samples, and must not be used to promote `quality_status`, `trust_level`, `review_status`, or downloadability.

The pack remains routing-disabled and catalogue-only until one selected variant has exact emitted-record evidence, safe fixtures, and replay/read-back or collector read-back.

## Acceptable evidence for fixture authoring

For a selected variant, collect one of the following before writing parser fixtures:

1. **Sanitized lab export from a known product/source version**
   - Record product version, component, source file/table/API/report, timezone settings, collector/export command, and record-boundary rule.
   - Sanitize users, hosts, IPs, OCIDs, database/application names, paths, SQL/business values, request parameters, and customer identifiers while preserving field names, delimiters, nulls, quoting, arrays, and timestamp format.
2. **Vendor-certified or documented exact emitted example**
   - Must show a complete record, not just a column dictionary or feature description.
   - Must include redistribution/licence posture or be summarized into synthetic-equivalent rows without copying restricted sample text.
3. **Collector output with raw source row retained**
   - JSON/CSV/syslog/CEF/HEC wrappers are acceptable only when the collector envelope and embedded Oracle row are both captured.
   - The fixture must state whether SC4S/Manager sees the wrapper, the raw Oracle row, or both.

Column lists, product feature docs, upstream parser names, screenshots, or generic SIEM mappings are useful for planning but are not enough for fixtures because they do not prove export serialization, record boundaries, timestamp rendering, null handling, or collector envelope.

## Variant-specific unblock checklist

### `oracle_oem_admin_audit`
- Capture Cloud Control admin/audit rows for login, privilege/role change, target change, and job submission.
- Preserve administrator, target name/type, job/incident identifiers, operation/result, source IP, and timestamp.

### `oracle_oem_incident_job_agent`
- Capture incident, job execution, agent/OMS, or target-status export rows only for a selected report/API/source file.
- Preserve severity/status, target identity, metric/finding/check IDs, lifecycle state, and collector/export envelope.

### `oracle_oem_repository_export`
- If using repository SQL exports, capture the exact CSV/JSON serialization and null/quoting behavior before fixtures.
## Minimum implementation gate after evidence arrives

Before this source definition becomes a deployable pack, update all of the following together:

- Replace placeholder fixture rows with sanitized/synthetic-equivalent records for the selected variant only.
- Add SC4S/parser or collector-relay artifacts only for the proven envelope.
- Update `source_delivery`, `pack_variants`, `event_families`, `test_event_sets`, `validation_harness`, README, artifact hashes, and known limitations.
- Keep trust conservative (`catalogued` or `curated`, `unverified`) until replay/read-back or production-equivalent evidence passes.
- Run focused marker/family/hash checks and `scripts/run_ci.sh`.

## Rejected shortcuts

Do not unblock fixtures from any of these alone:

- Oracle table/view/API field dictionaries without an emitted export format.
- Upstream parser presence or generic SIEM field mappings.
- Screenshots or blog prose that omit full record boundaries.
- Invented JSON wrappers around Oracle columns.
- CI/schema success, placeholder test events, or blocked preflight notes.
