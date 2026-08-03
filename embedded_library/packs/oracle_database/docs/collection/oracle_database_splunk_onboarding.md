# Oracle Database Server Splunk onboarding research and collection guidance — 2026-07-06

## Attribution and access notes

This note is derived from public vendor documentation and public Splunkbase metadata accessed 2026-07-06. It contains SecHub analysis and conservative deployment guidance only; no Oracle product samples, Splunk TA files, proprietary SPL, or dashboard XML are copied.

## Scope

Oracle Database Server collection candidates covered here:

- Unified Audit (`UNIFIED_AUDIT_TRAIL`) and traditional audit (`DBA_AUDIT_TRAIL`, OS/XML audit files).
- Fine-Grained Auditing (`DBA_FGA_AUDIT_TRAIL`).
- Oracle Net listener logs, including ADR listener text/XML candidates.
- Database ADR alert/diagnostic logs (`V$DIAG_INFO`, `V$DIAG_ALERT_EXT`, alert text/XML files).
- RAC/Grid Infrastructure/ASM candidates where the log path is deployment-specific.

## Official Oracle source evidence

| Area | Public reference | Evidence-supported collection implication |
| --- | --- | --- |
| Unified Audit | Oracle `UNIFIED_AUDIT_TRAIL`: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/UNIFIED_AUDIT_TRAIL.html | Treat as a database view/table polling source. Use DB Connect or a site-owned collector with checkpoints and one row per event. Preserve DB user, action, object, client, return-code, CDB/PDB, SQL, and policy fields where present. |
| Traditional audit setting | Oracle `AUDIT_TRAIL`: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/AUDIT_TRAIL.html | Audit location/format depends on initialization setting: database table, OS audit files, XML audit, extended variants, or disabled. Do not enable a file monitor until the local setting and format are known. |
| OS audit directory | Oracle `AUDIT_FILE_DEST`: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/AUDIT_FILE_DEST.html | OS audit file collection should monitor the configured audit-file destination rather than assume one universal path. |
| Traditional audit rows | Oracle `DBA_AUDIT_TRAIL`: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/DBA_AUDIT_TRAIL.html | Use table/view polling or staged row exports when traditional audit is database-backed. |
| FGA rows | Oracle `DBA_FGA_AUDIT_TRAIL`: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/DBA_FGA_AUDIT_TRAIL.html | Use table/view polling or staged exports. Treat SQL text/binds and policy context as sensitive but security-relevant; masking must be opt-in and tested. |
| Syslog audit option | Oracle `AUDIT_SYSLOG_LEVEL`: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/AUDIT_SYSLOG_LEVEL.html | Some audit records can be written to the operating-system audit/syslog path when configured. This supports syslog/file relay as a deployment option, not a default parser claim. |
| ADR inventory | Oracle `V$DIAG_INFO`: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/V-DIAG_INFO.html | Query ADR paths on each host/SID instead of hard-coding paths; use the view to discover ADR base/home and trace/alert locations. |
| ADR alert rows | Oracle `V$DIAG_ALERT_EXT`: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/V-DIAG_ALERT_EXT.html | Alert data can be collected as rows/exports as an alternative to text/XML file tailing. |
| Oracle Net ADR/logs | Oracle Net Services troubleshooting: https://docs.oracle.com/en/database/oracle/oracle-database/19/netag/troubleshooting-oracle-net-services.html | Listener diagnostics live in ADR homes with alert XML (`alert/log.xml`) and trace/text logs. Validate listener, SCAN listener, TCPS, and failure formats separately. |
| Clusterware/Grid | Oracle Clusterware troubleshooting: https://docs.oracle.com/en/database/oracle/oracle-database/19/cwadd/troubleshooting-oracle-clusterware.html | Grid/RAC logs are component-specific. Use narrow component monitors and ADR discovery; do not recursively ingest all Grid logs without volume and boundary tests. |

## Splunk official/community TA coverage

