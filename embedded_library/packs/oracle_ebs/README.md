# Oracle E-Business Suite security and audit logs

Curated SecHub Resources pack for Oracle E-Business Suite security/audit monitoring through a conservative normalized JSON relay. The pack focuses on EBS Sign-On Audit, AuditTrail-style sensitive changes, FND/application security errors, concurrent requests, workflow/mailer changes, OHS/WebLogic/Forms/OAF app-tier telemetry, and May/June 2026 advisory-focus modules such as Oracle Payments / File Transmission and Enterprise Command Center Framework.

## Ingestion and collection notes

This pack does **not** collect Oracle E-Business Suite directly. A site-owned collector or relay must extract approved EBS table/log/API/file sources, sanitize fixture copies when needed, and emit one JSON object per line with:

- `vendor=oracle`
- `product=e_business_suite`
- `source_mode=ebs_security_json_relay`
- `event_family` set to one of the declared EBS families
- `event_time` in UTC ISO-8601 form
- raw business/security context preserved unless a local, approved, replay-tested reduction rule exists

Typical source paths are EBS Sign-On Audit queries, AuditTrail-generated audit table exports, `FND_LOG_MESSAGES` exports, concurrent request metadata/logs, workflow/mailer tables or logs, OHS access/security logs, WebLogic server/security logs, and Forms/OAF application-tier logs. Collector credentials/checkpoints are owned by the customer/SOC environment, not by this pack.

Default routing is a dedicated TCP listener example on `20104` with sourcetype `oracle:ebs:security:json` and index `main`. Adjust index locally before deployment if required.

Additional conservative onboarding guidance for EBS application-family sources is available in `docs/collection/oracle-ebs-app-family-splunk-onboarding.md`, with disabled example stanzas in `splunk/default/inputs.conf.example`. Those examples cover the normalized EBS relay plus evidence-gated OLM staged exports, APEX activity/debug staged exports, and ECC Server/Framework/import/data-load log categories. They are not enabled defaults and do not claim native parser validation.

## Splunk dashboard scope

`oracle_ebs_security_overview.xml` helps answer:

- Is the EBS normalized relay arriving?
- Which EBS event families, applications, modules, users, responsibilities, source IPs, and risk buckets are visible?
- Are Oracle Payments / File Transmission and June 2026 ECC/module advisory-focus events present?
- Which sign-on/authentication failures, admin/security configuration changes, AuditTrail object/account changes, concurrent request failures, workflow/mailer errors, OHS, WebLogic, Forms/OAF, and FND security events need triage?
- Which raw events should analysts copy into manual SPL drilldown while preserving vendor context?

The dashboard is scoped only to `source_mode=ebs_security_json_relay` and grounded in synthetic-equivalent fixtures plus Splunk JSON extraction. It is not live Oracle field validation, not an exploit detector, and not evidence that any estate has patched or been compromised.

## Event families

- `ebs_signon_success`
- `ebs_signon_failure`
- `ebs_audittrail_sensitive_change`
- `ebs_fnd_security_error`
- `ebs_concurrent_privileged_request`
- `ebs_workflow_mailer_change`
- `ebs_ohs_suspicious_http`
- `ebs_weblogic_security`
- `ebs_forms_oaf_error`
- `ebs_oracle_payments_file_transmission`
- `ebs_enterprise_command_center`
- `ebs_supplier_payroll_financials`

## May/June 2026 advisory context

- May 2026 Oracle EBS risk matrix includes CVE-2026-46817 for Oracle Payments / File Transmission, affecting EBS 12.2.3-12.2.15 and described by Oracle as unauthenticated HTTP network access leading to Oracle Payments takeover. The Hacker News reported active exploitation in June 2026.
- June 2026 Oracle EBS risk matrix contains a broader set of high-severity EBS modules, including Enterprise Command Center Framework, iSupplier Portal, Receivables, Payroll, Cost Management, HR, iSupport, Universal Work Queue, and other financial/supply-chain modules.

See `docs/research/thehackernews-oracle-ebs-cve-2026-46817-20260701.md` for article attribution and advisory-to-dashboard mapping. See `docs/research/oracle-official-ebs-logging-audit-source-evidence-20260701.md` and `docs/research/oracle-official-ebs-source-shape-gap-addendum-20260701.md` for Oracle documentation/eTRM source-family evidence, official-source shape boundaries, and native-parser blockers.

## Field and reduction stance

No default drops, masking, or null routing are shipped. EBS user names, responsibilities, changed values, request parameters, workflow notification context, SQL/bind-like fields, hostnames, source IPs, and business object values can be sensitive but are often incident-critical. Any local reduction must be opt-in and replay/read-back tested before use.

The expanded fixtures remain synthetic-equivalent and use `SYNTH_` actor/object values plus documentation IP ranges. They add admin/security configuration, concurrent request failure, and Workflow Notification Mailer error coverage using only field families justified by the Oracle documentation/eTRM evidence note; they do not introduce native parser claims.

## 2026-07-06 Splunk onboarding guidance

`docs/collection/oracle-ebs-app-family-splunk-onboarding.md` and `splunk/default/inputs.conf.example` add disabled, conservative Splunk collection examples for EBS, Oracle Learning Management, APEX, and Enterprise Command Center lanes. The examples preserve the pack boundary: `oracle:ebs:security:json` is a normalized relay sourcetype, while native table/file/API sources still require local source-shape proof and Splunk read-back before parser promotion.

## Validation status

Local schema/fixture/XML checks can prove this pack is internally sane. They do not prove native EBS source validation. Current evidence posture remains:

- `quality_status`: `curated`
- `trust_level`: `unverified`
- `validation_harness.status`: `blocked` until source-backed replay/read-back exists

Do not promote this pack to validated/field-validated without SC4S listener, HEC delivery, and Splunk indexed read-back evidence for a selected Oracle EBS source mode.
