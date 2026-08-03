# Okta System Log pack

Conservative SecHub Resources SC4S pack for Okta System Log JSON records arriving from an Okta API/Event Hook/streaming pipeline, Cribl, HEC-style relay, or another collector that forwards one JSON event per line to a dedicated SC4S listener.

This pack is an identity-control-plane intake pack, not a statement of full Okta SIEM validation. It preserves the full JSON event, routes fixture-backed high-value families, and exposes durable analyst fields while keeping trust `curated`/`unverified` until real replay/read-back evidence exists.

## Evidence searched

- Okta Developer: System Log query reference (`https://developer.okta.com/docs/reference/system-log-query/`).
- Okta Developer: System Log API reference (`https://developer.okta.com/docs/api/openapi/okta-management/management/tags/systemlog`).
- Okta Developer: Event Types reference (`https://developer.okta.com/docs/reference/api/event-types/`), including public `user.session.*`, `system.api_token.*`, `app.oauth2.*`, `application.user_membership.*`, and `user.risk.*` event-type families.
- Public Okta System Log object conventions: `published`, `eventType`, `actor`, `client`, `outcome`, `target`, `debugContext`, `transaction`, and `uuid` style fields.

## Scope

- Listener: dedicated TCP syslog example on port `20066` with source tag `OKTA_SYSTEM_LOG`.
- Payload: newline-delimited JSON, either headerless or syslog-wrapped by the relay.
- Routed families: authentication/session, MFA, user lifecycle, policy/admin changes, API token/OAuth administration, application assignment, and user-risk signal events.
- Default index: `netauth` because this is identity-plane telemetry.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20066` with source tag `OKTA_SYSTEM_LOG`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `netauth` / sourcetype(s) `okta:system:authn`, `okta:system:mfa`, `okta:system:lifecycle`, `okta:system:policy`, and 3 more declared sourcetype(s). Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Fixture semantics

- File: `test-events/okta_system_log_test_events.txt`.
- Format: one compact JSON object per line.
- Wire/envelope: fixture file is headerless JSON payload; `scripts/send_tcp_20066.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; no multiline records.
- Timestamp: fixtures use the Okta `published` field with UTC ISO-8601 `Z`/offset-equivalent timestamps.
- Markers: `SC4S_OKTA_SYSTEM_LOG_TEST_*` values each occur exactly once; the current fixture set has nine records including `user.session.start`, `app.oauth2.token.grant`, `application.user_membership.add`, and `user.risk.detect` rows.

Validation SPL smoke pattern:

```spl
index=netauth "SC4S_OKTA_SYSTEM_LOG_TEST_" earliest=-2h
| table _time index sourcetype source vendor product event_type event_id user actor_id actor_display_name src_ip action result result_reason signature severity object object_id object_type target_user credential_type authentication_provider policy_id request_id session_id user_agent oauth_client_id grant_type scopes marker _raw
```

## Reduction stance

No event drops or field deletions are enabled by default. `docs/okta_system_log_reduction_candidates.csv` lists advisory candidates only. User-agent and geographic fields may be high-cardinality, but they are often useful for suspicious-auth triage. `debugContext.debugData` and `target` arrays are high-risk to drop because they explain request IDs, policy/factor context, affected apps/users/tokens, and other incident-reconstruction details.

## Disposable E2E harness

`packs/okta_system_log/scripts/e2e_docker_compose.sh` defines a disposable Splunk TEST + SC4S TEST harness with `plan`, `write-compose`, `up`, `replay`, `readback`, `run`, and `down` modes. It mounts this pack's SC4S parser and Splunk knowledge, creates `index=netauth`, replays all nine Okta System Log JSON fixtures through TCP `20066`, and reads back the expected `okta:system:*` sourcetypes plus identity, result, target/object, MFA/OAuth/policy/session, marker, and raw JSON fields.

Use `packs/okta_system_log/scripts/e2e_docker_compose.sh plan` for the exact one-shot command and evidence stages. Passing the harness would be SC4S TEST -> Splunk TEST replay/read-back evidence for the fixture-backed JSON relay route only. It would still not prove a live Okta tenant, API/Event Hook delivery, pagination/checkpoint custody, collector wrapping, or field validation.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-07.md` shows port `20066` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked unless the disposable E2E harness is run successfully in a permitted Docker lab.
- Fixtures are synthetic-equivalent and preserve public System Log object shape, but they are not real Okta tenant records.
- Exact collector field wrapping and source-type naming must be compared against the local Okta/Cribl/Event Hook pipeline before promotion.
- OAuth token-grant, application-assignment, and risk-event coverage is synthetic-equivalent and grounded in public event-type/object-shape documentation only; it does not prove local authorization-server policy behavior, token contents, or collector envelopes.
- Optional reduction must be tested against production-like identity data before enablement.

## Dashboard coverage

`Splunk > Dashboards > Okta System Log - Overview` is shipped as `splunk/default/data/ui/views/okta_system_log_overview.xml`.

The dashboard is intentionally scoped to the seven fixture-backed Okta System Log JSON relay families, with session-start, OAuth token-grant, application-assignment, and user-risk branches routed in this pack: authentication/session, MFA, user lifecycle, policy/admin changes, API token administration/OAuth token grants, application assignment, and risk events. Panels use only the `okta:system:*` sourcetypes plus fields proven by the fixtures and `props.conf`/JSON search-time knowledge: `event_type`, `event_id`, `user`, `actor_display_name`, `actor_id`, `src_ip`/`src`, `action`, `result`, `result_reason`, `severity`, `signature`, `object`, `object_id`, `object_type`, `target_user`, `credential_type`, `authentication_provider`, `policy_id`, `request_id`, `session_id`, `user_agent`, `oauth_client_id`, `grant_type`, `scopes`, `object_id`, and `marker`.

The dashboard supports onboarding and first triage (volume, family distribution, denied/warning outcome counts, top actors/source IPs, MFA/authentication review, lifecycle/policy/API-token/application assignment/risk review, sourcetype/source/host coverage, and recent raw-event context). It is not replay/read-back validation and does not expand scope to direct Okta API polling, pagination/checkpoint custody, Event Hook delivery guarantees, collector-envelope variants, exhaustive event-type optional fields, authorization-server/token-content validation, or non-System-Log Okta products.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real Okta fixture or production-equivalent replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, and normalized fields.
