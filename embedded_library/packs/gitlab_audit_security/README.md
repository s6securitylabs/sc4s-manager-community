# GitLab Audit and Security Events

Curated SecHub Resources pack for GitLab Audit Events API and top-level group audit-event-streaming records relayed as one JSON object per line.

## Scope

- Source identity: GitLab audit events from the Audit Events API or audit event streaming.
- Delivery mode: collector/API or webhook receiver relay. The collector owns GitLab access tokens, webhook receipt, pagination, retries, deduplication policy, and checkpoint state.
- SC4S boundary: this pack expects one GitLab audit-event JSON object per line on a dedicated TCP syslog relay listener. It does not make SC4S a native GitLab HTTP destination.
- Default route: `index=gitops`, `sourcetype=gitlab:audit:json`, `source=gitlab_audit_security`.

Out of scope for this initial pack: GitLab application logs, web access logs, runner logs, container registry logs, Git push/event streams, direct SC4S HTTP intake, and complete coverage of GitLab's moving audit-event-type catalogue.

## Fixture-backed families

| Family | Evidence basis | Example marker | Notes |
| --- | --- | --- | --- |
| `project_admin_change` | GitLab Audit Events API examples for project administrative changes | `SC4S_GITLAB_AUDIT_SECURITY_TEST_PROJECT_001` | Project archive-style administrative change. |
| `group_admin_change` | GitLab group audit-event examples | `SC4S_GITLAB_AUDIT_SECURITY_TEST_GROUP_002` | Group add/delete style administrative change. |
| `user_account_change` | GitLab user/account audit examples | `SC4S_GITLAB_AUDIT_SECURITY_TEST_USER_003` | Email/account change context with `change`, `from`, and `to`. |
| `audit_streaming_config_change` | GitLab audit-event-streaming and audit-event-type docs | `SC4S_GITLAB_AUDIT_SECURITY_TEST_STREAM_004` | Audit streaming header/destination configuration change. |

Fixtures are synthetic-equivalent records shaped from public GitLab documentation. They use documentation IP ranges, `example.test` identities, synthetic IDs, and explicit markers. They are not tenant data and are not replay/read-back validation.

## Collection and pipeline notes

- API polling or audit-event streaming should be terminated by a collector/webhook receiver before SC4S.
- The collector should relay exactly one audit-event JSON object per line. Native API response arrays or HTTP POST envelopes must be split/unwrapped before this pack sees them.
- GitLab documentation states a streamed audit event can be sent more than once. Use the `id` / `event_id` field for deduplication in the collector or searches; do not drop records in the parser by default.
- Preserve the nested `details` object. GitLab audit fields can appear both as flattened top-level fields and nested `details` keys depending on scope/version.
- No default lossy reduction, masking, or field dropping is enabled.

## Validation harness

Current status: **blocked**. Local preflight evidence is in `validation/preflight-2026-06-20.md` and shows the missing SC4S TEST listener / Splunk TEST search path in this repository run. This is useful blocker evidence only; it is not validation.

A disposable Docker/Compose harness is available at `scripts/e2e_docker_compose.sh` for permitted lab environments. It can write an isolated Splunk TEST + SC4S TEST Compose stack, create `index=gitops`, replay all 4 synthetic-equivalent GitLab audit fixtures through TCP `20099`, and run summary/detail read-back SPL. Use `scripts/e2e_docker_compose.sh plan` to inspect the exact stages without requiring Docker. Passing that harness would be fixture-route lab evidence only; it would not prove live GitLab tenant/API delivery, token custody, pagination, webhook/audit-stream receiver behavior, collector envelope unwrapping, or field validation.

Expected replay/read-back SPL:

```spl
index=gitops "SC4S_GITLAB_AUDIT_SECURITY_TEST_" earliest=-2h
| table _time index sourcetype source vendor product gitlab_audit_family id event_id event_type created_at author_id author_name author_email src_user entity_id entity_type entity_path target_id target_type target_details object ip_address src_ip action change from to custom_message signature signature_id marker _raw
```

A future validation pass must prove event count `4`, route/index/sourcetype/source, timestamp parsing, raw JSON retention, actor/source IP context, target/object context, and fixture marker uniqueness through SC4S TEST -> HEC/Splunk TEST indexed read-back.

## Reduction posture

See `docs/gitlab_audit_security_reduction_candidates.csv`. All candidate reductions are advisory only and disabled by default. Actor identity, source IP, target details, entity path, and nested `details` are often required to reconstruct administrative changes and must be retained unless local replay/read-back and approval prove a specific reduction is safe.

## Provenance

- Official GitLab Audit Events API docs: `https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/api/audit_events.md`.
- Official GitLab audit event streaming docs: `https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/user/compliance/audit_event_streaming.md`.
- Official generated audit event type catalogue: `https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/user/compliance/audit_event_types.md`.
- SecHub evidence scan: `docs/evidence/gitlab-audit-security-evidence-scan-20260620.md`.

## Limitations

- No live GitLab tenant/API relay, audit-stream receiver, SC4S replay, HEC delivery, or Splunk read-back evidence has been captured.
- Fixture coverage is intentionally narrow and does not state exhaustive GitLab audit-event-type coverage.
- HTTP streaming delivery requires a collector/webhook receiver; direct GitLab-to-SC4S HTTP delivery is not implemented or validated by this pack.
- Trust remains `curated` / `unverified` until replay/read-back or production-equivalent evidence exists.
