# Oracle Database demo-lab data acquisition plan — 2026-07-02

## Purpose

Identify practical, low-cost ways to generate **real Oracle Database demo lab logs** for the `oracle_database` pack without copying restricted third-party samples or inventing product output.

This is an acquisition plan, not validation evidence. It does not promote `quality_status`, `trust_level`, `validated`, `s6_verified`, `field_validated`, or `field_verified`.

## Best available lab-data routes

| Route | Source | Cost / openness | Licence / redistribution posture | Evidence value |
|---|---|---:|---|---|
| Oracle Database Free container image | `https://container-registry.oracle.com/ords/f?p=113:4:100::::P4_REPOSITORY,AI_REPOSITORY_NAME,P4_REPOSITORY_NAME:3,Oracle%20Database%20Free,database/free` | Free-to-use Oracle image, not open source | Oracle image terms apply; do not redistribute database binaries. Sanitised generated logs can be retained if they contain no Oracle copyrighted sample text or secrets. | Strongest route for live source-generated Unified Audit, listener, and alert/ADR records. |
| Oracle official Docker build files | `https://github.com/oracle/docker-images/tree/main/OracleDatabase/SingleInstance/dockerfiles` | Build scripts are public; database software remains Oracle-licensed | Repository scripts are under Oracle's repository licence; the installed database is governed by Oracle terms. Do not vendor binaries into this repo. | Strong route when container registry access is unavailable. |
| Community Oracle Free/XE container wrappers | `https://github.com/gvenzl/oci-oracle-free`, `https://hub.docker.com/r/gvenzl/oracle-free`, `https://github.com/gvenzl/oci-oracle-xe`, `https://hub.docker.com/r/gvenzl/oracle-xe` | Free community packaging around Oracle Free/XE images | Convenience wrapper; Oracle database terms still apply. Verify repository licence before reusing wrapper scripts. Generated logs can be sanitised and attributed as lab-generated. | Practical fastest route for disposable lab generation. |
| Oracle Vagrant DB projects | `https://github.com/oracle/vagrant-projects/tree/main/OracleDatabase/21.3.0-XE` | Public Vagrant project for Oracle XE lab | Scripts public; database software terms still apply. Do not redistribute VM images or binaries. | Useful fallback where Docker is unsuitable. |
| Existing public parser/sample repos | Elastic, oralunk, listener/alert parsers recorded in research notes | Mostly source-shape only | Licence varies; Oracle docs and many no-licence repos are not fixture sources. | Use for cross-checking field shape, not for production validation. |

## Recommended first lab target

Use Oracle Database Free or XE in a disposable Docker/VM lab and capture **source-generated** records for one narrow variant at a time:

1. `oracle_database_unified_audit`
   - Enable or confirm Unified Auditing.
   - Generate successful and failed authentication, privileged action, and object access events.
   - Capture the selected export/envelope: syslog-style record, SQL/CSV/JSON export from `UNIFIED_AUDIT_TRAIL`, or collector output with the raw row retained.
2. `oracle_database_listener`
   - Capture `listener.log` from successful connect and failed/refused connection attempts.
   - Preserve standalone listener shape first; defer RAC/SCAN/TCPS variants.
3. `oracle_database_alert_adr`
   - Capture ADR alert text/XML or `V$DIAG_ALERT_EXT` export for one lifecycle message and one ORA/error message.

Traditional audit-file fixtures already have source-shape coverage, but should still be replaced or complemented with Oracle Free/XE generated records before any trust promotion.

## Sanitisation rules

- Replace database names, hostnames, usernames, services, schemas, object names, IPs, SQL text, bind values, filesystem paths, and container identifiers with documentation-range or `LAB_` values.
- Preserve record boundary, field order, delimiters, labels, null/empty rendering, quoting, timestamp format/timezone, multiline behavior, and error/status tokens.
- Keep original raw lab captures outside public/export paths until sanitised.
- Retain a private capture note with exact product version, image tag, container/VM route, audit configuration, commands used, and sanitisation map.

## Minimum evidence to promote beyond source-shape alpha

Before raising the Database pack above catalogue/source-shape alpha, capture and commit:

- Sanitised lab-generated fixture file for the selected variant only.
- Collection/runbook note with product version, image source, configuration, and capture path.
- Parser/collector artifacts matching the exact envelope that SecHub/SC4S will see.
- Replay/read-back evidence showing event count, index, sourcetype, source, host, timestamps, required extracted fields, marker fields, and raw preservation.

## Current conclusion

A free demo lab path is feasible for Database using Oracle Database Free/XE containers or Vagrant, but it is **not open-source product output**. The safe route is to generate our own lab records, sanitise them, and document Oracle licensing boundaries. Public third-party samples remain source-shape references unless their licence explicitly permits redistribution.
