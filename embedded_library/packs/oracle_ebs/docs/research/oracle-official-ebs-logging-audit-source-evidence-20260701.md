# Oracle E-Business Suite public logging/audit source evidence — 2026-07-01

- **Title:** Oracle E-Business Suite public logging/audit source evidence for SecHub Resources pack scoping
- **Publisher / organisation:** Oracle documentation, Oracle Security Alerts, Oracle eTRM public table documentation
- **Original URLs:** listed per section below
- **Publication date:** various Oracle documentation/security-alert publication dates; exact dates not consistently available from public pages
- **Access date:** 2026-07-01
- **Licence / terms:** Oracle documentation/eTRM pages are referenced and summarized only; no Oracle tables, manuals, article bodies, screenshots, or proprietary samples are mirrored.

## Purpose

This note records the public evidence boundary behind the conservative `oracle_ebs` normalized JSON relay. It explains which EBS source families are reasonable to model synthetically at a generic level, and which native schemas/log grammars remain blocked until source-backed samples are provided.

## Oracle May/June 2026 vulnerability context

Official Oracle pages:

- Oracle Security Alerts index: https://www.oracle.com/security-alerts/
- May 2026 Critical Security Patch Update Advisory: https://www.oracle.com/security-alerts/cspumay2026.html
- May 2026 verbose risk matrix: https://www.oracle.com/security-alerts/cspumay2026verbose.html
- June 2026 Critical Security Patch Update Advisory: https://www.oracle.com/security-alerts/cspujun2026.html
- June 2026 verbose risk matrix: https://www.oracle.com/security-alerts/cspujun2026verbose.html

May 2026 Oracle EBS context from the public advisory/risk matrix includes Oracle E-Business Suite versions 12.2.3 through 12.2.15, multiple EBS patches, and unauthenticated remote exposure in some entries. The highest-priority monitoring focus for this pack remains Oracle Payments / File Transmission because CVE-2026-46817 was publicly reported as exploited in the wild and Oracle's May matrix describes Oracle Payments/File Transmission network/HTTP exposure.

May 2026 EBS modules that are useful triage priorities include Oracle Payments, Oracle Internet Procurement Connector, Oracle Financials Common Modules, Oracle iAssets, Oracle Public Sector Financials International, Oracle Universal Work Queue, Oracle Payroll, and Oracle Flow Manufacturing.

June 2026 Oracle EBS context includes broader EBS 12.2.3-12.2.15 and V15/V16 module exposure. Useful triage priorities include Oracle Enterprise Command Center Framework, Oracle iSupplier Portal, Oracle Applications Manager, Process Manufacturing Product Development, Universal Work Queue, Advanced Outbound Telephony, Cost Management, Enterprise Asset Management, Receivables, Human Resources/HRMS/Payroll, Project Portfolio Analysis, Subledger Accounting, Public Sector Financials, Quality, Spares Management, and Complex Maintenance Repair and Overhaul.

This vulnerability context is a dashboard prioritisation input only. It does not create exploit signatures or native parser validation.

## Sign-On Audit

References:

- Oracle Applications Sign-On Audit documentation: https://docs.oracle.com/cd/A60725_05/html/comnls/us/fnd/sonaud01.htm
- Public eTRM `APPLSYS.FND_LOGINS`: https://etrm.live/etrm-12.1.1/etrm.oracle.com/pls/et1211d9/etrm_pnav0f2b-2.html

Public evidence supports generic synthetic sign-on/session fixtures because Oracle documents Sign-On Audit levels and the public eTRM describes login/session table fields such as `LOGIN_ID`, `USER_ID`, `START_TIME`, `END_TIME`, `PID`, `SPID`, `TERMINAL_ID`, `LOGIN_NAME`, and `SESSION_NUMBER`.

Safe synthetic relay family: `ebs_signon_success`, `ebs_signon_failure`.

