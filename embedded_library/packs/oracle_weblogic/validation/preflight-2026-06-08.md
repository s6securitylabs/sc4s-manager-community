# Validation preflight — oracle_weblogic — 2026-06-08

Status: blocked / not run.

This pack definition records Oracle source-family coverage and source-shape requirements. It does not ship SC4S parser artifacts or fixtures, and no listener replay, HEC delivery, Splunk indexed read-back, Manager collector read-back, or production-equivalent validation has been performed.

Blocker layer: source_mapping.

Required next evidence before promotion:

- exact product/version/source mode for the selected variant;
- raw/structured format and collector envelope;
- event boundary, record separator, uniqueness, multiline behaviour, delimiting, and timezone policy;
- safe sanitised sample or synthetic-equivalent fixture derived from exact emitted shape;
- replay/read-back or collector/import/read-back evidence proving event count, index/source/sourcetype, timestamps, and required fields.