| Component | Public metadata observed | SecHub position |
| --- | --- | --- |
| Splunk Add-on for Oracle Database | Splunkbase app 1910, `Splunk_TA_oracle`, Splunk-built, cloud compatible. Public API description says it collects Oracle Database Server standard and fine-grained audit trails, trace files, incident, alert, listener, and other OS logs, and leverages Splunk DB Connect for performance and inventory data. URL: https://splunkbase.splunk.com/app/1910/ | **Prefer official TA where available.** Do not copy its app content. Use this pack's `inputs.conf.example` only as conservative onboarding scaffolding, path inventory, or a bridge when TA details are insufficient/not installed. |
| Splunk DB Connect | Splunkbase app 2686, Splunk-built generic SQL database import/export app with Oracle support. URL: https://splunkbase.splunk.com/app/2686/ | **Preferred collection path** for `UNIFIED_AUDIT_TRAIL`, `DBA_AUDIT_TRAIL`, `DBA_FGA_AUDIT_TRAIL`, `V$DIAG_ALERT_EXT`, inventory, and performance views. DBX inputs are configured in DB Connect, not in this `inputs.conf.example`. |
| Splunk DBX Add-on for Oracle JDBC | Splunkbase app 6151, Splunk-built Oracle JDBC driver add-on for DB Connect. URL: https://splunkbase.splunk.com/app/6151/ | Required/expected companion for DB Connect Oracle polling in many deployments; still site-owned to install and manage driver/version compatibility. |
| Oracle Unified Audit app | Splunkbase app 6172, third-party app focused on Oracle unified audit dashboards; public metadata only reviewed. URL: https://splunkbase.splunk.com/app/6172/ | Dashboard/coverage prior art only. Do not vendor content or assume parser compatibility. |
| Omega Core Audit for Oracle | Splunkbase app 4307, third-party app for Omega Core Audit deployments. URL: https://splunkbase.splunk.com/app/4307/ | Product-specific prior art, not a native Oracle Database TA replacement. |
| Legacy Log File Analysis for Oracle 11g | Splunkbase app 1538, older restricted/contact-vendor listing noted in prior repo research. URL: https://splunkbase.splunk.com/app/1538/ | Historical evidence that Oracle monitoring mixes files, scripts, audit trails, and DB Connect; not current validation. |

Splunk docs pages for the Add-on were not fetchable from this environment (`HTTP 403` on `docs.splunk.com/Documentation/AddOns/released/OracleDB/...`), so this note relies on accessible Splunkbase public API metadata plus existing repo research. Evidence gap: local installation of `Splunk_TA_oracle` should be inspected by the operator to map exact official sourcetypes, inputs, props, and CIM coverage before choosing custom SecHub sourcetypes.

## Conservative collection model

1. **Prefer table/view polling for audit rows.** Use Splunk DB Connect or a site-owned collector for `UNIFIED_AUDIT_TRAIL`, `DBA_AUDIT_TRAIL`, `DBA_FGA_AUDIT_TRAIL`, and `V$DIAG_ALERT_EXT`. Use stable checkpoint columns/timestamps, record database/container identity, and emit one event per row if staging to files.
2. **Use file monitoring for OS/ADR logs only after path discovery.** Discover per-host values through Oracle configuration and `V$DIAG_INFO`; then monitor narrow files such as `adump/*.aud`, `diag/.../trace/alert_*.log`, `diag/.../alert/log.xml`, and listener `trace/listener.log`/`alert/log.xml`.
3. **Keep XML/text variants distinct until proven.** Listener and alert logs can exist as text and XML under ADR. Validate line breaking/timestamps for each variant before routing them to a common sourcetype.
4. **Do not broadly tail trace/incident directories by default.** Trace and incident files may be high volume and sensitive. Add targeted stanzas only for a documented SOC use case with replay/read-back and retention approval.
5. **RAC/Grid/ASM are separate candidates.** SCAN listener, ASM, CRS/CSS/OHASD and cluster resource logs must be enabled component-by-component after path and volume proof.
6. **No default lossy filtering.** SQL text, binds, object names, users, modules, service names, client host/IP, error codes, and policy context are often incident-critical. Redaction/masking must be opt-in and evidence-backed.

## Implemented SecHub artifacts

- `splunk/default/inputs.conf.example` adds disabled, placeholder stanzas for:
  - traditional OS audit files;
  - staged traditional/unified/FGA JSON exports;
  - listener text/XML ADR candidates;
  - database ADR alert text/XML candidates;
  - selected RAC/Grid/ASM candidate paths.
- The example uses SecHub sourcetypes (`oracle:database:*`) rather than official TA sourcetypes because the pack is still unverified and does not redistribute Splunk TA knowledge. If a customer installs `Splunk_TA_oracle`, they should prefer official TA sourcetypes/props or add an explicit, tested sourcetype bridge.

## Evidence gaps before promotion

- Fetch/inspect current official Splunk Add-on for Oracle Database documentation or an installed `Splunk_TA_oracle` to confirm current sourcetypes, file inputs, DBX inputs, field extractions, CIM tags, and supported Oracle versions.
- Generate or obtain sanitized real Oracle Database records for each enabled source mode.
- Run Splunk ingestion/read-back for each stanza/source mode, proving event count, source, sourcetype, host, timestamp, line breaking, multiline/XML handling, and sensitive-field handling.
- Confirm path layouts for Linux/Windows, CDB/PDB, RAC, SCAN listeners, ASM/Grid homes, and Oracle versions in target estates.
