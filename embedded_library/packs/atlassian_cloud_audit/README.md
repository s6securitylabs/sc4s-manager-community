# Atlassian Cloud Audit

Curated SecHub Resources pack for Atlassian Cloud audit records relayed as one JSON object per line. The initial scope is conservative and source-shape limited:

- Jira Cloud audit API records from `/rest/api/3/auditing/record`.
- Confluence Cloud audit records from `/wiki/rest/api/audit` / `/wiki/rest/api/audit/since`.
- Atlassian Admin organization Events API records from `/admin/v1/orgs/{orgId}/events` or `/events-stream`.

This pack is **curated / unverified**. It has schema/fixture/source-shape coverage only. It has not been replayed through a live Atlassian API collector, SC4S route, HEC path, or Splunk TEST indexed read-back.

## Source delivery and collection boundary

Atlassian Cloud audit data is an API/collector relay source, not native appliance syslog. A collector or Manager-owned workflow must:

1. Hold Atlassian credentials and OAuth/API scopes such as organization Events API `read:events:admin` where applicable.
2. Poll or receive Jira, Confluence, or organization audit pages/streams.
3. Track pagination, rate limits, cursors, retries, and checkpoint state.
4. Split API result arrays/pages into one audit event per record.
5. Relay each event as one JSON object per line to the SC4S listener.
6. Add or preserve source-mode context such as `source_product` so Jira, Confluence, and organization records are reviewable separately.

SecHub Resources does not poll Atlassian APIs and does not manage tenant credentials.

## Evidence and provenance

Primary source-shape evidence is recorded in `docs/evidence/atlassian-cloud-audit-evidence-scan-20260621.md`:

- Atlassian official Jira Cloud REST v3 OpenAPI exposes audit record fields such as `associatedItems`, `authorAccountId`, `authorKey`, `category`, `changedValues`, `created`, `description`, `eventSource`, `id`, `objectItem`, `remoteAddress`, and `summary`.
- Atlassian official Confluence Cloud OpenAPI exposes audit fields such as `author`, `remoteAddress`, `creationDate`, `summary`, `description`, `category`, `sysAdmin`, `superAdmin`, `affectedObject`, `changedValues`, and `associatedObjects`.
- Atlassian Admin organization Events API exposes JSON:API-style pages and event models with `id`, `type`, `attributes`, `links`, `message`, actor, location, and object context.

Fixtures are synthetic-equivalent records shaped to those public schemas. They do not contain tenant data, tokens, real account IDs, or production hostnames.

## Event families and sourcetype

All initial records route to `atlassian:cloud:audit:json` in index `gitops`.

| Family | Source mode | Fixture marker | Key fields |
| --- | --- | --- | --- |
| `jira_cloud_audit` | Jira Cloud audit API JSON | `SC4S_ATLASSIAN_CLOUD_AUDIT_TEST_JIRA_001` | `created`, `summary`, `category`, `authorAccountId`, `remoteAddress`, `objectItem`, `changedValues` |
| `confluence_cloud_audit` | Confluence Cloud audit API JSON | `SC4S_ATLASSIAN_CLOUD_AUDIT_TEST_CONFLUENCE_002` | `creationDate`, `summary`, `category`, `author`, `remoteAddress`, `affectedObject`, `changedValues` |
| `organization_audit_event` | Atlassian Admin organization Events API JSON | `SC4S_ATLASSIAN_CLOUD_AUDIT_TEST_ORG_003` | `id`, `type`, `attributes.action`, `attributes.time`, `attributes.actor`, `attributes.location`, `attributes.object` |

## Validation harness

Current state: blocked preflight only. The pack now includes a runnable disposable harness requirements at `scripts/e2e_docker_compose.sh` for operators with Docker/Compose access:

```bash
packs/atlassian_cloud_audit/scripts/e2e_docker_compose.sh plan
packs/atlassian_cloud_audit/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/atlassian_cloud_audit/compose.yaml`, starts disposable Splunk TEST and SC4S TEST containers, creates `index=gitops`, replays all three synthetic-equivalent Atlassian Cloud audit JSON fixtures through TCP `20100`, samples SC4S/syslog-ng stats, and runs summary/detail Splunk read-back searches.

Read-back SPL requirements:

```spl
index=gitops "SC4S_ATLASSIAN_CLOUD_AUDIT_TEST_" earliest=-2h
| table _time index sourcetype source vendor product source_product atlassian_audit_family event_id created creationDate attributes.time action summary category user src_user src_ip object object_type change from to location_country location_region location_city marker _raw
```

Expected count: `3`.

Blocked evidence: `validation/preflight-2026-06-21.md`. That preflight found no local TCP listener on `20100` and no authenticated Splunk management/search path; it is not validation evidence. The Docker/Compose harness is a lab execution requirements only until a run captures SC4S listener movement, HEC delivery, and Splunk indexed read-back evidence.

## Analyst knowledge

The Splunk knowledge is intentionally non-lossy:

- JSON KV extraction is enabled.
- `vendor`, `product`, `vendor_product`, `atlassian_audit_family`, `event_id`, `action`, `signature`, actor, source-IP, object, and change context are derived for search convenience.
- Eventtypes separate Jira, Confluence, organization events, and a narrow security-relevant grouping.
- Tags are discovery metadata only and do not state complete CIM coverage.

The included dashboard XML is an operator example for local Splunk use. The registered screenshot under `dashboards/screenshots/` is a sanitized Splunk TEST documentation example only; it is not source validation, SC4S replay/read-back evidence, HEC delivery proof, or production readiness evidence.

## Reduction posture

No drops, masking, null routing, or lossy field removal are enabled by default. `docs/atlassian_cloud_audit_reduction_candidates.csv` lists advisory review candidates only. Actor identity, source IP, changed values, target object context, and raw JSON should be retained by default because they explain audit findings and support reviewer challenge.

## Known limitations

- No live Atlassian tenant/API relay replay/read-back has been performed.
- API authentication, pagination, rate limits, entitlement differences, and checkpoint behavior are collector responsibilities and were not tested here.
- Jira is backed by an official example response shape; Confluence and organization variants are schema-backed synthetic-equivalent rows from this scan and should be tested with sanctioned tenant samples.
- Bitbucket Cloud, Trello, Opsgenie, Statuspage, Atlassian Guard/Access-specific event families, Jira application logs, and product access logs are out of scope.
- Trust remains `curated` / `unverified` until replay/read-back evidence proves event count, index, sourcetype, source, timestamps, and required normalized fields.
