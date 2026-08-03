# Oracle Database Unified Audit source-shape references — 2026-07-01

Attribution:

- `sarat1kyan/oralunk`, `TA-oracle-db-exadata/default/transforms.conf` and `default/props.conf`, accessed 2026-07-01. Repository licence: MIT. Use: parser-shape reference for Oracle Unified Audit syslog-style field layout; no raw estate samples copied.
- Oracle Database 19c documentation for unified audit syslog / Windows Event Viewer field mapping and `UNIFIED_AUDIT_TRAIL`, accessed 2026-07-01. Oracle documentation is copyrighted; use only as factual field/source-behaviour reference. Do not copy Oracle prose, tables, or examples into fixtures.
- `tmuth/splunking-oracle` Unified Audit query/test-policy material, accessed 2026-07-01. No licence detected. Use for planning only, not redistributable fixture or parser content.

Use in this pack: source-shape reference only. The fixture in `test-events/oracle_database_unified_audit_syslog.txt` is synthetic-equivalent with documentation-range values and explicit `SC4S_...TEST...` markers. It is not a copy of Oracle docs, oralunk parser content, or any customer/estate sample.

Observed shape summary: Oracle Unified Audit syslog-style messages are expected to carry an Oracle Unified Audit prefix followed by labelled fields such as `LENGTH`, `TYPE`, `DBID`, `SESID`, `CLIENTID`, `ENTRYID`, `STMTID`, `DBUSER`, `CURUSER`, `ACTION`, `RETCODE`, `SCHEMA`, `OBJNAME`, and optionally PDB/container identifiers.

Evidence boundary: this supports a conservative synthetic-equivalent source-shape fixture for future parser work. It does not prove native SC4S routing, Splunk sourcetype extraction, or live Oracle Unified Audit read-back. Keep the pack catalogue-only/unverified until source mapping and replay/read-back evidence exist.
