# HashiCorp Vault Audit

Curated SecHub Resources pack for HashiCorp Vault audit device records emitted as default JSON, one audit entry per line. The scope is conservative and fixture-backed for request, response, error response, authentication, token lifecycle, secret access, namespace/mount context, audit-device administration, policy/system-change, and policy-denied audit families.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20084` with source tag `HASHICORP_VAULT_AUDIT`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `netauth` / sourcetype(s) `hashicorp:vault:audit`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Evidence and provenance

Primary public evidence:

- HashiCorp Vault audit overview: `https://developer.hashicorp.com/vault/docs/audit`.
- HashiCorp Vault audit log entry schema: `https://developer.hashicorp.com/vault/docs/audit/schema`.
- HashiCorp Vault file, syslog, and socket audit devices: `https://developer.hashicorp.com/vault/docs/audit/file`, `https://developer.hashicorp.com/vault/docs/audit/syslog`, and `https://developer.hashicorp.com/vault/docs/audit/socket`.
- HashiCorp audit API/device options: `https://developer.hashicorp.com/vault/api-docs/system/audit`.
- HashiCorp auth/token API: `https://developer.hashicorp.com/vault/api-docs/auth/token`.
- Official docs/source schema partials under `hashicorp/web-unified-docs` and Vault audit formatter/source structures under `hashicorp/vault` corroborate JSON field names and request/response object shape.
- Parser ecosystem corroboration only: Elastic HashiCorp Vault integration, Datadog Vault logs pipeline, Google SecOps/Chronicle HashiCorp parser documentation, and HashiCorp's Splunk tutorial all handle Vault audit JSON fields such as `time`, `type`, `auth.*`, `request.id`, `request.operation`, `request.path`, `request.remote_address`, `response.*`, and `error`. No third-party parser or app code is copied into this pack.

Fixtures are synthetic-equivalent records shaped from public HashiCorp schema examples and ecosystem field expectations. They use RFC5737 documentation IP addresses, `example.test`/synthetic identities, synthetic UUIDs, HMAC-looking placeholder values, and explicit marker fields. No production Vault tokens, accessors, tenant identifiers, hostnames, or customer data are included.

## Source shape

- **Delivery model:** one Vault audit JSON object per line from a file audit device, socket audit device, syslog wrapper, Fluent Bit, Vector, Cribl, or another relay.
- **Wire/envelope:** fixture file is headerless JSONL; helper script wraps each payload in an RFC5424-style line for the dedicated TCP listener. Official docs identify syslog `tag`/`facility` options but no exact full syslog envelope sample was used.
- **Timestamp:** source `time` is ISO-8601/RFC3339 with timezone in fixtures and should be the primary event time.
- **Event boundary:** one JSON object per line. `jsonx`, custom `prefix`, raw-secret logging (`log_raw=true`), additional enterprise namespace edge cases, and endpoint-specific payload variations remain out of initial scope.
- **Namespace/mount semantics:** fixture coverage includes a request with `request.namespace.id`, `request.namespace.path`, `request.mount_type`, and `request.mount_accessor` to prove non-lossy namespace and mount grouping fields. This is schema-grounded triage context only, not live Vault Enterprise namespace validation.
- **Policy decision semantics:** fixture coverage includes a response with `auth.policy_results.allowed=false`, `request.policy_override=true`, `request.client_id`, `request.request_uri`, and `request.wrap_ttl` to prove non-lossy denied-policy and request-context fields. This is schema-grounded triage context only, not live ACL/Sentinel validation.
- **Token lifecycle semantics:** fixture coverage includes an `auth/token/create` response with `response.auth.lease_duration`, `response.auth.renewable`, `response.auth.token_type`, `response.auth.policies`, and `response.auth.orphan` to prove non-lossy token TTL/policy context. This is API/schema-grounded triage context only, not live token creation, renewal, revocation, orphaning, or lease behavior validation.
- **Audit-device administration semantics:** fixture coverage includes a `sys/audit/file` update request so operators can detect audit device enable/change attempts by path and operation. The fixture does not prove local audit-device option effects, exact syslog envelope behavior, or raw/HMAC handling beyond the conservative default JSON posture.
- **Default index/sourcetype:** `netauth` / `hashicorp:vault:audit`.

## Included event families

| Family | Evidence-backed fields | Notes |
| --- | --- | --- |
| `request` | `time`, `type=request`, `auth.display_name`, `auth.policies`, `request.id`, `request.operation`, `request.path`, `request.remote_address`, `request.remote_port` | Generic API request audit entry. |
| `response` | `time`, `type=response`, correlated `request.id`, `response.data`, `response.auth`, `error` where present | Response audit entry; successful and error responses need live validation before promotion. |
| `response_error` | `time`, `type=response`, `request.id`, `request.operation`, `request.path`, top-level `error` | Error/failure response triage grounded in the public audit schema `error` field; not a complete Vault error taxonomy. |
| `auth` | `request.path` under auth mounts, `auth.display_name`, `auth.entity_id`, `request.operation`, token/accessor HMAC placeholders | Authentication/token lifecycle context; not a complete Vault identity model. |
| `token_lifecycle` | `request.path=auth/token/create`, `response.auth.lease_duration`, `response.auth.renewable`, `response.auth.token_type`, `response.auth.policies`, `response.auth.orphan` | Token lifecycle response context grounded in public token API/schema fields; not live token lifecycle validation. |
| `secret` | `request.path` under secret/kv paths, `request.operation`, HMAC/sanitized request data | Secret access/change audit context; no raw secrets are included or expected. |
| `namespace` | `request.namespace.id`, `request.namespace.path`, `request.mount_type`, `request.mount_accessor`, `request.path` | Enterprise namespace / mount grouping context grounded in the public audit schema; not live namespace validation. |
| `audit_device` | `request.path` under `sys/audit`, `request.operation`, derived `vault_audit_device` | Audit-device administration triage grounded in the public system audit API path; not local audit-device option validation. |
| `policy` | `request.path` under sys/policies or sys/auth, `request.operation`, `auth.policies` | Policy/system-change audit context; local enterprise namespace and mount variations may differ. |
| `policy_denied` | `auth.policy_results.allowed=false`, `request.policy_override`, `request.client_id`, `request.request_uri`, `request.wrap_ttl`, top-level `error` | ACL/Sentinel-denied request triage grounded in public schema fields; not complete policy-engine validation. |

