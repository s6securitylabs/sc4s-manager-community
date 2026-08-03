# Oracle Database audit-file fixture IVV — 2026-07-01

Scope: local source-shape/fixture validation for `oracle_database` traditional audit-file and Unified Audit syslog-style fixtures only.

Verdict: **Alpha source-shape / unverified**. The pack now has synthetic-equivalent audit-file and Unified Audit syslog-style event logs. No parser artifacts are exported while this remains a generic source-definition pack, and no live Oracle DB, SC4S listener, HEC delivery, Splunk indexed read-back, or field validation was performed.

Evidence used:

- Elastic `integrations` Oracle `database_audit` pipeline test shape reviewed as source-shape reference under Elastic License 2.0; raw samples were not copied.
- Synthetic-equivalent local fixtures: `test-events/oracle_database_audit_file.txt` and `test-events/oracle_database_unified_audit_syslog.txt`.
- No SC4S route artifact or Splunk search-time extraction is exported for this pack yet.

Checks expected before promotion:

1. Select and implement one deployable envelope before replay; current fixtures are source-shape examples only.
2. For traditional audit-file relay, confirm exactly 3 events in `index=infraops sourcetype="oracle:database:audit:file"` with all `SC4S_ORACLE_DATABASE_TEST_AUDIT_*` markers once parser/export artifacts exist.
3. For Unified Audit syslog-style relay, confirm exactly 3 events in `index=infraops sourcetype="oracle:database:unified_audit"` with all `SC4S_ORACLE_DATABASE_TEST_UNIFIED_AUDIT_*` markers once parser/export artifacts exist.
4. Verify `_time`, user/action/return-code/object fields, source/host, marker fields, and raw preservation.
5. Keep trust `unverified` until replay/read-back evidence exists.
