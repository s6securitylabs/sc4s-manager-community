# SQL database logs pack

Conservative SecHub Resources SC4S pack for native PostgreSQL, MySQL, and MariaDB text-log relay lines. Initial scope is intentionally narrow: PostgreSQL stderr/syslog-style text lines with a declared log prefix, including statement-duration metadata where enabled, MySQL error-log rows, MariaDB error-log rows, MySQL/MariaDB slow-query metadata rows, and MariaDB general-query command rows.

This is curated intake guidance, not live database validation. Trust remains `unverified` and quality remains `curated` until real database log relay replay and Splunk indexed read-back evidence exists.

## Evidence searched

- `docs/evidence/sql-database-logs-evidence-scan-20260608.md` records reachable PostgreSQL, MySQL, MariaDB, and Elastic/Filebeat documentation for logging destinations, log-prefix fields, error-log anatomy, slow-query metadata, general-query command rows, multiline/sensitive-data warnings, and parser ecosystem support.
- Initial fixtures use synthetic-equivalent values derived from documented structure only.
- PostgreSQL CSV/JSON logs, PostgreSQL multiline/full statement handling beyond the one-line duration fixture, MySQL JSON error logs, MariaDB/MySQL audit-plugin output, cloud-provider wrappers, and multiline SQL payload parsing are deferred until exact emitted-record evidence and a replay/read-back testbed are available.

## Scope

- Listener: dedicated TCP syslog example on port `20079` with source tag `SQL_DATABASE_LOGS`.
- Payloads: one database log record per line.
- Routed sourcetypes: `postgresql:server:log`, `mysql:error:log`, `mariadb:error:log`, `mysql:slowquery:log`, and `mariadb:general:log`.
- Default index: `infraops`.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20079` with source tag `SQL_DATABASE_LOGS`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `infraops` and sourcetype(s) `postgresql:server:log`, `mysql:error:log`, `mysql:slowquery:log`, `mariadb:general:log`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Fixture semantics

- File: `test-events/sql_database_logs_test_events.txt`.
- Format: raw database log payload lines with synthetic documentation-shaped values.
- Wire/envelope: headerless fixture payloads; `scripts/send_tcp_20079.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per physical line; multiline SQL bodies and stack traces are out of scope for this first pack.
- Timestamp: PostgreSQL fixtures use UTC text timestamps with timezone token; PostgreSQL duration fixtures preserve milliseconds as `query_duration_ms`; MySQL slow/error fixtures use ISO-8601 UTC tokens; MariaDB general fixture uses local text timestamp and requires deployment timezone policy before promotion.
- Delimiting: PostgreSQL prefix plus severity/message, MySQL bracketed component fields, MariaDB timestamp/thread/severity/message fields, slow-query `#` metadata fields, and MariaDB general-query thread/command/argument tokens with fixture-backed user/client/database extraction for the current `Connect user@client on database` shape.
- Markers: `SC4S_SQL_DATABASE_LOGS_TEST_*` values each occur exactly once.
- Sanitisation: fixtures use RFC5737 addresses, example users/databases, and non-sensitive synthetic SQL/message context only.

Validation SPL smoke pattern:

```spl
index=infraops "SC4S_SQL_DATABASE_LOGS_TEST_" earliest=-2h
| table _time index sourcetype source vendor product user src db_user database db_command severity action signature signature_id marker process_id thread_id query_time query_duration_ms lock_time rows_sent rows_examined db_statement error_code component db_message _raw
```

## Dashboard scope

`sql_database_logs_overview.xml` is a fixture-backed Splunk SimpleXML overview for onboarding and first triage. It covers only the current synthetic-equivalent PostgreSQL text, MySQL and MariaDB error-log, PostgreSQL statement-duration metadata, MySQL slow-query metadata, and MariaDB general-query fixtures. Panels focus on event arrival, sourcetype coverage, error/warning/access-denied and slow-query counters, database user/client context, PostgreSQL and MySQL/MariaDB error review, slow-query metadata, MariaDB command rows, onboarding coverage, and recent raw database-log context.

The dashboard deliberately does not state PostgreSQL CSV/JSON, PostgreSQL multiline/full statement handling, MySQL JSON error logs, audit-plugin formats, cloud-provider wrappers, multiline SQL bodies, complete query-body parsing, collector health, or replay/read-back validation. Database logs can contain sensitive SQL/data fragments; any production dashboard expansion must remain grounded in sanitized fixtures or retained read-back evidence.

## Reduction stance

No event drops or field deletion are enabled by default. `docs/sql_database_logs_reduction_candidates.csv` lists advisory-only candidates for high-volume successful statement noise, long SQL payload redaction, and repetitive operational notices. Authentication failures, admin/privilege statements, database/user/client identity, slow-query metadata, error severity/code/message, process/thread/session identifiers, and raw message context are risky to drop and must be retained by default.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-08.md` shows port `20079` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from public documentation, not real customer or database exports.
- Native database logs may contain credentials, SQL literals, tenant/object names, and row fragments. Production collection must apply local data-handling policy before publication or sharing.
- PostgreSQL CSV/JSON, PostgreSQL multiline/full statement handling, MySQL JSON error logs, audit-plugin formats, cloud-provider wrappers, and multiline SQL bodies remain deferred variants.
- Reduction candidates are advisory only and require local replay/read-back plus rollback review before enablement.

## Disposable E2E Docker harness

One-shot lab command:

```bash
packs/sql_database_logs/scripts/e2e_docker_compose.sh run
```

Plan-only command, safe for CI and hosts without Docker:

```bash
packs/sql_database_logs/scripts/e2e_docker_compose.sh plan
```

The harness writes an idempotent Compose stack under `.tmp/e2e/sql_database_logs/`, recreates a disposable Splunk TEST plus SC4S TEST project, mounts this pack's SC4S parser and Splunk knowledge artifacts, creates/preflights index `infraops`, replays `test-events/sql_database_logs_test_events.txt` through TCP listener `20079`, and runs Splunk read-back searches for `SC4S_SQL_DATABASE_LOGS_TEST_` markers.

Required evidence stages are Splunk TEST readiness, SC4S listener ownership, fixture send count, SC4S/syslog-ng counter movement, HEC delivery, Splunk indexed read-back, and coverage-matrix review. Passing the harness is still only fixture-backed SC4S TEST -> Splunk TEST evidence for the listed PostgreSQL/MySQL/MariaDB text-log source shapes; it is not production or field validation.

Current fixture coverage includes PostgreSQL login/permission/duration rows, MySQL access-denied and slow-query metadata rows, MariaDB connect/general-query rows, and MariaDB access-denied error rows. Logout/disconnect, high-level database/system metrics, audit-plugin output, cloud wrappers, JSON log variants, and multiline SQL remain explicit gaps until source-shape fixtures and read-back evidence are added.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real database log relay replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, user/database/client fields, eventtypes/tags, and normalized fields.
