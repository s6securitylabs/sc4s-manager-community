# Google Cloud / Workspace Audit

Conservative SecHub Resources pack for Google Cloud Audit Logs (`LogEntry` JSON carrying `protoPayload` / `google.cloud.audit.AuditLog`) and Google Workspace Admin Reports API `Activity` JSON relayed as one JSON object per line.

This is an API/export/collector relay pack, not proof that SC4S can collect Google APIs directly. It preserves raw JSON, routes fixture-backed audit families to `google:audit:json`, and exposes durable analyst fields while keeping trust `curated`/`unverified` until real Google relay replay/read-back evidence exists.

## Scope

Fixture-backed source-shape variants:

- Google Cloud Admin Activity audit log entries (`cloudaudit.googleapis.com/activity`).
- Google Cloud Data Access audit log entries (`cloudaudit.googleapis.com/data_access`), including narrow fixture-backed `authorizationInfo.permission` allow/deny context.
- Google Cloud System Event audit log entries (`cloudaudit.googleapis.com/system_event`).
- Google Cloud Policy Denied audit log entries (`cloudaudit.googleapis.com/policy`) for denied IAM/access-policy decisions.
- Google Workspace Admin SDK Reports API login activities.
- Google Workspace Admin SDK Reports API admin/user-setting activities.
- Google Workspace Admin SDK Reports API Drive access activities.
- Google Workspace Admin SDK Reports API OAuth token authorization activities.
- Google Workspace Admin SDK Reports API Groups membership activities.
- Google Workspace Admin SDK Reports API Calendar access-control activities.
- Google Workspace Admin SDK Reports API SAML login activities, including narrow failed-login context.