Blocked promotion: exact customer query, joins to user/responsibility tables, timezone, collector envelope, terminal/source mapping, and field-level semantics require source-backed evidence.

## AuditTrail

Reference:

- Oracle EBS Security Guide, AuditTrail: https://docs.oracle.com/cd/E26401_01/doc.122/e22952/T156458T663771.htm

Oracle documents AuditTrail audit groups/tables and the `Audit Trail Update Tables` process that creates shadow tables, database triggers, and audit views. This supports generic audit-change semantics for sensitive-object monitoring.

Safe synthetic relay family: `ebs_audittrail_sensitive_change`.

Blocked promotion: exact shadow table names, columns, primary keys, old/new value fields, and source timezone vary by customer-selected audit groups/tables and must not be treated as universal.

## FND / OAF logging framework

References:

- Oracle EBS Developer's Guide logging framework overview: https://docs.oracle.com/cd/E18727_01/doc.121/e12897/T302934T359300.htm
- Oracle EBS Developer's Guide logging framework/API details: https://docs.oracle.com/cd/E18727_01/doc.121/e12897/T302934T359303.htm
- Public eTRM `APPLSYS.FND_LOG_MESSAGES`: https://etrm.live/etrm-12.1.1/etrm.oracle.com/pls/et1211d9/etrm_pnavfaff.html

Public Oracle docs/eTRM support generic FND/OAF application logging fixtures with fields such as `MODULE`, `LOG_LEVEL`, `MESSAGE_TEXT`, `SESSION_ID`, `USER_ID`, `TIMESTAMP`, `LOG_SEQUENCE`, `NODE`, `NODE_IP_ADDRESS`, transaction context fields, and ECID fields where available.

Safe synthetic relay family: `ebs_fnd_security_error`.

Blocked promotion: exact deployed log level policy, message grammar, sensitive values in message text, ECID propagation, and customer-specific module names require source-backed evidence.

## Concurrent Manager / concurrent requests

Reference:

- Public eTRM `APPLSYS.FND_CONCURRENT_REQUESTS`: https://etrm.live/etrm-12.2.2/etrm.oracle.com/pls/trm1222/etrm_pnavbedf.html

Public eTRM supports generic concurrent request metadata fixtures using fields such as `REQUEST_ID`, `PHASE_CODE`, `STATUS_CODE`, `CONCURRENT_PROGRAM_ID`, `PROGRAM_APPLICATION_ID`, `REQUESTED_START_DATE`, `ACTUAL_START_DATE`, `ACTUAL_COMPLETION_DATE`, `LOGFILE_NAME`, `LOGFILE_NODE_NAME`, `OUTFILE_NAME`, `OUTFILE_NODE_NAME`, `ARGUMENT_TEXT`, `COMPLETION_TEXT`, and `CONC_LOGIN_ID`.

Safe synthetic relay family: `ebs_concurrent_privileged_request`.

Blocked promotion: exact program lookup, argument sensitivity, logfile parsing, node/path details, and local timezone require source-backed evidence.

## Workflow / Notification Mailer

Reference:

- Oracle Workflow Notification Mailer documentation: https://docs.oracle.com/cd/E24628_01/em.121/e54435/wf_nfcn_mlr.htm

Public docs support high-level workflow/notification-mailer operational context, including outbound/inbound notification flow and response handling. They do not, by themselves, prove a stable raw runtime log line grammar.

Safe synthetic relay family: `ebs_workflow_mailer_change` as a normalized collector event or metric-derived event.

Blocked promotion: exact Workflow runtime log line format, table/query selection, mailer component log paths, and notification payload sensitivity require source-backed evidence.

## Oracle HTTP Server / OHS

Reference:

- Oracle HTTP Server logging documentation: https://docs.oracle.com/en/middleware/fusion-middleware/web-tier/14.1.2/administer-ohs/man_logs.html

Oracle documents OHS access/error logs and the default access-log/Common Log Format-style fields, including client/host, ident, user, timestamp, ECID, request, status, and bytes.

