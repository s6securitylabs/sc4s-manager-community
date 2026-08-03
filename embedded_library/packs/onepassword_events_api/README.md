# 1Password Events API

Curated SecHub Resources SC4S pack for 1Password Events API records relayed as one JSON object per line after a collector unwraps `items[]` from `/api/v2/auditevents`, `/api/v2/itemusages`, and `/api/v2/signinattempts` responses.

## Review status

- Public Review status: Unreviewed
- Internal quality: curated
- Internal trust: unverified
- No live 1Password tenant/API relay, SC4S listener replay, HEC delivery, or Splunk indexed read-back has been captured.

## Source shape and provenance

Public 1Password Events API documentation and OpenAPI 1.4.1 schema evidence describe response wrappers with `cursor`, `has_more`, and `items[]`, plus item shapes for audit events, item usage, and sign-in attempts. The repository evidence scan is `docs/evidence/onepassword-events-api-evidence-scan-20260620.md`. This pack's SC4S route expects the collector to emit each `items[]` member as one compact JSON line. SC4S does not own bearer tokens, cursor state, polling windows, retry logic, or checkpoint storage.

Fixtures are synthetic-equivalent records derived from public field/schema evidence, not copied tenant data. They use `example.test` users, documentation/synthetic IDs, and a synthetic marker field.

## Event families

| Family | Sourcetype | Evidence-backed trigger | Notes |
| --- | --- | --- | --- |
| Audit event | `1password:events` | `action=join`, `object_type=gm` | Group membership/admin audit shape. |
| Item usage | `1password:events` | `action=secure-copy`, `used_version=*` | Item/vault usage telemetry. |
| Sign-in attempt | `1password:events` | `category=firewall_failed`, `type=continent_blocked` | Authentication/firewall failure telemetry. |

## Ingestion and delivery notes

A collector/API relay is required. It should poll the Events API endpoints, manage credentials and cursors securely outside this pack, unwrap response `items[]`, preserve one event per line, and forward to the dedicated SC4S source tag/listener (`1PASSWORD_EVENTS_API`, TCP 20098 in the example). Do not enable lossy field filtering by default. Email, location, client, item, session, and failure-detail fields can be sensitive but are commonly needed for audit challenge and incident reconstruction.

## Validation harness

Current harness status: blocked. Required read-back SPL:

```spl
index=netauth "SC4S_1PASSWORD_EVENTS_API_TEST_" earliest=-2h
| table _time index sourcetype source vendor product onepassword_event_family action category type event_id user src_user target_user object object_type src_ip session_id client_app client_platform location_country reason marker _raw
```

Expected count: 3. Required verification: event count, index, sourcetype, source, vendor/product, family, action/category/type, timestamp, actor/user fields, target/object fields, session/source IP where present, client/location context, marker uniqueness, and raw JSON.

Blocked preflight evidence: `validation/preflight-2026-06-20.md`.

### Disposable Docker E2E harness

`packs/onepassword_events_api/scripts/e2e_docker_compose.sh` provides an idempotent disposable Splunk TEST + SC4S TEST harness with `plan`, `write-compose`, `up`, `replay`, `readback`, `run`, and `down` stages. The harness replays all 3 synthetic-equivalent JSON fixtures through TCP `20098` and checks `index=netauth` for the `SC4S_1PASSWORD_EVENTS_API_TEST_` markers plus the read-back fields above.

Use `packs/onepassword_events_api/scripts/e2e_docker_compose.sh plan` to print the exact one-shot command and evidence stages without requiring Docker. A successful lab run would be replay/read-back evidence only for the fixture-backed collector-unwrapped JSON relay shape; it would not prove live 1Password tenant/API delivery, bearer token custody, cursor/checkpoint handling, API `items[]` envelope unwrapping, or complete Events API action coverage.

## Reduction posture

Basic and standard templates preserve all fields. `docs/onepassword_events_api_reduction_candidates.csv` lists privacy/noise candidates only; no masking, dropping, or trimming is enabled by default. Any reduction must be locally reviewed and replay/read-back tested before use.

## Known limitations

- Only three synthetic-equivalent families are fixture-backed.
- Native API response wrappers are not the default SC4S event boundary; collectors must split `items[]`.
- Per-action audit details vary; the pack preserves unknown JSON fields rather than stating complete normalization.
- Documentation examples/OpenAPI evidence are not live tenant validation.