Out of initial scope: Security Command Center findings, VPC Flow Logs, Cloud DNS/Load Balancer logs, BigQuery export rows, Workspace app-specific exhaustive schemas beyond the fixture-backed login/admin/Drive/token/groups/calendar/SAML branches, Pub/Sub envelope metadata, vendor SIEM connector custody, and direct API polling. Add those as separate variants only after exact source-shape evidence or local capture exists.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20111` with source tag `GOOGLE_CLOUD_WORKSPACE_AUDIT`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `main` / sourcetype(s) `google:audit:json`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Evidence and provenance

Public evidence used for this pack is summarized in `docs/evidence/google-cloud-workspace-audit-evidence-scan-20260613.md`.

Representative source URLs:

- Google Cloud Audit Logs overview: <https://cloud.google.com/logging/docs/audit>
- Cloud Logging `LogEntry` REST schema: <https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry>
- Google Cloud `AuditLog` schema: <https://cloud.google.com/logging/docs/reference/audit/auditlog/rest/Shared.Types/AuditLog>
- Cloud Logging export sinks: <https://cloud.google.com/logging/docs/export/configure_export_v2>
- Google Workspace Reports API Activity schema: <https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities>
- Elastic Google Cloud and Google Workspace integrations for ecosystem field-family corroboration.
- Splunk Add-on for Google Cloud Platform listing for sourcetype/collection context only; no proprietary Splunk app content was copied.

Fixtures are synthetic-equivalent records shaped from public schemas and examples using `example.test`, `example-project`, documentation IP ranges, and synthetic IDs. They contain no customer tenant identifiers, access tokens, project secrets, or production audit records.

## Transport, envelope, and event boundaries

- Recommended listener: dedicated TCP line-delimited JSON on port `20111`.
- Fixture file: `test-events/google_cloud_workspace_audit_test_events.txt`.
- Event boundary: one JSON object per line.
- Timestamp policy: Google Cloud records use top-level `timestamp`; Workspace records use `id.time`; both are timezone-qualified UTC in fixtures.
- Default index: `main` until a deployment-specific cloud/SaaS index is chosen.
- Default sourcetype: `google:audit:json`.

## Splunk required-field coverage notes

`props.conf` keeps `KV_MODE=json` / `AUTO_KV_JSON=true` and derives the following analyst fields where present:

- `google_audit_family`
- `cloud_project`
- `gcp_service`
- `method`
- `user` / `src_user`
- `src_ip` / `src`
- `action`
- `signature` / `signature_id`
- `resource_name`
- `status`
- `gcp_permission` / `gcp_permission_granted` for fixture-backed GCP `authorizationInfo` access decisions
- `app`
- `marker`
- `workspace_oauth_app` / `workspace_oauth_client_id` / `workspace_oauth_client_type` for fixture-backed OAuth token activity
- `workspace_group_email` / `workspace_member_email` / `workspace_member_role` for fixture-backed Groups membership activity
- `workspace_calendar_id` / `workspace_calendar_access_level` / `workspace_calendar_grantee_email` for fixture-backed Calendar ACL activity
- `workspace_saml_application` / `workspace_saml_failure_type` for fixture-backed SAML failed-login activity

Policy Denied records use the same AuditLog schema and preserve `protoPayload.status.code` / `protoPayload.status.message` so reviewers can distinguish denied access-policy decisions from successful admin/system events. The Data Access fixtures now include both granted and denied `authorizationInfo` examples so reviewers can prove permission/grant extraction without treating the pack as exhaustive IAM analysis.

The mappings are intentionally partial. Nested Google Cloud service-specific payloads and Workspace `events[].parameters` are preserved but not exhaustively normalized.

## Dashboard coverage

`Splunk > Dashboards > Google Cloud / Workspace Audit - Overview` is shipped as `splunk/default/data/ui/views/google_cloud_workspace_audit_overview.xml`.

The dashboard is intentionally scoped to the eleven fixture-backed Google Cloud / Workspace JSON relay families in this pack: GCP Admin Activity, GCP Data Access, GCP System Event, GCP Policy Denied, Workspace login, Workspace admin, Workspace Drive, Workspace OAuth token, Workspace Groups membership, and Workspace Calendar ACL activity, and Workspace SAML login activity. Panels use only the shared sourcetype `google:audit:json` plus fields proven by the fixtures and `props.conf`/JSON search-time knowledge: `google_audit_family`, `cloud_project`, `gcp_service`, `method`, `app`, `user`/`src_user`, `src_ip`, `action`, `signature`, `signature_id`, `resource_name`, `status`, `gcp_permission`, `gcp_permission_granted`, `workspace_calendar_id`, `workspace_calendar_access_level`, `workspace_calendar_grantee_email`, `workspace_saml_application`, `workspace_saml_failure_type`, `marker`, and preserved raw JSON/nested fields such as `protoPayload.*`, `protoPayload.authorizationInfo.*`, `actor.email`, `id.applicationName`, and `events{}.name` where Splunk JSON search-time extraction is expected.

The dashboard supports onboarding and first triage (volume, family distribution, admin/system/policy-denied and data-access counters, non-success/error signal review, top users/source IPs, GCP service/project coverage, Workspace application/event names, cloud resources touched, sourcetype/source/host coverage, and recent raw-event context). It is not replay/read-back validation and does not expand scope to Security Command Center findings, VPC Flow Logs, Pub/Sub envelope metadata, API credential custody, direct collection, or complete service/app-specific optional-field coverage.

## Validation status

Local validation is structural only. No replay/read-back evidence exists.

Intended read-back SPL:

```spl
index=main "SC4S_GOOGLE_CLOUD_WORKSPACE_AUDIT_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product google_audit_family cloud_project gcp_service method app user src_user src_ip action signature signature_id resource_name status gcp_permission gcp_permission_granted workspace_oauth_app workspace_oauth_client_id workspace_oauth_client_type workspace_group_email workspace_member_email workspace_member_role workspace_calendar_id workspace_calendar_access_level workspace_calendar_grantee_email workspace_saml_application workspace_saml_failure_type marker _raw
```

Expected fixture count: `12` events with one unique marker each.

Current blocker: no local listener on `127.0.0.1:20111` and no local Splunk TEST ports (`8089` / `8000`) were reachable. See `validation/preflight-2026-06-22.md`.

### Disposable E2E harness requirements

`./scripts/e2e_docker_compose.sh` defines an idempotent Docker/Compose SC4S TEST -> Splunk TEST harness for a permitted lab run:

```bash
packs/google_cloud_workspace_audit/scripts/e2e_docker_compose.sh plan
packs/google_cloud_workspace_audit/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/google_cloud_workspace_audit/compose.yaml`, starts disposable Splunk and SC4S containers, mounts this pack's Splunk knowledge and SC4S parser artifacts, replays all 12 Google Cloud / Workspace JSON fixtures through TCP `20111`, and runs summary/detail SPL over `index=main` for the `SC4S_GOOGLE_CLOUD_WORKSPACE_AUDIT_TEST_` markers. A successful lab run would prove only the synthetic-equivalent fixture replay/read-back path for this pack's declared JSON relay shape. It does not prove live Google Cloud project or Workspace tenant emission, Pub/Sub/API/export collector behavior, credential custody, pagination/checkpoints, destination envelope metadata, export completeness, field validation, or production readiness.

## Reduction posture

No drops or field deletion are enabled by default. `docs/google_cloud_workspace_audit_reduction_candidates.csv` lists advisory candidates only. Caller/resource/authentication context, Workspace `events[].parameters`, user identity, project/customer context, timestamps, service/method/action, and raw JSON are retained by default because they are central to incident reconstruction and audit challenge.