Safe synthetic relay family: `ebs_ohs_suspicious_http`, if a collector tags OHS records as EBS application-tier context and preserves the raw request fields.

Blocked promotion: exact EBS deployment paths, OHS format customisations, reverse-proxy headers, ECID/session/user linkage, and exploit-specific indicators require source-backed evidence.

## WebLogic and EBS managed servers

References:

- Oracle WebLogic HTTP logging documentation: https://docs.oracle.com/cd/E13222_01/wls/docs81/ConsoleHelp/domain_server_logging_http.html
- Oracle EBS 12.2 setup guide / managed server context: https://docs.oracle.com/cd/E26401_01/doc.122/e22953/T174296T589913.htm

Oracle documents WebLogic HTTP access logging, common/extended formats, and EBS 12.2's use of WebLogic managed servers including examples such as `oacore`, `oafm`, `forms`, and `forms-c4ws`.

Safe synthetic relay family: `ebs_weblogic_security` for collector-normalized app-tier authentication/security/error events.

Blocked promotion: exact WebLogic security log grammar, domain/server paths, managed-server coverage, and EBS user/session responsibility linkage require source-backed evidence.

## Forms / OAF traces

References:

- Oracle EBS Developer's Guide SQL trace options: https://docs.oracle.com/cd/E26401_01/doc.122/e22961/T302934T359305.htm
- Oracle Forms tracing and diagnostics: https://docs.oracle.com/en/middleware/developer-tools/forms/12.2.1.4/working-forms/tracing-and-diagnostics.html

Oracle documents Forms SQL Trace and Forms Trace for execution paths/user actions and diagnostics. Public docs support generic trace/diagnostic event concepts but not a universal raw line grammar.

Safe synthetic relay family: `ebs_forms_oaf_error` as a normalized collector event.

Blocked promotion: exact trace line format, trace enablement policy, source path, SQL/bind sanitisation, and performance-safe collection posture require source-backed evidence.

## Fixture safety summary

Safe to model synthetically in this pack as **normalized relay** events:

- sign-on success/failure
- generic AuditTrail sensitive change
- FND/OAF security/error message
- concurrent privileged request
- workflow/mailer routing or notification event
- OHS suspicious HTTP request tagged to EBS context
- WebLogic application-tier security event
- Forms/OAF error/trace-derived event
- Oracle Payments / File Transmission advisory-focus event
- Enterprise Command Center Framework advisory-focus event
- high-risk supplier/payroll/financials module activity

Still blocked as native authoritative parsers:

- direct EBS table/shadow-table schema parsing without customer/source query evidence
- exact Workflow Notification Mailer runtime log line grammar
- exact OHS/WebLogic/EBS deployed file paths and local formats
- exact Forms/OAF trace line grammar
- exploit-specific indicators from third-party reporting
- any fixture or dashboard assertion based on real customer/business data without sanitised source-backed approval

## Ecosystem/source-corpus discovery addendum

Access date for all ecosystem checks in this addendum: 2026-07-01. These checks are discovery signals only; no proprietary Splunk TA/app content, Elastic package implementation, or third-party dashboard SPL is copied into this repository.

