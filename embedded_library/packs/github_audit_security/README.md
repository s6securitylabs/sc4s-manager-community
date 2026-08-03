# GitHub Audit and Security Logs

Conservative SecHub Resources pack for GitHub organization/enterprise audit-log JSON records relayed as one event per line. It is intended for GitHub Audit Log API exports, audit-log streaming destinations, or collector relays that preserve the GitHub audit event JSON payload.

## Review and trust status

- Public Review status: Unreviewed
- Internal quality: `curated`
- Internal trust: `unverified`
- Validation: schema/fixture/build checks only; no live GitHub audit stream, SC4S replay, HEC delivery, or Splunk indexed read-back has been captured.

Do not treat this pack as validated or field-validated until a SOC reviewer can inspect replay/read-back evidence from a real GitHub audit feed.

## Scope

Fixture-backed families in this first pack:

| Family | Example action | Sourcetype | Notes |
| --- | --- | --- | --- |
| Repository changes | `repo.create` | `github:audit:json` | Repository lifecycle/visibility/admin actions. |
| Organization/team/outside-collaborator access | `org.add_member`, `org.add_outside_collaborator` | `github:audit:json` | Organization/team membership plus outside-collaborator invitee, inviter, permission, and repository context where present. |
| Enterprise owner/admin changes | `business.add_admin` | `github:audit:json` | Enterprise/business owner administration metadata such as `business`, `permission`, and request context; no private enterprise records. |
| SSO credential authorization | `org_credential_authorization.grant` | `github:audit:json` | SAML/OIDC SSO credential authorization metadata; token values are never represented. |
| Token/app access | `personal_access_token.request_created` | `github:audit:json` | Programmatic access/token/app events; token values are never represented. |
| GitHub Actions administration | `actions_secret.create` | `github:audit:json` | Workflow/runner/secret/variable administration metadata. |
| Audit-log streaming configuration | `audit_log_streaming.update` | `github:audit:json` | Audit-log stream endpoint state/sink metadata; no secret values. |
| Webhook administration | `hook.create` | `github:audit:json` | Webhook creation/change metadata including hook ID and subscribed event names. |
| SSH certificate authority | `ssh_certificate_authority.create` | `github:audit:json` | Organization/enterprise SSH CA metadata such as CA ID and fingerprint; no private key material. |
| Secret scanning | `secret_scanning_alert.resolve` | `github:audit:json` | Alert metadata only; no raw secrets. |
| Code/dependency security alerts | `code_scanning_alert.fixed`, `dependabot_alert.dismiss` | `github:audit:json` | Metadata-only alert lifecycle context; no SARIF/advisory payload completeness stated. |
| Branch protection/rules | `protected_branch.update_required_status_checks_enforcement_level` | `github:audit:json` | Branch protection and repository-ruleset changes. |

