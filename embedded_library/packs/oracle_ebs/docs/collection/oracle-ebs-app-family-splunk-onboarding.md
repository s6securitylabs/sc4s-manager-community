# Oracle E-Business Suite, OLM, APEX, and ECC Splunk onboarding guidance — 2026-07-06

## Evidence boundary

This note is based on public Oracle documentation already recorded in the SecHub Oracle evidence set plus public Splunkbase/Splunk TA inventory review. It contains SecHub/S6 collection guidance only; it does not copy Oracle product logs, proprietary Splunk TA files, or third-party parser content.

The existing `oracle_ebs` pack supports a **site-owned normalized JSON relay** (`sourcetype=oracle:ebs:security:json`). It is not native collection from EBS tables or files. Native EBS, OLM, APEX, and ECC sources require local source-shape capture and read-back before parser promotion.

## Source families and collection method

| Source family | Recommended collection path | Why | Default SecHub sourcetype posture |
| --- | --- | --- | --- |
| EBS Sign-On Audit | DB Connect or site-owned SQL collector, then normalized JSON relay | Sign-on data is table/query based, not a native syslog feed | Normalize into `oracle:ebs:security:json` with `event_family=ebs_signon_success` / `ebs_signon_failure` |
| EBS AuditTrail | DB Connect or scheduled export of approved AuditTrail shadow tables | AuditTrail identifies changed application objects but serialization is estate-specific | Normalize into `oracle:ebs:security:json` with `event_family=ebs_audittrail_sensitive_change` |
| FND/application errors | `FND_LOG_MESSAGES` table export plus selected app-tier files | Useful security/application context; may contain business data | Normalize into `oracle:ebs:security:json` or keep raw as `oracle:ebs:application:raw` until parsed |
| Concurrent manager/request logs | Targeted file monitors plus metadata table export | High-volume and business-sensitive; request IDs connect business operations to failures | Keep raw `oracle:ebs:concurrent:raw` or normalize selected security events |
| Workflow / Notification Mailer | Table/log export from Workflow and mailer components | Critical for approval-routing and fraud investigations | Normalize into `oracle:ebs:security:json` with workflow event families |
| OHS/WebLogic/Forms/OAF app tier | Use Oracle OHS/WebLogic/FMW packs where exact format is known | These are middleware/web logs, not EBS table audit records | `oracle:weblogic:*`, `oracle:fusion_middleware:*`, or normalized EBS relay for selected security events |
| Oracle Learning Management (OLM) | Treat as an EBS module: AuditTrail, Sign-On Audit, FND/concurrent/workflow exports tagged with OLM module context | No separate native OLM log shape is established here | Custom staged sourcetypes `oracle:olm:*` only as collector handoff; normalize security events into EBS relay |
| Oracle APEX | DB Connect/site-owned collector from APEX activity/debug/workspace views plus ORDS/OHS/WebLogic access logs | APEX activity is database/view backed; web tier is separate | `oracle:apex:activity:json` / `oracle:apex:debug:json` until parser evidence exists |
| Enterprise Command Center (ECC) | EBS normalized relay for advisory/security events plus targeted ECC import/framework/data-load logs | ECC appears as both an EBS module/advisory surface and application-tier logs | `oracle:ebs:security:json` with `event_family=ebs_enterprise_command_center`; raw ECC sourcetypes remain planning only |

## Relevant TA / app position

- **No official Splunk TA coverage was established for native EBS/OLM/APEX/ECC in this pass.** Use existing Splunk DB Connect for database-backed collection and SecHub custom sourcetypes for normalized relays.
- **Do not put SQL credentials or checkpoint state inside this pack.** DB Connect inputs, SQL collectors, and export jobs are estate-owned.
- **Do not directly assign raw EBS app-tier logs to `oracle:ebs:security:json`.** That sourcetype expects normalized JSON with `vendor=oracle`, `product=e_business_suite`, `source_mode=ebs_security_json_relay`, `event_family`, and UTC `event_time`.
- **Use official/product-specific knowledge when it exists.** WebLogic/OHS/FMW should stay in their own source families and only feed EBS relay events when a collector explicitly maps a source event to an EBS security/audit family.

## Operator enablement checklist

1. Select one source family and identify the real source owner: DBA, Apps DBA, Middleware admin, or SOC collector owner.
2. Define the exact collection mode: DB Connect query, SQL spool/export, file monitor, API/report export, or normalized relay.
3. Capture source-shape evidence: field list, one event per row/file/message, timestamp/timezone, null/escaping, multiline behaviour, checkpoint key, host/source identity, and sensitive-field review.
4. Enable only the matching disabled stanza from `splunk/default/inputs.conf.example` or from the product-level `products/oracle-enterprise/splunk/inputs.conf.example`.
5. Read back in Splunk: event count, index, sourcetype, source, host, timestamp, key fields, and raw preservation.
6. Only then add parser/dashboard/search-time knowledge beyond the existing normalized JSON pack.

## Evidence gaps before promotion

- Exact native EBS export shape for Sign-On Audit, AuditTrail, FND, concurrent, workflow, Forms/OAF and module-specific records.
- Whether OLM has any separate operational log stream worth parsing outside EBS table/app-tier context.
- APEX chosen source views/API/export shape and ORDS/web-tier correlation plan.
- ECC exact framework/import/data-load log paths and emitted record examples.
- Replay/read-back evidence for any enabled source lane.
