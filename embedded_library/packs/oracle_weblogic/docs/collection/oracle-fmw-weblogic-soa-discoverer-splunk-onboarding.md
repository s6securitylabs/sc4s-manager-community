# Oracle Fusion Middleware, WebLogic, SOA, and Discoverer Splunk onboarding guidance — 2026-07-06

## Evidence boundary

This note is conservative collection guidance for Oracle Fusion Middleware families. It builds on the existing `oracle_weblogic` SecHub pack and official Oracle logging documentation. It does not copy Oracle product logs, Splunk TA internals, or third-party parser content.

The current `oracle_weblogic` pack has an alpha, synthetic-equivalent server/access log slice for `oracle:weblogic:server` and `oracle:weblogic:access`. Fusion Middleware diagnostic/ODL, SOA/OSB/BPM, Node Manager, audit provider, Forms/Reports component logs, and Discoverer lanes remain source-shape-gated until exact emitted samples and read-back exist.

## Official evidence reviewed

- Oracle WebLogic Server 14.1.2, **Understanding WebLogic Logging Services**: <https://docs.oracle.com/en/middleware/fusion-middleware/weblogic-server/14.1.2/wllog/logging_services.html>
  - Supports WebLogic server-log planning: server log messages begin with `####` followed by angle-bracket message attributes.
  - Confirms HTTP subsystem access logs are text files and that access-log behavior can be configured per server or virtual host.
  - Confirms Node Manager writes startup/status messages to `NM_HOME/nodemanager.log`, with `NM_HOME` defaulting to `DOMAIN_HOME/nodemanager`.
- Oracle Fusion Middleware 12.2.1.4, **Managing Log Files and Diagnostic Data**: <https://docs.oracle.com/en/middleware/fusion-middleware/12.2.1.4/asadm/managing-log-files-and-diagnostic-data.html>
  - Supports generic Fusion Middleware diagnostic collection planning: most FMW components write Oracle Diagnostic Logging (ODL) diagnostic files; most Java components use `DOMAIN_HOME/servers/server_name/logs`, with default log name `server-name-diagnostic.log`; system components use component log directories under the domain.
  - Notes ODL text is default but XML can be configured, so line breaking and timestamp handling must be proven per component.
- Oracle HTTP Server 14.1.2, **Managing Oracle HTTP Server Logs**: <https://docs.oracle.com/en/middleware/fusion-middleware/web-tier/14.1.2/administer-ohs/man_logs.html>
  - Supports keeping OHS separate from WebLogic: OHS has error logs, access logs, and `wl_exportwallet_log`; access logs default to Common Log Format with ECID in Oracle's documented default `LogFormat`.
- Oracle Forms 12.2.1.4, **Tracing and Diagnostics**: <https://docs.oracle.com/en/middleware/developer-tools/forms/12.2.1.4/working-forms/tracing-and-diagnostics.html>
  - Supports Forms-specific diagnostic planning: Forms servlet diagnostics write to `$DOMAIN_HOME/servers/WLS_FORMS/logs/<application name>-diagnostic.log`; Forms trace files default to `forms_pid.trc` under the Forms system component trace location.
- Oracle Service Bus 14.1.2, **Monitoring Oracle Service Bus**: <https://docs.oracle.com/en/middleware/soa-suite/service-bus/14.1.2/administer/monitoring-oracle-service-bus.html>
  - Supports monitoring/fault/invocation requirements for Service Bus, but this pass did not find a universal raw log grammar suitable for a parser fixture.
- Oracle SOA Suite/BPM 14.1.2, **Administering Oracle SOA Suite and Oracle Business Process Management Suite** and **Monitoring SOA Composite Applications**: <https://docs.oracle.com/en/middleware/soa-suite/soa/14.1.2/administer/index.html> and <https://docs.oracle.com/en/middleware/soa-suite/soa/14.1.2/administer/monitoring-soa-composite-applications.html>
  - Supports SOA/BPM operational monitoring concepts (composite applications, instances, faults, flow tracing/metrics), but not a single native file format for all SOA audit/invocation events.

## Public Splunk TA / app position