| Source | URL(s) checked | Classification | Safe signal for `oracle_ebs` | Licence / handling |
| --- | --- | --- | --- | --- |
| Splunkbase app catalogue API, exact Oracle/EBS search by metadata | https://splunkbase.splunk.com/api/v1/app/ and filtered public metadata for `Oracle E-Business Suite`, `Oracle EBS`, `FND_LOG_MESSAGES`, `FND_LOGINS`, and `AuditTrail Oracle EBS` | **metadata-only / insufficient for EBS-native parser** | No clear modern Splunkbase app/TA specifically for Oracle E-Business Suite logging/audit was found in public app metadata. This supports keeping native EBS source modes blocked rather than claiming an upstream TA exists. | Splunkbase metadata only; do not download or copy proprietary app content unless licence and redistribution are explicitly reviewed. |
| Splunk Add-on for Oracle Database | https://splunkbase.splunk.com/app/1910/ | **metadata-only / reference-only** | Public metadata says the TA collects Oracle Database standard/FGA audit trails, trace files, incident, alert, listener, and other OS logs, and uses DB Connect for performance/inventory. Useful for EBS database-audit adjacency, but it does not prove EBS Sign-On Audit, AuditTrail shadow tables, FND, concurrent, workflow, Forms/OAF, or OHS/WebLogic app-tier parsing. | Splunk General Terms; metadata summarized only. Treat as Oracle Database pack reference, not vendorable EBS content. |
| Splunk DB Connect and Oracle JDBC add-on | https://splunkbase.splunk.com/app/2686/ and https://splunkbase.splunk.com/app/6151/ | **metadata-only / reference-only** | Public metadata confirms a reasonable collection path for EBS table/view exports through Splunk DB Connect plus Oracle JDBC. This supports the relay model for FND tables and AuditTrail exports, but the exact SQL, joins, checkpoints, and field semantics remain site-owned evidence. | Splunk General Terms; metadata summarized only. Do not vendor app content. |
| Splunkbase Oracle database audit apps | https://splunkbase.splunk.com/app/6172/ and https://splunkbase.splunk.com/app/4307/ | **metadata-only / reference-only** | Public descriptions mention executive/security/operational views for Oracle Database unified audit / Omega Core Audit. Useful dashboard inspiration for role-separated views and database-activity posture, but not EBS application-audit evidence. | Third-party EULA; metadata summarized only. No SPL/dashboard copying. |
| Legacy Oracle 11g log analysis Splunkbase listing | https://splunkbase.splunk.com/app/1538/ | **metadata-only / reference-only** | Public metadata mentions log files, audit trail, trigger-based TCP inputs, shell scripts, DB Connect, field extractions, reports, and dashboards. Good historical confirmation that Oracle monitoring often mixes DB/file/script/DBX inputs, but not a current EBS parser source. | Contact-vendor licence; metadata summarized only. Do not vendor. |
| Elastic Package Registry: Oracle integration | https://epr.elastic.co/package/oracle/1.31.3 | **reference-only** | Package metadata exposes Oracle Database data streams such as `database_audit`, `memory`, `performance`, `sysmetric`, `system_statistics`, and `tablespace`; `database_audit` uses file collection with an example audit-log path. This is useful for the adjacent Oracle Database pack and for EBS database-audit planning, not for native EBS application tables/logs. | Elastic package material is not copied; use only high-level dataset/source-shape signals unless licence review approves vendoring. |
| Elastic Package Registry: Oracle WebLogic integration | https://epr.elastic.co/package/oracle_weblogic/1.9.1 | **reference-only** | Public package metadata exposes WebLogic `access`, `admin_server`, `domain`, and `managed_server` log datasets plus Jolokia metrics, with default log path patterns under `servers/<ServerName>/logs/`. Useful for EBS 12.2 app-tier adjacency and dashboard panels for web/app-tier failures, but not proof of EBS user/session/responsibility linkage. | Elastic package material is not copied; reference only. |
| Fluent Bit built-in parser catalogue | https://github.com/fluent/fluent-bit/blob/master/conf/parsers.conf | **insufficient** | No Oracle/EBS/WebLogic parser signal was observed in the checked public parser catalogue. | Apache-licensed upstream project, but no relevant parser to vendor. |
| Logstash grok-patterns-core legacy/ECS patterns | https://github.com/logstash-plugins/logstash-patterns-core/tree/main/patterns | **insufficient** | No Oracle/EBS/WebLogic parser signal was observed in the checked public grok pattern files. | Apache-licensed upstream project, but no relevant parser to vendor. |
| Upstream Splunk Connect for Syslog repository scan | https://github.com/splunk/splunk-connect-for-syslog | **insufficient / blocked for native EBS** | A shallow public repository scan did not find Oracle EBS, Oracle application, FND, or WebLogic source definitions. This supports maintaining the local `oracle_ebs` parser as a normalized JSON relay only; there is no observed upstream SC4S EBS parser to mirror. | Upstream SC4S repo reference only; no vendorable Oracle EBS parser found. |
| GitHub public repository and issue search | https://api.github.com/search/repositories and https://api.github.com/search/issues queries for `Oracle E-Business Suite Splunk`, `Oracle EBS Splunk`, `FND_LOG_MESSAGES`, `FND_LOGINS`, `Concurrent Manager Splunk Oracle`, and `Workflow Notification Mailer Splunk` | **insufficient** | Repository search returned no actionable public EBS/Splunk parser/dashboard repositories for the exact EBS table/log terms. Issue search mostly returned vulnerability-tracker or unrelated hits, with no safe canonical log shapes or dashboard SPL to reuse. | Public search metadata only; do not treat unrelated issue text as source evidence. |

