# Oracle Exadata engineered systems logs source-shape acquisition plan — 2026-06-20

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

### `oracle_exadata_cell_alert`
- Capture CellCLI alert-history/export rows or cell alert files from a known Exadata generation.
- Preserve cell/node identity, alert type, severity, metric/object, timestamp/timezone, and clear/active state.

### `oracle_exadata_cell_syslog`
- Capture representative storage-cell syslog lines with component/program names and severity vocabulary.
- Preserve RFC3164/RFC5424/headerless envelope, event boundary, and source host behavior.

### `oracle_exadata_ilom_switch`
- Capture ILOM/service-processor and RoCE/InfiniBand switch events only for the exact hardware/source mode selected.
- Preserve hardware object, port/link/disk/fan/power context, state/result, and timestamp.

### `oracle_exadata_exachk_exawatcher_asr`
- Capture EXAchk/ORAchk, ExaWatcher/OSWatcher, or ASR report/API/export schemas before declaring report-family fixtures.
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
