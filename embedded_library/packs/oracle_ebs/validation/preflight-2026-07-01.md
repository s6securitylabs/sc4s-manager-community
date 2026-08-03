# Oracle E-Business Suite normalized JSON relay preflight — 2026-07-01

## Scope

This preflight promotes `oracle_ebs` from catalogue-only source-shape planning to a conservative parser-capable SecHub Resources pack for a **site-owned normalized JSON relay**. It responds to Oracle May 2026 EBS advisory activity and the reported active exploitation of CVE-2026-46817 by making operator-useful EBS security/audit fields searchable and dashboardable when a collector emits the documented relay shape.

## What was validated locally

- Synthetic-equivalent fixture corpus has one JSON object per line and unique markers for every declared event family.
- SC4S parser artifact matches only `vendor=oracle`, `product=e_business_suite`, `source_mode=ebs_security_json_relay`, and an `ebs_*` event family.
- Splunk props use JSON search-time extraction and derive common analyst fields without dropping raw context.
- Dashboard SPL uses fields present in fixtures or `spath` extraction.

## What remains blocked

- No live Oracle E-Business Suite instance was queried.
- No native EBS Sign-On Audit, AuditTrail, FND, concurrent manager, workflow, OHS, WebLogic, Forms, OAF, Oracle Payments, ECC, supplier, payroll, or financials emitted record was captured.
- No SC4S TEST -> HEC -> Splunk TEST indexed read-back has been captured for this pack as of this note.
- This pack must remain `curated` / `unverified` until replay/read-back or production-equivalent evidence exists.

## Next IVV path

1. Obtain a sanitized export or lab sample for the selected EBS source-mode rows/logs.
2. Confirm timestamp, timezone, event boundary, field delimiting, multiline policy, and sensitive-value handling.
3. Replay the normalized relay fixture and source-backed samples through the dedicated SC4S listener into Splunk TEST.
4. Read back event count, index, sourcetype, source, host, timestamp, event family, markers, and required fields.
5. Only then consider evidence promotion.
