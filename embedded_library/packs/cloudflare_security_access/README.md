# Cloudflare Security and Access pack

Conservative SecHub Resources SC4S pack for Cloudflare Logpush / Zero Trust security and access records relayed one JSON record per line through a dedicated SC4S listener.

This is not Cloudflare validation. It preserves full records, routes fixture-backed high-value families, and exposes durable analyst fields while keeping trust `curated`/`unverified` until real Cloudflare relay replay/read-back evidence exists.

## Evidence searched

- Cloudflare Logs / Logpush overview and destination documentation.
- Cloudflare Logpush output options and field references for `http_requests`, `firewall_events`, `access_requests`, `gateway_dns`, `gateway_http`, and `audit_logs`.
- Elastic Cloudflare integration package public docs/source for conservative HTTP/logpull and audit field-family comparison only; no Elastic parser logic or fixtures are copied.
- Splunkbase Cloudflare App for Splunk public listing for JSON and Zero Trust sourcetype compatibility notes only; no Splunk app content is redistributed.
- Evidence note: `docs/evidence/cloudflare-security-access-evidence-scan-20260608.md`.
- Splunk Cloudflare App compatibility bridge design: `docs/splunk_cloudflare_app_bridge.md`. This is deployment guidance only; no Splunk app knowledge objects or samples are redistributed.

## Scope

- Listener: dedicated TCP syslog example on port `20081` with source tag `CLOUDFLARE_SECURITY_ACCESS`.
- Payloads: newline-delimited JSON records from Logpush/Zero Trust relays, collector pipelines, object-store pulls, or HTTP-destination receivers after they have been split into one Cloudflare record per line.
- Routed families: HTTP request logs, WAF/firewall events, Access requests, Gateway DNS, Gateway HTTP, Gateway Network, and account audit logs.
- Default index: `netwaf` because the initial pack is security/edge/WAF oriented. Local deployments may route audit or Zero Trust records to different indexes after replay/read-back.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20081` with source tag `CLOUDFLARE_SECURITY_ACCESS`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `netwaf` / sourcetype(s) `cloudflare:http:request`, `cloudflare:waf:event`, `cloudflare:access:request`, `cloudflare:gateway:dns`, and 3 more declared sourcetype(s). Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Fixture semantics

- File: `test-events/cloudflare_security_access_test_events.jsonl`.
- Format: one compact JSON object per line.
- Wire/envelope: fixture file is headerless application payload; `scripts/send_tcp_20081.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; no multiline records.
- Timestamp: fixtures use documented timestamp-style fields (`EdgeStartTimestamp`, `Datetime`, `Timestamp`, or `When`) with UTC `Z` values.
- Markers: `SC4S_CLOUDFLARE_SECURITY_ACCESS_TEST_*` values each occur exactly once.
- Values are synthetic-equivalent: example domains, documentation IP ranges, and `example.test` identities only. No Cloudflare tenant/customer data, API tokens, customer hostnames, or raw production logs are present.

Validation SPL smoke pattern:

```spl
index=netwaf "SC4S_CLOUDFLARE_SECURITY_ACCESS_TEST_" earliest=-2h
| table _time index sourcetype source vendor product cloudflare_family ray_id user src_ip src_internal_ip dest uri url http_method http_user_agent status cache_status action signature signature_id rule_id ruleset_id rule_message policy_id policy_name service_token_id session_id dest_ip dest_port src_port transport app sni query query_type resolver_decision resource_id resource_type resource_name interface event_id virtual_network_id virtual_network_name marker _raw
```

## Disposable E2E harness requirements

`packs/cloudflare_security_access/scripts/e2e_docker_compose.sh` now provides an idempotent disposable Splunk TEST + SC4S TEST harness requirements:

```bash
packs/cloudflare_security_access/scripts/e2e_docker_compose.sh plan
packs/cloudflare_security_access/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/cloudflare_security_access/compose.yaml`, starts a named Compose project, creates/searches index `netwaf`, mounts this pack's Splunk knowledge and SC4S parser artifacts read-only, replays the seven synthetic-equivalent fixture records through the dedicated `CLOUDFLARE_SECURITY_ACCESS` TCP listener on port `20081`, and runs summary/detail Splunk read-back SPL over the `SC4S_CLOUDFLARE_SECURITY_ACCESS_TEST_` markers.

