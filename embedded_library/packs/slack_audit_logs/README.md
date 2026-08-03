# Slack Audit Logs

Conservative SecHub Resources pack for Slack Enterprise Audit Logs API records relayed as one JSON object per event. The pack is intended for SC4S/syslog-ng and Splunk ingestion of collector-unwrapped audit entries, not for polling Slack directly.

## Scope

- Vendor/product: Slack / Audit Logs API.
- Source mode: Slack Enterprise Audit Logs API `entries[]` responses collected by a separate API collector, unwrapped to one JSON object per line, and relayed to the dedicated SC4S listener.
- Sourcetype: `slack:audit`.
- Default index: `netauth`.
- Fixture-backed families: user session, anomaly, app security, file security, workspace administration, and user/admin role changes.

This pack does **not** statement complete Slack Audit Logs coverage, Slack message-content monitoring, DLP/eDiscovery coverage, Slack Enterprise tenant validation, SC4S replay validation, HEC delivery evidence, or Splunk indexed read-back.

## Evidence and provenance

Grounding evidence is recorded in `docs/evidence/slack-audit-logs-evidence-scan-20260619.md`:

- Slack official Audit Logs API guide/reference, methods/actions reference, and anomalous-events reference.
- Elastic Slack integration docs/package material used only for field-family comparison and corroboration, not copied parser code or sample records.

Public evidence supports conservative synthetic-equivalent fixtures for the core Slack audit event shape: `id`, `date_create`, `action`, `actor`, `entity`, `context`, and action-specific `details`. All fixture values are synthetic examples using `example.test` domains and RFC 5737 documentation IP ranges.

## Collection and delivery boundaries

Slack Audit Logs API collection is a collector responsibility. The collector must own:

- Enterprise-plan and organization-owner prerequisites.
- OAuth user token custody for `auditlogs:read` scope. Never place Slack tokens in this pack, SC4S config, fixtures, or generated artifacts.
- Cursor pagination, checkpoint/lookback, rate and limit handling, retry/deduplication, and API response envelope handling.
- Splitting native Slack API responses into one audit entry per relayed JSON record.

The SC4S route expects one JSON object per event after the collector unwraps the native `entries[]` response. Do not send an entire API response envelope as a single event unless a local collector/parser variant has been separately reviewed and validated.

## Transport and route

- Listener source ID: `SLACK_AUDIT_LOGS`.
- Example TCP listener port: `20096`.
- Recommended transport for local testing: line-delimited TCP syslog / JSON relay.
- Production deployments should prefer a TLS/RFC5425 route if the local SC4S deployment provisions TLS for this source.

The parser intentionally matches a narrow set of fixture-backed Slack audit actions plus the required JSON structures. It should not hijack generic Slack text or message-content logs.

## Fixture semantics

`test-events/slack_audit_logs_test_events.txt` contains six compact JSON lines:

| Marker | Family | Action | Notes |
| --- | --- | --- | --- |
| `SC4S_SLACK_AUDIT_LOGS_TEST_SESSION_001` | `user_session` | `user_login` | Login/session context with actor, entity, workspace, source IP, user agent, and session ID. |
| `SC4S_SLACK_AUDIT_LOGS_TEST_ANOMALY_002` | `anomaly` | `anomaly` | Anomaly details for prior IP/user-agent and reason. |
| `SC4S_SLACK_AUDIT_LOGS_TEST_APP_003` | `app_security` | `app_approved` | App approval context with scopes and app owner. |
| `SC4S_SLACK_AUDIT_LOGS_TEST_FILE_004` | `file_security` | `file_downloaded` | File metadata with synthetic private URL and MD5-style hash. |
| `SC4S_SLACK_AUDIT_LOGS_TEST_WORKSPACE_005` | `workspace_admin` | `workspace_settings_changed` | Workspace setting change details. |
| `SC4S_SLACK_AUDIT_LOGS_TEST_ROLE_006` | `user_admin_role` | `user_role_changed` | User role change details. |

Event boundary is one JSON object per line. `date_create` is the source timestamp as UTC epoch seconds. Fixture markers must appear exactly once each.

## Splunk knowledge

`props.conf` enables JSON auto-KV for `slack:audit`, parses `date_create` as epoch seconds, and derives conservative fields including:

- `vendor`, `product`, `vendor_product`.
- `slack_audit_family`, `event_id`, `action`, `signature`, `signature_id`.
- Actor/user context: `user`, `src_user`, `actor_id`, `actor_name`, `actor_email`, `actor_type`.
- Entity/object context: `target_user`, `target_user_id`, `target_user_email`, `object`, `object_type`.
- Context fields: `src_ip`, `src`, `user_agent`, `session_id`, `workspace_id`, `workspace_name`, `workspace_domain`.
- Details fields: `reason`, `previous_ip_address`, `previous_user_agent`, `file_hash`, and `file_url_private`.

Eventtypes and tags are fixture-backed discovery helpers only; they are not complete CIM certification.

## Validation harness

Current status: **blocked**. The pack includes a validation harness requirements and command-grounded preflight evidence at `validation/preflight-2026-06-19.md`, but no Slack API relay, SC4S route replay, HEC delivery, or Splunk indexed read-back was captured.

A disposable Docker/Compose harness requirements is now available at `scripts/e2e_docker_compose.sh` for permitted lab runs. Use `packs/slack_audit_logs/scripts/e2e_docker_compose.sh plan` to review the stages without Docker, or `packs/slack_audit_logs/scripts/e2e_docker_compose.sh run` to stand up disposable Splunk TEST + SC4S TEST, replay the six JSON fixtures through TCP `20096`, and query `index=netauth` for read-back. Passing that harness would be fixture-route lab evidence only; it would not prove live Slack Enterprise API collection, OAuth token custody, cursor pagination/checkpointing, API `entries[]` envelope unwrapping, collector wrapper behavior, or complete Slack Audit Logs action coverage.

Expected read-back SPL once a testbed is available:

```spl
index=netauth "SC4S_SLACK_AUDIT_LOGS_TEST_" earliest=-2h
| table _time index sourcetype source vendor product slack_audit_family action event_id user src_user actor_id actor_email target_user target_user_id object object_type src_ip user_agent session_id workspace_id workspace_domain reason previous_ip_address previous_user_agent file_hash file_url_private marker _raw
```

A validation-grade run must prove event count `6`, index `netauth`, sourcetype `slack:audit`, source, timestamps from `date_create`, vendor/product fields, family/action routing, actor/entity/context/details fields, and raw JSON preservation. Do not promote `quality_status` or `trust_level` until replay/read-back evidence exists.

## Reduction and privacy posture

No lossy filtering, dropping, masking, sampling, or redaction is enabled by default. Slack audit records may contain sensitive user emails, names, source IPs, user agents, file URLs, and workspace identifiers, but these fields are often necessary for incident reconstruction and audit challenge.

Advisory candidates are documented in `docs/slack_audit_logs_reduction_candidates.csv`. Any masking/sampling/trimming must be opt-in and must pass replay/read-back with rollback instructions before production use.

## Known limitations

- No live Slack Enterprise tenant/API capture or product-version evidence is present.
- Native API response envelopes are not fixture-backed as SC4S event boundaries; collectors must unwrap `entries[]`.
- Official action tables are broad and may evolve; this pack only routes fixture-backed initial families.
- Action-specific `details` fields are partial and conservative.
- Collector wrappers from Cribl, Elastic Agent, custom Lambda/Function, Event Hub, or object-store pipelines require local envelope comparison before stating compatibility.
- Splunk app compatibility is not asserted; the pack emits `slack:audit` with local field guidance.
