# Splunk Cloudflare App sourcetype bridge design

This note records a conservative compatibility design for deployments that also use the public Cloudflare App for Splunk. It is documentation-only: the SecHub Resources pack still emits explicit family sourcetypes and does not copy Splunk app knowledge objects, vendor samples, or proprietary content.

## Why a bridge may be needed

The SecHub Resources pack routes Cloudflare records by source family so operators can review parser behaviour and read-back evidence precisely:

| SecHub Resources sourcetype | Family | Public Cloudflare App compatibility target |
| --- | --- | --- |
| `cloudflare:http:request` | Logpush HTTP request records | `cloudflare:http` or broad `cloudflare:json` searches |
| `cloudflare:waf:event` | WAF/firewall events | broad `cloudflare:json` searches; app-specific WAF assumptions require local review |
| `cloudflare:access:request` | Zero Trust Access request records | `cloudflare:access` or broad `cloudflare:json` searches |
| `cloudflare:gateway:dns` | Zero Trust Gateway DNS records | `cloudflare:dns` or broad `cloudflare:json` searches |
| `cloudflare:gateway:http` | Zero Trust Gateway HTTP records | `cloudflare:http` or broad `cloudflare:json` searches |
| `cloudflare:audit` | Account audit logs | `cloudflare:audit` or broad `cloudflare:json` searches |

The public Splunkbase listing for the Cloudflare App identifies JSON and Zero Trust sourcetype expectations, but this repository has not imported or redistributed the app. Compatibility therefore stays as a deployment design until a local operator tests it against their installed app version.

## Safe bridge pattern

If a deployment needs app dashboards/searches to see Library-emitted records, prefer non-lossy search-time bridging rather than changing SC4S routing:

1. Keep the Library family sourcetypes as the indexed `sourcetype` values.
2. Add local search-time eventtypes or macros that include both the app sourcetypes and the SecHub Resources sourcetypes used by the deployment.
3. Do not rewrite all SecHub Resources events to a single broad `cloudflare:json` sourcetype unless local replay/read-back proves no family-specific routing, retention, or required-field evidence is lost.
4. Validate the bridge with a marked replay/read-back search that proves event count, original SecHub Resources sourcetype, app-facing search inclusion, Cloudflare family, action/decision, Ray/request ID, user/source context, and audit/resource fields.
5. Keep any app-specific field aliases or dashboard assumptions local until their licence and behaviour are reviewed.

Example local search macro shape (operator-owned, not shipped as a Library artifact):

```spl
(`cloudflare_app_base` OR sourcetype IN ("cloudflare:http:request", "cloudflare:waf:event", "cloudflare:access:request", "cloudflare:gateway:dns", "cloudflare:gateway:http", "cloudflare:audit"))
```

## Validation expectation

Before enabling a bridge in production, run a deployment-local replay/read-back check such as:

```spl
index=netwaf "SC4S_CLOUDFLARE_SECURITY_ACCESS_TEST_" earliest=-2h
| eval app_bridge_family=case(
    sourcetype="cloudflare:http:request", "cloudflare:http",
    sourcetype="cloudflare:gateway:http", "cloudflare:http",
    sourcetype="cloudflare:access:request", "cloudflare:access",
    sourcetype="cloudflare:gateway:dns", "cloudflare:dns",
    sourcetype="cloudflare:audit", "cloudflare:audit",
    sourcetype="cloudflare:waf:event", "cloudflare:json",
    true(), "unmapped")
| stats count values(sourcetype) as library_sourcetypes values(app_bridge_family) as app_bridge_families values(cloudflare_family) as cloudflare_families by marker
```

This proves the bridge sees the same marked SecHub Resources events without using app compatibility as evidence of Cloudflare source validation.

## Evidence boundaries

- This bridge note does not validate the Cloudflare App for Splunk.
- It does not prove Cloudflare relay replay/read-back.
- It does not promote `cloudflare_security_access` above `curated` / `unverified`.
- It does not authorize copying Splunk app props, transforms, dashboards, or samples into this repository.