This is a runnable lab requirements only. Passing it would prove the fixture-backed SC4S TEST -> Splunk TEST route for the declared Cloudflare JSON relay families; it would not prove a real Cloudflare tenant, Logpush job, Zero Trust account, selected-field configuration, object-store/API collector wrapper, or export completeness. It does not change the current `curated`/`unverified` trust posture.

## Dashboard

The pack includes `splunk/default/data/ui/views/cloudflare_security_access_overview.xml`, a fixture-backed Splunk SimpleXML overview for onboarding and first triage. It follows the SaaS/cloud-security and network/WAF dashboard pattern: total event arrival, family distribution, blocked/isolated decisions, WAF/firewall activity, Access and audit counts, top users/source IPs, WAF rule triage, Access/Gateway/audit context, HTTP status/host coverage, onboarding coverage, and recent raw events.

Dashboard searches are limited to fields proven by the fixtures and Splunk JSON/props knowledge: `cloudflare_family`, `ray_id`, `user`, `src_ip`, `src_internal_ip`, `dest`, `uri`, `url`, `http_method`, `http_user_agent`, `status`, `cache_status`, `action`, `signature`, `signature_id`, `rule_id`, `rule_message`, `ruleset_id`, `policy_id`, `policy_name`, `service_token_id`, `session_id`, `dest_ip`, `dest_port`, `src_port`, `transport`, `app`, `sni`, `query`, `query_type`, `resolver_decision`, `resource_id`, `resource_type`, `resource_name`, `interface`, `event_id`, `virtual_network_id`, `virtual_network_name`, and `marker`. The dashboard does not state coverage for unmodelled Logpush datasets, DLP forensic-copy payloads, CASB findings, collector envelopes, selected-field variations, Cloudflare account/action-specific `Metadata` schemas, Bot Management-specific analytics, or replay/read-back validation.

## Reduction stance

No event drops or field deletions are enabled by default. `docs/cloudflare_security_access_reduction_candidates.csv` lists advisory candidates only. Ray/request identifiers, source IP, host/path/URL, method, user/device identity, policy/rule identifiers, action/decision, audit actor/resource, and raw metadata are retained by default because they are central to WAF/edge investigation, Zero Trust access review, DNS/HTTP policy triage, audit challenge, and incident reconstruction.

## Source-shape hardening note

Gateway Network fixture coverage was added from Cloudflare's generated Logpush dataset documentation for `gateway_network`, which lists `SessionID`, source/destination IP and port, `TransportProtocol`, `DetectedProtocol`, `SNI`, `Email`, device, virtual-network, policy, and action fields. The synthetic fixture is conservative and proves only the one-line JSON relay required-field coverage; it does not validate a live Cloudflare Zero Trust Gateway network export or collector envelope.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-08.md` shows port `20081` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from official Cloudflare field references; they are not real tenant records.
- Elastic parser evidence covers Cloudflare `logpull`/HTTP-style logs and audit data streams, but does not prove every Zero Trust Access/Gateway family in this pack.
- The Cloudflare App for Splunk public listing expects `cloudflare:json` for general Cloudflare JSON and Zero Trust sourcetypes such as `cloudflare:access`, `cloudflare:audit`, `cloudflare:dns`, and `cloudflare:http`; this pack intentionally uses more explicit family sourcetypes, so app compatibility may require local non-lossy aliasing/search-time bridging after local review. See `docs/splunk_cloudflare_app_bridge.md` for a conservative design; it is not validation evidence.
- GitHub/community parser searches did not find a high-confidence reusable Logstash/Vector/Fluent Bit/Cribl parser source in this run, so collector-wrapper compatibility remains unproven.
- Account audit `Metadata` is action-specific and remains raw/conservative; this pack does not state a complete Cloudflare administration taxonomy.
- Collector wrappers may nest records, rename selected fields, or batch Logpush rows; compare local delivery output before promotion.
- Optional reduction must be tested against production-like Cloudflare data before enablement.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real Cloudflare relay replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, Cloudflare family routing, Ray/request identifiers, user/device/source context, WAF/action semantics, Gateway policy/network decisions, audit actor/resource fields, and normalized fields.
