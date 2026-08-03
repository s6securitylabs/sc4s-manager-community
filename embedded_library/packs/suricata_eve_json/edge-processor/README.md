# Splunk Edge Processor templates for `suricata_eve_json`

This directory contains file-backed SPL2 module candidates and metadata for optional Splunk Edge Processor pipeline templates.

Current template:

- `suricata_eve_flow_reduce`: Suricata EVE flow/stat reduction candidate.

Status: candidate only. These artifacts have not been validated in Splunk Edge Processor and must not be enabled as lossy reduction without preview, non-production replay/read-back, detection impact review, and rollback approval.

Directory shape:

- `modules/`: SPL2 pipeline module candidates.
- `templates/`: JSON metadata describing source-type definitions, transforms, destinations, lossy behavior, validation, and rollback.
- `samples/`: synthetic-equivalent raw and parsed sample snippets for review.
- `validation/`: preflight checklist and current validation gap.
