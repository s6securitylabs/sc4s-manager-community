# JFrog Platform pack

Conservative SecHub Resources SC4S pack for JFrog Platform relay logs, focused on source shapes backed by public evidence: Artifactory request/access/traffic records, Access security-audit records, router request JSON, narrow Distribution request/access records, and narrow Xray request/service/webhook records.

This pack is for curated intake and required-field review, not for JFrog validation. Trust remains `unverified` and quality remains `curated` until real JFrog relay replay and Splunk indexed read-back evidence exists.

## Evidence searched

- `docs/evidence/jfrog-platform-evidence-scan-20260608.md` records public parser/integration evidence from JFrog, Sumo Logic, Datadog, and community/JFrog-maintained collector repositories.
- 2026-06-18 evidence retry verified official JFrog log-file docs, Xray DB/service-log KB, Xray webhook payload-format KB, Cloud Log Collection limitations, JFrog-maintained Distribution parser evidence, and Pipelines path-only evidence. This unblocked narrow Xray request/service/webhook fixtures only at the time.
- 2026-06-22 Distribution scoped pass used JFrog-maintained Apache-2.0 parser evidence plus official log/access docs to add narrow `distribution-request.log` and `distribution-access.log` coverage. Distribution release-bundle lifecycle/status/business-event semantics and Pipelines structured fixtures remain blocked until exact public schemas, emitted examples, or sanitized source records are available.
- Artifactory request logs: pipe-delimited timestamp, trace ID, source IP, user, method, URL, status, size, duration, and user-agent fields.
- Artifactory access logs: timestamp, trace ID, raw bracketed `action_response`, repository path, user, and client IP context.
- Artifactory traffic logs: numeric timestamp, trace/request ID, traffic direction such as `DOWNLOAD`, source IP, repository path, and transfer byte count.
- Access security-audit logs: pipe-delimited timestamp, token ID, user IP, user, principal, entity, event type, event, and data-changed context.
- Router request logs: JSON request records with a `time` timestamp.

- Xray request/service/webhook logs: generic JFrog request-log structure for `/xray/` request paths, Xray service-log bracketed records, and Xray webhook JSON payload fields such as `alert_id`, `top_severity`, `watch_name`, `policy_name`, `policy_rule`, and `issues`.

Distribution request/access parser evidence is implemented narrowly for `distribution-request.log` and `distribution-access.log`. Distribution release-bundle lifecycle/status/business-event semantics remain blocked because public evidence did not expose exact emitted schemas. Pipelines remains blocked for structured fixtures because public evidence found only logger paths/raw forwarding, not exact build/provenance event schemas.

## Scope

- Listener: dedicated TCP syslog example on port `20070` with source tag `JFROG_PLATFORM`.
- Payloads: one JFrog record per line; fixture file is headerless application payload and the send helper wraps each line in RFC5424-style TCP syslog.
- Routed sourcetypes: `jfrog:artifactory:request`, `jfrog:artifactory:access`, `jfrog:artifactory:traffic`, `jfrog:access:security_audit`, `jfrog:router:request`, `jfrog:distribution:request`, `jfrog:distribution:access`, `jfrog:xray:request`, `jfrog:xray:service`, and `jfrog:xray:webhook`.
- Default index: `main` until an environment-specific software-supply-chain/security index is selected.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20070` with source tag `JFROG_PLATFORM`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `main` / sourcetype(s) `jfrog:artifactory:request`, `jfrog:artifactory:access`, `jfrog:artifactory:traffic`, `jfrog:access:security_audit`, `jfrog:router:request`, `jfrog:xray:request`, `jfrog:xray:service`, `jfrog:xray:webhook`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Fixture semantics

- File: `test-events/jfrog_platform_test_events.txt`.
- Format: mixed custom application records, one event per line.
- Wire/envelope: headerless fixture payloads; `scripts/send_tcp_20070.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; no multiline fixtures in this pack. Public evidence notes that some Artifactory access/service logs can be multiline, so local collector configuration must be checked before promotion.
- Timestamp: request/access/security-audit, Distribution request/access, and Xray request/service fixture timestamps are UTC ISO-8601 with `Z`; traffic uses the public numeric `yyyyMMddHHmmss` shape; router JSON uses `time`; Xray webhook JSON uses `created`.
- Markers: `SC4S_JFROG_PLATFORM_TEST_*` values each occur exactly once, including the Distribution request/access markers added for the parser-shaped request/access rows.
- Sanitisation: examples use `EXAMPLE\\` users, documentation IP ranges, synthetic trace IDs/tokens/alert IDs, and example repository paths; no tenant/customer data is present.

