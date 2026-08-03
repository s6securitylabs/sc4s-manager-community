# Edge Processor preflight: `zeek_json_routine_conn_reduce`

Status: **not validated in Splunk Edge Processor**. This note is a required guardrail for the candidate artifacts only; it is not replay/read-back evidence and does not promote pack trust or quality.

Required before enabling any lossy behavior:

1. Preview the SPL2 module in Splunk Edge Processor with representative sample events and confirm parser/field references are valid for the deployed source shape.
2. Install/enable in a non-production route with `$source` and `$destination` bound to the local source and destination.
3. Replay the pack sample plus representative production-equivalent records.
4. Read back from Splunk and verify event counts, index `netids`, sourcetypes/source, timestamps, required normalized fields, and raw context retention.
5. Compare detections, dashboards, accelerated data models, and notable-event searches before/after reduction.
6. Document approved predicates, expected reduction percentage, owners, time window, and rollback trigger.

Rollback:

- Disable/detach this Edge Processor pipeline template.
- Route the source directly to the original destination/index.
- Replay held-out samples and verify full-fidelity ingestion/read-back has resumed.
