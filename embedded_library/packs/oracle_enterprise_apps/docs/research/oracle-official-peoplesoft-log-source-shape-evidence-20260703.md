# Oracle PeopleSoft / PeopleTools log source-shape evidence — 2026-07-03

Attribution:
- Primary source: Oracle official PeopleTools documentation (system/server-process logging, Process Scheduler logging, signon auditing, Integration Broker gateway logging), Oracle Tuxedo documentation (ULOG), plus vendor-neutral corroboration (Integrigy PeopleSoft auditing whitepaper) and community references for behavioural detail.
- Author/organisation: Oracle Corporation (product docs) and cited third parties; analysis and derived source-shape mapping by S6 (SecHub Resources).
- Access date: 2026-07-03.
- Licence/terms: source docs are copyrighted. This note summarises facts (field order, timestamp format, delivery channel, table names) and quotes nothing verbatim beyond short field/format tokens. No vendor sample logs, tables, or screenshots are copied.

Use in this pack: source-shape reference and blocker triage only. It does **not** promote `quality_status`, `trust_level`, or any `validated`/`verified` label. PeopleSoft remains a catalogue/source-definition family inside `oracle_enterprise_apps` with routing disabled until exact emitted records plus replay/read-back evidence exist.

## Scope decision

PeopleSoft is already catalogued in this pack (alongside JD Edwards and Siebel). This pass decides which PeopleSoft sub-sources could graduate to a future fixture-backed deployable-alpha slice versus which must stay catalogue-only. Recommendation up front: **do not create a standalone PeopleSoft pack**; keep it inside `oracle_enterprise_apps`. The PIA web tier is already covered by `packs/oracle_weblogic` and `packs/oracle_ohs` and should be cross-referenced, not duplicated.

## Per-source verdicts

| Source | Line-oriented file-tail/syslog shape | Collection path | Verdict |
| --- | --- | --- | --- |
| App Server APPSRV.LOG (+ Tuxedo ULOG/TUXLOG) | YES — documented single-line grammar | File tail | Promotable-with-sample |
| Process Scheduler SCHDLR.LOG | PARTIAL→YES — same server-process framework | File tail | Promotable-with-sample |
| Integration Broker — dispatcher logs (PSBRKDSP etc.) | YES — app-server-style single line | File tail | Folds into app-server grammar |
| Integration Broker — gateway msgLog/errorLog.html | NO/PARTIAL — HTML, per-entry grammar not public | File (HTML) | Blocked pending sample |
| Signon audit — PSPTLOGINAUDIT / PSACCESSLOG | NO — database tables, no emitted line | DB export | Catalogue-only (DB export) |
| Security/record/field/DB-level audit — PSAUDIT + custom tables | NO — database tables/triggers | DB export | Catalogue-only (DB export) |
| Native syslog emitter | NO — none exists | — | File tail + DB export only |
| Web / PIA (WebLogic/OHS) | reuse existing packs | File tail | Redirect to oracle_weblogic / oracle_ohs |

## Key documented facts

- **Server-process log family (APPSRV.LOG, SCHDLR.LOG, IB dispatcher logs):** Oracle documents a stable single-line grammar shared by all PeopleSoft server processes (PSAPPSRV, PSQRYSRV, PSBRKDSP, ...), with field order approximately `ServerProcess.PID (ServiceRequestNumber) [Timestamp] SRID TOPInstanceID OperatorID (LogLevel) Message`. Timestamp is `YYYY-MM-DDThh:mm:ss.sss` (ISO-8601 with milliseconds). Parsing hazards: by default there is **no UTC offset** on the timestamp; correlation fields (SRID, TOP instance ID, Operator ID) are positional but frequently a literal `-` placeholder; and the field separator is configurable via the domain `LogFieldSeparator` parameter (default space). Log level is numeric in parentheses `(0)`–`(5)` (LogFence). These facts are enough to *draft* a regex but a real sample is required to lock the separator variant and confirm placeholder behaviour.
- **Tuxedo ULOG/TUXLOG:** separate documented single-line grammar `hhmmss.machine!process.PID.thread.context: CATALOG:num: message` (e.g. `LIBTUX_CAT:262`), 6-digit local-time-only timestamp, daily file naming (`ULOG.mmddyy`). App-server companion source.
- **Process Scheduler SCHDLR.LOG:** part of the same server-process logging framework (LOGFENCE 0–5, default 3; single-line). The full positional grammar is not re-printed in the scheduler doc, so treat it as "same family, confirm identical layout with a fixture." Authoritative process/report **failure status** lives in DB tables (PSPRCSRQST etc.), not in SCHDLR.LOG; the log is operational/diagnostic.
- **Integration Broker gateway logs:** `msgLog.html` / `errorLog.html` under the gateway web app, created only when something is logged, path/name/level configurable in `integrationGateway.properties`; log levels documented (`-100` off, `-1`, `1`–`5`, default `2`). The **per-entry field grammar is not publicly documented** and the HTML markup makes it non-line-oriented — a poor parser target without a captured sample. IB **dispatcher/handler** processes, by contrast, log to the standard server-process log format and fold into the app-server grammar.
- **Signon audit (PSPTLOGINAUDIT, PSACCESSLOG):** database tables, not emitted log lines. PSPTLOGINAUDIT columns include `PT_AUTH_TYPE`, `OPRID`, `PTSIGNONID`, `PT_SIGNON_STATUS` (0 success / 1 failure), `FAILEDLOGINS`, `LASTSIGNONDTTM`; note a successful login clears the user's failure rows, so failed-login history is **volatile** and streaming-from-table is lossy. PSACCESSLOG records PIA/app-server/batch signon-signout keyed on OPRID with sign-on/sign-out DTTM. Collection is DB query export (e.g. Splunk DB Connect / a collector), not syslog. This is the highest-value security data and the hardest to onboard as "logs."
- **Record/field/DB-level audit (PSAUDIT + custom tables):** field-level audit → PSAUDIT record; record-level audit → per-record custom tables; database-level (trigger-based) audit → custom tables capturing changes made outside the PeopleSoft UI, including security-table changes. All are DB-table/trigger outputs with `AUDIT_*` columns and an `AUDIT_STAMP` datetime; no emitted line; DB export only.
- **Collection model:** PeopleSoft has **no native syslog emitter**. Two paths only: file tail of the domain `LOGS` directory (APPSRV.LOG, TUXLOG/ULOG, SCHDLR.LOG, IB dispatcher logs, WebLogic/OHS web logs), and DB query export (PSACCESSLOG, PSPTLOGINAUDIT, PSAUDIT and custom audit tables). Syslog relay is not native — it needs a file-to-syslog relay (agent or SC4S file source). No dedicated Datadog or Elastic PeopleSoft log integration/module was found; no official Splunk PeopleSoft TA with a published sourcetype/regex was found.