Validation SPL smoke pattern:

```spl
index=main "SC4S_JFROG_PLATFORM_TEST_" earliest=-2h
| table _time index sourcetype source vendor product jfrog_component jfrog_log_family trace_id user src_ip action vendor_raw_action traffic_direction transfer_bytes event_type event entity_name repo_path url http_method http_status status xray_service severity alert_id top_severity watch_name policy_name policy_rule marker _raw
```

## Disposable E2E harness

`packs/jfrog_platform/scripts/e2e_docker_compose.sh` provides an idempotent Docker/Compose harness requirements for a permitted Splunk TEST + SC4S TEST lab. Use `plan` to inspect the required stages without Docker, or `run` to recreate the disposable stack, replay all ten fixture records through TCP `20070`, and query Splunk for indexed read-back in `index=main`.

Expected evidence stages are Splunk TEST readiness with HEC and `main`, SC4S listener readiness for source ID `JFROG_PLATFORM`, fixture replay, SC4S/syslog-ng listener/parser/destination movement, HEC delivery, indexed Splunk read-back, and coverage review across the declared Artifactory, Access, router, Distribution, and Xray families.

This harness is a runnable lab runbook only. Passing it would prove fixture-route SC4S TEST -> Splunk TEST read-back for the synthetic-equivalent one-line relay shapes; it would not prove live JFrog source-version emission, JFrog Cloud Log Collection, SaaS/on-prem export differences, collector credential custody, API pagination/checkpoints, archive decompression, Kubernetes sidecar/file-tail behavior, multiline access/service logs, Distribution lifecycle/business-event schemas, Pipelines structured events, production readiness, or field validation.

## Reduction stance

No event drops or field deletions are enabled by default. `docs/jfrog_platform_reduction_candidates.csv` lists advisory candidates only. Retain authentication, token, user/group, permission/admin, artifact publish/deploy/download/delete, repository path, trace ID, source IP, status, user-agent, and router/service context by default. High-volume successful downloads, health checks, and debug/service chatter are optional review candidates only after local sampling and read-back prove that investigation context is preserved.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-08.md` shows port `20070` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from public parser/sample evidence, not real JFrog deployment records.
- Artifactory access/service logs may be multiline in some deployments; this pack's fixtures cover one-line access/security/request/traffic/router/Xray shapes only.
- Xray coverage is narrow: request records are scoped to generic request-log rows whose URL begins `/xray/`; service-log rows are operational context; webhook JSON covers policy/violation alert shape from public payload-format docs, not live webhook delivery.
- JFrog Cloud Log Collection currently documents Artifactory/Audit support only; do not assume cloud-exported Xray logs without local proof.
- Distribution request/access logs are implemented only for JFrog-maintained parser-shaped request/access records. Distribution release-bundle status/activity and Pipelines build provenance remain blocked for structured parsing until exact sample/schema evidence is captured.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real JFrog relay replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, component/family routing, raw vendor action fields, actor/source IP, artifact/entity context, eventtypes/tags, and normalized fields.

## Splunk dashboard

`splunk/default/data/ui/views/jfrog_platform_soc.xml` — SOC overview dashboard covering ingestion health, Artifactory request/access events, Access security-audit admin and token activity, router request errors, traffic byte summaries by direction/path, artifact upload/download activity by user/IP, narrow Distribution request/access triage, narrow Xray request/service/webhook triage fields, and drilldown SPL. All sourcetypes require a dedicated listener on port 20070 with JFROG_PLATFORM source tag. Not field-validated; panels use synthetic-equivalent fixture evidence only.