- No official Splunk-supported add-on for the full Fusion Middleware/SOA/Discoverer estate was established in this pass.
- Splunk documentation paths for an Oracle WebLogic Server add-on were not publicly accessible from this environment (`docs.splunk.com` returned HTTP 403 for the checked Add-ons path), and Splunkbase search pages did not expose reusable WebLogic/FMW TA details without JavaScript/API access. Treat any locally owned Splunkbase/community TA as site evidence only until its license, sourcetypes, and props are reviewed.
- The SecHub `oracle_weblogic` Splunk artifacts remain the current custom TA slice for WebLogic server/access fixtures only. Do not copy proprietary TA internals into this repository.

## Source families and collection method

| Source family | Recommended collection path | Sourcetype posture | Notes |
| --- | --- | --- | --- |
| WebLogic server/domain logs | Universal Forwarder or file collector on AdminServer and Managed Server log paths | `oracle:weblogic:server` | Existing pack has alpha parser/search-time knowledge for selected server-log shapes; validate exact version/format and multiline stack traces. |
| WebLogic HTTP access logs | Universal Forwarder or file collector on the access log path configured per server/virtual host | `oracle:weblogic:access` | Confirm the configured access format before enabling; access format is administrator-configurable. |
| WebLogic security audit provider | File/collector after enabling and capturing provider output | `oracle:weblogic:audit` planning only | Needs exact audit-provider sample, principal/action/result fields, and sensitive-data review. |
| Node Manager | Universal Forwarder or file collector for `nodemanager.log` and any per-domain Node Manager paths | `oracle:weblogic:nodemanager` planning only | Official docs support the default path concept; validate lifecycle format and multiline behaviour before parser work. |
| Fusion Middleware ODL/diagnostic logs | Universal Forwarder or file collector on domain/server/component diagnostic logs | `oracle:fusion_middleware:diagnostic` planning only | ODL text/XML and multiline behavior are component/config dependent; capture boundaries first. |
| SOA Suite / OSB / BPM | SOA audit export, diagnostic log file collection, or site-owned API/report collector | `oracle:soa:audit` planning only | Invocation payloads can include business data; use allowlisted fields and raw preservation rules. |
| Forms / Reports | Use FMW/Forms/Reports-specific diagnostic and trace paths, not the WebLogic parser by default | source-specific or `oracle:fusion_middleware:diagnostic` after proof | Forms servlet logs use ODL-like diagnostics; trace files need a separate source-shape capture. |
| Oracle HTTP Server | Prefer `oracle_ohs` source-specific pack or web-server sourcetypes | `oracle:ohs:*` | Do not route Apache-style access/error logs through WebLogic parser unless source shape is equivalent and tested. |
| Discoverer | Legacy UF/file collector after path confirmation | `oracle:discoverer:server` planning only | Discoverer installations vary and may be obsolete; require local path/sample evidence before parser work. |

## Conservative `inputs.conf` use

`splunk/default/inputs.conf.example` is a disabled deployment-app scaffold. It intentionally uses placeholders such as `<DOMAIN_HOME>`, `<MW_HOME>`, `<ORACLE_HOME>`, and `<ORACLE_COLLECTOR_STAGING>` because Oracle estates differ. Operators should copy only the relevant stanza into a local deployment app, replace placeholders with a precise path, and enable one source family at a time.

Do not use broad overlapping monitor stanzas in production. In particular, avoid collecting the same file as both `oracle:weblogic:server` and `oracle:fusion_middleware:diagnostic`; split server logs, access logs, diagnostic logs, and component traces into non-overlapping paths.

## Operator enablement checklist

1. Inventory domains, AdminServer/Managed Server names, OHS/system-component names, log paths, rotation naming, access log format, diagnostic log format, and timezone settings.
2. Enable one disabled stanza from `splunk/default/inputs.conf.example` at a time in a site-owned Splunk deployment app.
3. Prove line breaking and timestamp extraction on current logs before enabling dashboards/alerts.
4. For SOA/OSB/BPM audit exports, define whether payloads, composite names, instance IDs, ECIDs, users, fault codes, and business identifiers are retained or masked.
5. Read back in Splunk: event count, source, host, sourcetype, timestamp, server/domain/component fields, request/fault identifiers, and raw preservation.
6. Promote only the proven lane; leave other FMW lanes catalogue-only.

## Evidence gaps before promotion

- Product-generated WebLogic server/access samples from a controlled lab or estate, replayed through SC4S/Splunk with indexed read-back.
- Exact security audit provider and Node Manager output examples.
- ODL/diagnostic multiline and timestamp handling per FMW component.
- SOA/OSB/BPM audit/export schema, payload handling, and privacy decision.
- Discoverer log path and sample evidence.