## Dashboard and fixture expansion recommendations from discovery

Do not copy proprietary dashboard XML/SPL from Splunkbase apps. The public ecosystem signals above still support a high-quality SOC dashboard shape for a site-owned EBS normalized relay:

1. **Authentication and session posture:** keep panels for EBS Sign-On Audit success/failure, failed-login spikes, privileged users, client/source IPs, and sessions without a known responsibility. Required evidence for native expansion: exact FND login/session query output, joins, timezone, and failure semantics.
2. **Administration / responsibility / security configuration changes:** expand AuditTrail panels when source-backed rows exist for responsibility grants, user status/profile option changes, function/menu/form changes, and workflow/mailer routing changes. Required evidence: exact audited object/table/shadow-table columns and old/new value handling.
3. **Concurrent request failures and privileged jobs:** add trend/top panels for request `PHASE_CODE`, `STATUS_CODE`, program/application, log/output node, completion text, and argument-risk review. Required evidence: approved query over `FND_CONCURRENT_REQUESTS` plus lookup joins and sanitisation rules for `ARGUMENT_TEXT`.
4. **Workflow / Notification Mailer operations:** add panels for inbound/outbound mailer state changes, deferred/error counts, response processing failures, and notification routing changes only after exact table/log/metric source is approved.
5. **App-tier and web-tier errors:** use WebLogic/OHS-adjacent references for panels covering HTTP 4xx/5xx spikes, suspicious EBS URL paths, Forms/OAF errors, ECID/request correlation, managed-server errors, and authentication/security exceptions. Keep generic `oracle_weblogic`/`oracle_ohs` validation separate from EBS validation.
6. **Database-adjacent EBS audit:** use Oracle Database TA/Elastic Oracle metadata only as a collection-pattern reference for APPS/SYS/DBA audit, not as EBS validation. Panels should preserve DB user/schema, object/action, client program/module, and EBS session linkage where source-backed.
7. **Fixture policy:** future fixtures should remain synthetic-equivalent unless contributed samples have explicit redistribution approval. Prefer one event per family with stable markers, UTC `event_time`, raw source identifiers (`source_table`, `source_log_path`, `collector_query_id`), and enough fields to exercise dashboards without business secrets.

## Pack implication

The implemented `ebs_security_json_relay` source mode remains the safest current compromise: a customer/SOC-owned collector can translate approved EBS rows/logs/metrics into one sanitized JSON object per line while preserving raw context in `_raw`. SecHub Resources can provide SC4S routing, Splunk search-time extraction, fixtures, and dashboarding for that relay without pretending to have universal native EBS source-shape validation. The ecosystem scan found useful Oracle Database/WebLogic/DB Connect adjacency signals and dashboard themes, but no public, vendorable Oracle EBS native parser or dashboard corpus suitable for trust promotion.
