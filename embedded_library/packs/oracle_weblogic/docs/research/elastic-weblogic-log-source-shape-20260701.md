# Elastic Oracle WebLogic source-shape reference — 2026-07-01

Attribution: Elastic `integrations` repository, package `oracle_weblogic`, data streams `admin_server`, `managed_server`, and `access`, pipeline test files under `packages/oracle_weblogic/data_stream/*/_dev/test/pipeline/`. Accessed 2026-07-01 via GitHub raw content. Repository licence posture: Elastic License 2.0 unless overridden; do **not** vendor Elastic test logs into this AGPL repository.

Use in this pack: source-shape reference only. The fixture file in this pack is synthetic-equivalent and rewritten with documentation-range hosts/IPs and `SYNTH_`/marker values; it is not a copy of Elastic's test logs and not a real WebLogic estate sample.

Observed shape summary: WebLogic server records begin `####<timestamp>` followed by angle-bracket fields including severity, subsystem, machine, server, thread, user/transaction/diagnostic fields, millisecond raw time, attribute map, message ID, and message text. HTTP access records use a common-log-like line with client IP, timestamp, quoted request, status, and bytes.

Evidence boundary: enough for conservative synthetic-equivalent server/access fixtures and search-time extraction checks. It is not native WebLogic syslog proof, not Security Audit provider proof, and not replay/read-back validation.
