# Unit 42 cloud-extortion research coverage note — 2026-06-13

## Attribution

- Title: “Leaked Environment Variables Allow Large-Scale Extortion Operation in Cloud Environments”
- Author / organisation: Unit 42, Palo Alto Networks
- Original URL: `https://unit42.paloaltonetworks.com/large-scale-cloud-extortion-operation/`
- Published: 2024-08-15
- Accessed: 2026-06-13
- Licence / terms: not identified as permissively redistributable during this review; this note stores attribution, derived analysis, and short technical references only, not a copy of the article text.

This note records pack coverage and detection recommendations for the `aws_cloud_audit_security` source pack. It is research-to-pack mapping only; it is not replay/read-back validation and must not raise trust or quality labels.

## Critical analysis of the research

Unit 42 describes a credible exposed-secret cloud intrusion pattern rather than an AWS platform vulnerability. The useful defensive value is the sequence of observable AWS control/data-plane actions, not just the published indicators.

Observed / reported stages that matter for this pack:

1. Initial access through leaked `.env` files containing long-lived AWS IAM access keys.
2. Early discovery with `GetCallerIdentity`, then IAM/S3/SES enumeration such as `ListUsers`, `ListBuckets`, `GetSendQuota`, `ListVerifiedEmailAddresses`, `GetAccountSendingEnabled`, `GetAccount`, and `ListIdentities`.
3. IAM privilege escalation by creating a role and attaching broad administrative policy: `CreateRole` followed by `AttachRolePolicy` with `AdministratorAccess`.
4. Failed EC2 staging attempts: `CreateSecurityGroup`, `AuthorizeSecurityGroupIngress`, `CreateKeyPair`, and `RunInstances`, including permissive ingress and compute-optimised instance intent.
5. Successful Lambda staging: `CreateFunction20150331` / `CreateFunction`, with automatic `CreateLogGroup` and `CreateLogStream` records; Unit 42 reported function name `ex` and role name `lambda-ex` in the investigated activity.
6. S3 impact: object access/exfiltration and deletion, then ransom-note style object writes. Detection quality depends heavily on CloudTrail data events or S3 access logging being enabled before the incident.
7. Network/source context: Tor/VPN/VPS/cloud/ISP source IPs and user-agent pivots were important to Unit 42’s reconstruction, but individual IP indicators age quickly. Prefer behaviour plus local threat-intel enrichment over static IOC-only matching.
8. Cost and Usage Reports can show S3 `GetObject` bytes-out and `DeleteObject` bytes-deleted spikes when CloudTrail data events/S3 access logs were absent, but they are coarse and should be treated as impact scoping, not primary detection.

Important caveats:

- The Unit 42 queries are hunting seeds. They explicitly require analyst review and should not be treated as automatically malicious.
- The AWS API names are strong detection anchors, but benign automation can run some of them. Correlation across identity, time, source IP, user agent, region fan-out, new role/policy state, and S3 object activity is what makes the pattern actionable.
- The pack cannot detect exposed `.env` files directly unless web/app scan telemetry is onboarded separately. It covers AWS-side consequences after credential use.

## Current pack coverage

Covered by `aws_cloud_audit_security`:

- `aws:cloud:cloudtrail` sourcetype for CloudTrail management and S3 data events when relayed into the pack listener.
- `aws:cloud:guardduty` sourcetype for GuardDuty findings that may corroborate compromised credentials, anomalous API use, or network behaviour.
- `aws:cloud:vpcflow` sourcetype for network-flow context around cloud-hosted staging or exfiltration paths.
- Normalized fields for account, region, event source/name, actor, source IP, user agent retention through raw/KV fields, resource context, GuardDuty type/severity, and VPC tuple/counters.
- Splunk dashboard `aws_cloud_audit_security_soc.xml`, with hunts for Unit 42-relevant stages: discovery, IAM privilege escalation, EC2/Lambda staging, S3 object access/delete/write, source IP/user-agent pivots, and GuardDuty/VPC context. The 2026-06-15 hardening pass added synthetic-equivalent CloudTrail fixture rows for `GetCallerIdentity`, `AttachRolePolicy`, `RunInstances`, `CreateFunction20150331`, `DeleteObject`, and `PutObject` so those dashboard branches are exercised by pack fixtures rather than remaining research-only searches.

Not currently covered or not guaranteed:

- Direct `.env` exposure scanning telemetry from public web assets.
- AWS Cost and Usage Report ingestion. CUR can help scope S3 bytes-out/deletion when data-event logging was absent, but it is not currently a source family in this pack.
- Native S3 server access logs as a separate record shape. CloudTrail S3 data events are represented; server access log line format remains a separate candidate source shape.
- A validated live AWS relay or Splunk read-back. The pack remains `curated` / `unverified`. The Unit 42 sequence fixtures are synthetic-equivalent and documentation-shaped; they are not real incident records.
- Static Unit 42 IP IOC matching. Those indicators can be used in local lookup enrichment, but the pack should not bake aging threat-intel into default logic.

## Recommendations for AWS packs

1. Keep `aws_cloud_audit_security` as the primary pack for this intrusion class because the required sourcetypes are CloudTrail, GuardDuty, and VPC Flow Logs.
2. Add/maintain dashboard coverage around behaviour sequences, not just single API names. High-value sequence: `GetCallerIdentity` / enumeration → `CreateRole` + `AttachRolePolicy` → `CreateFunction*` or EC2 staging → S3 `GetObject`/`DeleteObject`/ransom-note `PutObject`.
3. Preserve CloudTrail `requestParameters`, `responseElements`, `userIdentity`, `sourceIPAddress`, `userAgent`, `resources`, error fields, bucket/key names, and region/account context by default. These are not safe reduction targets for this incident class.
4. Treat CloudTrail data events for S3 as a required deployment recommendation for extortion readiness. Without them, the dashboard can still see management-plane actions but cannot reliably prove object exfiltration/deletion details.
5. Consider a future `aws_s3_access_and_usage` source-shape expansion for S3 server access logs and Cost and Usage Reports. Keep it separate unless exact line/CSV schema fixtures and relay envelopes are added.
6. Do not promote trust/quality from this research-to-dashboard mapping. Promotion still requires SC4S TEST → Splunk TEST replay/read-back against AWS-shaped fixture events or, ideally, a controlled AWS relay.
7. Consider local lookup integration for Tor/VPN/VPS/cloud-source enrichment, but keep it optional and environment-owned because provider/IP classifications drift.

## Dashboard analyst use

Start with the `AWS Cloud Audit and Security SOC` dashboard, set the index/account filter, and review:

- Whether reconnaissance APIs were run by the same actor/source/user-agent before changes.
- Whether `CreateRole` and `AttachRolePolicy` created or modified suspicious roles or attached `AdministratorAccess`.
- Whether EC2 or Lambda staging occurred quickly after privilege changes.
- Whether S3 object reads/deletes/writes spiked after the same actor/source appeared.
- Whether GuardDuty findings or VPC Flow Logs corroborate suspicious network endpoints.

Result interpretation should remain conservative: a row is a triage candidate until the analyst confirms identity ownership, expected automation, change tickets, source-IP legitimacy, and S3 business context.

## 2026-06-15 fixture-hardening update

This pass added fixture-backed coverage for the behavior sequence already described above: STS discovery, IAM policy attachment, EC2 staging, Lambda staging, S3 object deletion, and S3 ransom-note-style object write. The source evidence remains AWS CloudTrail public record schema/examples plus Unit 42 attributed behavioral analysis. No static threat-intel IOCs, real cloud records, or proprietary detections were copied.
