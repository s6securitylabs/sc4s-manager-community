# Elastic Oracle database audit source-shape reference — 2026-07-01

Attribution: Elastic `integrations` repository, package `oracle`, data stream `database_audit`, pipeline test file `packages/oracle/data_stream/database_audit/_dev/test/pipeline/test-oracle-database-audit.log`. Accessed 2026-07-01 via GitHub raw content. Repository licence posture: Elastic License 2.0 unless overridden; do **not** vendor Elastic test logs into this AGPL repository.

Use in this pack: source-shape reference only. The fixture file in this pack is synthetic-equivalent and rewritten with documentation-range values and `SYNTH_` markers; it is not a copy of Elastic's test log and not a real Oracle estate sample.

Observed shape summary: multiline Oracle audit-file records begin with a weekday/month timestamp and timezone offset, followed by labelled fields such as `LENGTH`, `ACTION`, `DATABASE USER`, `PRIVILEGE`, `CLIENT USER`, `CLIENT TERMINAL`, `STATUS`, `DBID`, `SESSIONID`, `USERHOST`, `CLIENT ADDRESS`, and `ACTION NUMBER`. Blank lines separate records in the sample.

Evidence boundary: this is enough for conservative synthetic-equivalent audit-file fixtures and search-time extraction checks. It is not enough to claim Unified Audit Trail table-export support, native SC4S validation, or production readiness. Replay/read-back must still prove the selected relay envelope.
