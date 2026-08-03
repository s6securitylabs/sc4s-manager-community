# AWS Cloud Audit and Security pack

Conservative SecHub Resources SC4S pack for AWS CloudTrail, GuardDuty finding, and VPC Flow Log records relayed one event per line through S3/SQS, Kinesis, EventBridge, Firehose, Cribl, or another collector into a dedicated SC4S listener.

This is a cloud audit/security/network intake pack, not AWS validation. It preserves full records, routes fixture-backed high-value families, and exposes durable analyst fields while keeping trust `curated`/`unverified` until real AWS relay replay/read-back evidence exists.

## Evidence searched

- AWS CloudTrail User Guide: record contents and official log-file examples.
- AWS GuardDuty API Reference: `Finding` data type and public finding type documentation.
- AWS VPC User Guide: VPC Flow Log record fields and default/custom `logFormat` guidance.
- Pre-build evidence note: `docs/evidence/aws-cloud-audit-security-evidence-scan-20260607.md`.
- Unit 42 cloud-extortion coverage note: `docs/unit42-cloud-extortion-coverage-20260613.md`.

## Scope

- Listener: dedicated TCP syslog example on port `20068` with source tag `AWS_CLOUD_AUDIT_SECURITY`.
- Payloads: newline-delimited CloudTrail/GuardDuty JSON records plus one-line VPC Flow Log records; relay wrappers may be headerless or syslog-wrapped.
- Routed families: CloudTrail management events, Unit 42-style CloudTrail discovery/IAM-escalation/execution-staging/S3-impact branches, CloudTrail data events, GuardDuty findings, and VPC Flow Logs.
- SC4S/syslog-ng routing sends matched records to the same analyst sourcetypes used by the Splunk knowledge and dashboard: `aws:cloud:cloudtrail`, `aws:cloud:guardduty`, and `aws:cloud:vpcflow`. This is a parser-routing requirement, not replay/read-back proof.
- Default index: `main` for cloud audit, finding, and network-flow security telemetry.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20068` with source tag `AWS_CLOUD_AUDIT_SECURITY`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `main` / sourcetype(s) `aws:cloud:cloudtrail`, `aws:cloud:guardduty`, `aws:cloud:vpcflow`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Fixture semantics

- File: `test-events/aws_cloud_audit_security_test_events.txt`.
- Format: one compact JSON object or one VPC Flow Log text record per line.
- Wire/envelope: fixture file is headerless application payload; `scripts/send_tcp_20068.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; no multiline records.
- Timestamp: CloudTrail uses `eventTime`, GuardDuty uses `updatedAt`, and VPC Flow Logs use epoch `start`/`end` fields. Fixture timestamps are UTC or epoch seconds.
- Markers: `SC4S_AWS_CLOUD_AUDIT_SECURITY_TEST_*` values each occur exactly once. The fixture set now includes Unit 42 cloud-extortion sequence branches for `GetCallerIdentity`, `AttachRolePolicy`, `RunInstances`, `CreateFunction20150331`, `DeleteObject`, and `PutObject` using synthetic-equivalent AWS documentation-shaped CloudTrail records.
- VPC Flow Log fixture uses the default documented field order: `version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status`, plus a final synthetic marker token for fixture identification.

## Validation

This pack is not validated. Local CI checks schema, fixture marker uniqueness, parser syntax, Splunk knowledge files, dashboard XML, and pack exportability only.

Replay/read-back target:

```spl
index=main "SC4S_AWS_CLOUD_AUDIT_SECURITY_TEST_" earliest=-2h
| table _time index sourcetype source vendor product aws_family aws_account_id aws_region eventName eventSource user src_user src_ip user_agent action role_name policy_arn function_name instance_id bucket object_key severity signature signature_id resource_id interface_id packets bytes log_status marker _raw
```

### Disposable E2E harness

`pack.json` references `scripts/e2e_docker_compose.sh` as an idempotent Docker/Compose harness for disposable SC4S TEST -> Splunk TEST replay/read-back. Use:

```bash
packs/aws_cloud_audit_security/scripts/e2e_docker_compose.sh plan
packs/aws_cloud_audit_security/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/aws_cloud_audit_security/compose.yaml`, starts isolated Splunk and SC4S containers, mounts this pack's SC4S/Splunk artifacts, replays the 10 fixture events through TCP `20068`, samples SC4S/syslog-ng counters, and searches Splunk for the expected `aws:cloud:cloudtrail`, `aws:cloud:guardduty`, and `aws:cloud:vpcflow` read-back. It generates an ephemeral HEC token at compose-write time unless `SPLUNK_HEC_TOKEN` is supplied; no token is committed. It fails closed when Splunk or syslog-ng is not healthy, TCP `20068` is not listening, the indexed marker count is not exactly 10, or any marker event has the wrong `main` index, expected AWS sourcetype, or `aws_cloud_audit_security` source.

Promotion to `validated` requires replaying all 10 fixture events through SC4S TEST and reading them back from Splunk TEST with the expected sourcetypes, index, source, timestamps, and normalized fields. Field validation additionally requires retained real AWS source-version or vendor-certified sample evidence. A passing disposable harness run remains fixture-backed lab evidence only; it does not prove any live AWS account, EventBridge/Firehose/S3/SQS/CloudWatch, Cribl, or other collector envelope.

## Unit 42 cloud-extortion dashboard

Splunk dashboard: `splunk/default/data/ui/views/aws_cloud_audit_security_soc.xml`.

Use it for CloudTrail/GuardDuty/VPC hunts aligned to the Unit 42 exposed-credential cloud-extortion pattern: IAM/STS/S3/SES discovery, `CreateRole` + `AttachRolePolicy` privilege escalation, EC2/Lambda staging, S3 object read/delete/write activity, source IP/user-agent pivots, and GuardDuty/VPC corroboration. Results are triage candidates, not automatic malicious verdicts; confirm expected automation, identity ownership, source IP legitimacy, and S3 business context.

## Reduction stance

No event drops or field deletions are enabled by default. `docs/aws_cloud_audit_security_reduction_candidates.csv` lists advisory candidates only. Identity, account, region, API action, source IP, user agent, request/response, finding identity/type/severity, resource context, network tuple, packet/byte counters, and log status are retained by default because they are central to incident reconstruction, cloud audit challenge, detection triage, and response scoping.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-07.md` shows port `20068` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from public AWS documentation and the attributed Unit 42 behavior sequence; they are not real tenant records and do not include real keys, tokens, bucket names, or account data.
- Collector wrappers may nest records under envelope fields or alter VPC Flow Log formats; compare local delivery output before promotion.
- Optional reduction must be tested against production-like AWS data before enablement.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real AWS relay replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, account/region/resource identity, CloudTrail action semantics, GuardDuty finding fields, VPC flow tuple fields, and normalized fields.