## Blockers to a deployable parser

1. Real sanitised sample lines for APPSRV.LOG / SCHDLR.LOG / ULOG — to lock the `LogFieldSeparator` variant, confirm placeholder behaviour of correlation fields, and confirm the default no-TZ timestamp.
2. DB-export schema/column order for PSACCESSLOG / PSPTLOGINAUDIT / PSAUDIT as actually emitted by the chosen collector (these become JSON/CSV, not syslog).
3. IB gateway HTML per-entry field grammar — not public; needs a captured sample.
4. No live PeopleTools instance, SC4S replay, HEC delivery, or Splunk read-back has occurred (same posture as the sibling weblogic/ebs packs).

## Representative sources (access date 2026-07-03)

- Server process logs (field order, ISO-8601 ms timestamp, `-` placeholders): `https://docs.oracle.com/cd/E92519_02/pt856pbr3/eng/pt/tsvt/task_WorkingWithPeopleSoftServerProcessLogs.html`
- App server logging/tracing (LogFence levels): `https://docs.oracle.com/cd/E41633_01/pt853pbh1/eng/pt/tibr/task_ManagingApplicationServerLoggingandTracing-076206.html`
- Tuxedo ULOG format: `https://docs.oracle.com/cd/E13203_01/tuxedo/tux71/html/intinf44.htm`
- Process Scheduler logging (LOGFENCE, single-line): `https://docs.oracle.com/cd/E92519_02/pt856pbr3/eng/pt/tprs/task_LoggingSystemforPeopleSoftProcessSchedulerServer-dc0783.html`
- Signon audit PSPTLOGINAUDIT (columns, table-only, volatility): `https://docs.oracle.com/cd/E92519_02/pt856pbr3/eng/pt/tsec/task_TrackingUserSign-InAttempts.html`
- Sign-in/sign-out activity PSACCESSLOG: `https://docs.oracle.com/cd/E80738_01/pt854pbh2/eng/pt/tsec/task_TrackingUserSignInandSignOutActivity-c076e7.html`
- Integration Broker gateway logging config: `https://docs.oracle.com/cd/E41633_01/pt853pbh1/eng/pt/tibr/task_ManagingIntegrationGatewayMessageandErrorLogging-076210.html`
- Auditing overview (table-based vs log-based, PSAUDIT/record/DB-level): Integrigy "Oracle PeopleSoft Auditing" whitepaper `https://www.integrigy.com/security-resources`

## Recommendation and current disposition

- **Promotable to a future fixture-backed deployable-alpha slice (within this pack), once one real sanitised sample per source is obtained and read-back passes:** `oracle:peoplesoft:appserver` (APPSRV.LOG, strongest), `oracle:peoplesoft:process_scheduler` (SCHDLR.LOG), with Tuxedo ULOG as an app-server companion and IB dispatcher logs folded into the app-server grammar. These are **file-tail only, no native syslog**.
- **Keep catalogue-only with explicit blockers:** `oracle:peoplesoft:signon:audit` (PSPTLOGINAUDIT/PSACCESSLOG — DB export only, PSPTLOGINAUDIT volatile) and `oracle:peoplesoft:security:audit` (PSAUDIT / record / DB-level trigger audit — DB export only). IB **gateway** msgLog/errorLog.html stays blocked pending a sample.
- **Redirect, don't duplicate:** PIA web-tier logs → `packs/oracle_weblogic` / `packs/oracle_ohs`.
- **Future variants (JDE, Siebel, OEM):** same pattern — operational logs are file-tailable, security/audit data is DB-table-based; OEM already has `packs/oracle_oem`. JDE/Siebel remain catalogue-only here.

Routing stays disabled and trust stays `unverified`: the emitted line grammar is documented well enough to draft a parser for the server-process family, but no sanitised sample or live replay/read-back has been captured, so no promotion is warranted in this run.