The pack preserves the raw JSON by default and adds only non-lossy Splunk props/eventtypes/tags.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20112` with source tag `GITHUB_AUDIT_SECURITY`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `gitops` / sourcetype(s) `github:audit:json`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Evidence and provenance

This pack is grounded in public GitHub documentation:

- REST audit-log response examples showing fields such as `@timestamp`, `action`, `actor`, `user`, `org`, `repo`, `created_at`, and `actor_location.country_code`.
- Public audit-log event taxonomy for repository, organization/team, outside-collaborator access (`org.add_outside_collaborator`), enterprise/business owner administration (`business.add_admin`), SSO credential authorization (`org_credential_authorization`), token/app, Actions, audit-log streaming (`audit_log_streaming.update`), webhook (`hook`), SSH certificate authority (`ssh_certificate_authority`), secret scanning, code scanning (`code_scanning_alert`), Dependabot (`dependabot_alert`), protected branch, and ruleset action families.
- Audit-log review/query documentation showing structured filtering over actor/action/repo/org/time/country.

See `docs/evidence/github-audit-security-evidence-scan-20260613.md` for the dated scan. Fixtures are synthetic-equivalent and use only example organizations, users, repositories, IDs, and markers.

## Transport and event boundaries

- Fixture wire shape: one compact JSON object per line, no syslog envelope in the fixture file.
- Recommended relay: dedicated TCP listener on `20112` for line-delimited JSON or syslog-wrapped JSON from a collector.
- Production deployments should prefer authenticated/encrypted collector or TLS/RFC5425 paths where available.
- Event boundary: one GitHub audit event per JSON object.
- Timestamp policy: `created_at` / `@timestamp` milliseconds since epoch in the fixtures; validate local stream timestamp semantics before promotion.

## Dashboard coverage

This pack includes `splunk/default/data/ui/views/github_audit_security_overview.xml`, a fixture-backed Splunk SimpleXML overview for onboarding and first triage. It follows the SaaS/identity/security-audit dashboard pattern from the local dashboard target-shape guidance: arrival health, family coverage, high-signal repository/branch/token/secret-scanning counters, actor and organization/repository context, administrative-action tables, onboarding coverage, and recent raw-event drilldown.

Dashboard panels are intentionally limited to fields proven by `test-events/github_audit_security_test_events.txt` and existing Splunk JSON/search-time knowledge: `github_audit_family`, `action`, `actor`, `user`, `src_user`, `org`, `business`, `repo`, `object`, `status`, `enterprise_role`, `audit_log_stream_id`, `audit_log_stream_enabled`, `audit_log_stream_sink`, `new_s3_bucket`, `old_s3_bucket`, `secrets_updated`, `hook_id`, `events`, `name`, `invitee`, `inviter`, `permission`, `public_repo`, `ssh_certificate_authority_id`, `fingerprint`, `oauth_credential_type`, `managed_token_scopes`, `user_agent`, `request_id`, `alert_number`, `alert_state`, `severity`, `security_advisory_ghsa_id`, `signature`, `signature_id`, `src`, `marker`, plus fixture-backed GitHub JSON fields such as `token_id`, `alert_number`, `secret_type`, `branch`, and `secret_name`. It does not state exhaustive GitHub audit taxonomy, Git event streaming, native SIEM/HEC/cloud envelope coverage, audit-streaming secret values, raw secret/token visibility, private key material, enterprise optional-field completeness, or replay/read-back validation.

## Validation harness

Blocked profile-aware harness:

```spl
index=gitops "SC4S_GITHUB_AUDIT_SECURITY_TEST_" earliest=-2h
| table _time index sourcetype source vendor product github_audit_family action actor user org business repo object status enterprise_role hook_id events name oauth_credential_type managed_token_scopes user_agent request_id audit_log_stream_id audit_log_stream_enabled audit_log_stream_sink new_s3_bucket old_s3_bucket secrets_updated invitee inviter permission public_repo ssh_certificate_authority_id fingerprint alert_number alert_state severity security_advisory_ghsa_id signature signature_id src marker _raw
```

Expected fixture count: 14. Required read-back fields include index, sourcetype, source, vendor/product, GitHub audit family, action, actor, org/business/repo/object context, enterprise owner/admin metadata, SSO credential metadata, audit-log streaming configuration metadata, outside-collaborator metadata, webhook metadata, SSH certificate authority metadata, alert number/state/severity where present, request/user-agent context, timestamp, marker, and raw JSON.

Local preflight evidence: `validation/preflight-2026-06-22.md`. It shows the local job host lacked the `20112` listener and Splunk TEST endpoints; this is blocker evidence only, not validation.

### Disposable E2E harness requirements

`packs/github_audit_security/scripts/e2e_docker_compose.sh` now provides an idempotent Docker/Compose harness requirements for a future SC4S TEST -> Splunk TEST run. Use `plan` to print the exact stages without requiring Docker, or `run` in a disposable lab to create Splunk/SC4S containers, pre-create index `gitops`, replay the 14 fixture events through TCP `20112`, and run summary/detail Splunk read-back SPL.

Passing that harness would be lab replay/read-back evidence only for the fixture-backed one-line GitHub audit/security JSON relay route. It would not prove a live GitHub organization/enterprise export, audit-log streaming sink, collector pagination/checkpoint ownership, Git event stream coverage, SARIF/advisory payload completeness, or field validation with real tenant telemetry.

## Reduction posture

No drops or lossy transforms are enabled. `docs/github_audit_security_reduction_candidates.csv` is advisory only. Retain actor, action, org, repo, token/app metadata, secret-scanning alert metadata, branch/ruleset context, timestamps, and raw JSON by default because these fields are needed for incident reconstruction and audit challenge.

## Known limitations

- No real GitHub audit stream was replayed through SC4S and read back from Splunk.
- Native GitHub streaming to SIEM/cloud destinations and collector wrappers may add transport/envelope metadata not represented by the fixtures.
- Per-action optional fields vary; the fixture set covers representative families, not the complete GitHub audit taxonomy, SSO credential lifecycle detail, audit-log streaming destination coverage, webhook delivery/configuration completeness, enterprise owner optional-field completeness, SARIF/code-scanning payload detail, or full Dependabot advisory schema.
- Secret scanning and token/app examples intentionally avoid raw secrets/tokens and should remain metadata-only.