## Splunk fields and validation SPL

Expected non-lossy fields after Splunk search-time extraction include:

```spl
index=netauth "SC4S_HASHICORP_VAULT_AUDIT_TEST_" earliest=-2h
| table _time index sourcetype source vendor product vault_audit_family vault_type vault_namespace vault_namespace_id vault_mount_type vault_mount_accessor vault_audit_device vault_token_lifecycle vault_token_type vault_token_ttl vault_token_renewable vault_token_policies vault_token_orphan vault_policy_allowed vault_policy_override vault_client_id vault_request_uri vault_wrap_ttl request_id action signature signature_id src_ip src src_port user src_user status result error_detail object marker _raw
```

The validation harness in `pack.json` uses the same read-back field set. It is a requirements only; it has not passed because no local SC4S/Splunk testbed was available in this run.

An idempotent disposable Docker/Compose harness is included at `scripts/e2e_docker_compose.sh` for a future lab run. Use `packs/hashicorp_vault_audit/scripts/e2e_docker_compose.sh plan` to review the planned Splunk TEST + SC4S TEST stages without Docker, or `run` to create the stack, pre-create `index=netauth`, replay all 10 fixtures through TCP/20084, sample SC4S counters, and query Splunk for the expected Vault audit fields. A passing run would be fixture-scope SC4S TEST -> Splunk TEST evidence only; it would not prove a live Vault cluster, audit-device options, syslog wrapper behavior, collector envelope completeness, or field validation.

## Dashboard scope

`splunk/default/data/ui/views/hashicorp_vault_audit_overview.xml` is a fixture-backed onboarding and first-triage dashboard for the default Vault audit JSON relay sourcetype `hashicorp:vault:audit`. It follows the identity/privileged-access audit pattern: event arrival health, audit-family distribution, auth/token activity, token lifecycle TTL/renewability context, secret and policy/system-change review, operation/status context, policy-denied and override context, top actors and source IP/port context, request/response correlation by `request_id`, onboarding coverage, and recent raw-event drilldown.

The dashboard intentionally uses only fields proven by the synthetic-equivalent fixture set and Splunk JSON/search-time knowledge: `vault_audit_family`, `vault_type`, `vault_namespace`, `vault_namespace_id`, `vault_mount_type`, `vault_mount_accessor`, `vault_audit_device`, `vault_token_lifecycle`, `vault_token_type`, `vault_token_ttl`, `vault_token_renewable`, `vault_token_policies`, `vault_token_orphan`, `request_id`, `action`, `signature`, `signature_id`, `src_ip`, `src`, `src_port`, `user`, `src_user`, `status`, `result`, `error_detail`, `object`, `marker`, and preserved JSON paths such as `request.path`, `request.operation`, `request.remote_address`, `request.remote_port`, `request.namespace.path`, `request.mount_type`, `request.mount_accessor`, `response.auth.lease_duration`, `response.auth.renewable`, `response.auth.token_type`, `response.auth.policies`, `response.auth.orphan`, `auth.policy_results.allowed`, `request.policy_override`, `request.client_id`, `request.request_uri`, `request.wrap_ttl`, `auth.display_name`, and top-level `error`. It does **not** statement coverage for `jsonx`, custom prefixes, raw-secret logging, additional enterprise namespace edge cases, exact syslog envelopes, token lifecycle side effects, local audit-device option effects, or endpoint-specific response-data schemas. Dashboard presence is usability hardening only; it is not replay/read-back validation.

## Reduction posture

No default drops, null queues, lossy redaction, or field trimming are shipped. `docs/hashicorp_vault_audit_reduction_candidates.csv` is advisory only and covers review-required candidates such as high-volume health/system reads, sensitive request/response data handling, and noisy successful token lookups. Any reduction must be enabled outside the basic/standard presets only after local replay/read-back proves event counts, request IDs, paths, operations, actor context, and rollback behavior.

## Current validation status

- Quality: `curated`.
- Trust: `unverified`.
- Local schema/fixture/pack validation: handled by repository CI.
- Live SC4S replay and Splunk indexed read-back: **not performed**.
- Blocked preflight evidence: `validation/preflight-2026-06-13.md` records that no local listener/Splunk TEST route was available in this repository run.

This pack must not be described as validated, S6 verified, field validated, or deployment-approved until replay/read-back evidence proves the intended route with real or production-equivalent Vault audit data.
