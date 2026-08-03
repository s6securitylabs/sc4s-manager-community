# QNAP NAS syslog pack

Conservative SecHub Resources SC4S pack for QNAP NAS QuLog/syslog messages. This pack promotes the `community_qnap_parser_snippet` catalogue candidate into a real, unverified pack using public event-shape evidence from the Apache-2.0 Elastic `qnap_nas` integration.

## Evidence and provenance

Public evidence reviewed during curation:

- Community catalogue candidate `community_qnap_parser_snippet` in `catalogue/generated/community/community-extra.json`.
- Elastic integrations repository, package `packages/qnap_nas` (Apache-2.0):
  - `data_stream/log/_dev/test/pipeline/test-event.log` shows QNAP `event log:` BSD/RFC3164-style examples from `qulogd`.
  - `data_stream/log/_dev/test/pipeline/test-access.log` shows QNAP `conn log:` access examples.
  - `data_stream/log/elasticsearch/ingest_pipeline/default.yml` documents parse fields for users, source IP, computer name, application, category, content, connection type, accessed resources, and action.
  - `docs/README.md` documents syslog collection over UDP/TCP/TLS.

Fixtures in this pack are synthetic-equivalent and sanitised. They preserve the public QNAP message grammar while replacing hosts, users, file paths, and IP addresses with example identities and RFC5737 documentation addresses.

## Scope

The pack covers QNAP NAS logs emitted by `qulogd` with these public shapes:

- `event log:` system/event records containing `Users`, `Source IP`, `Computer name`, `Application`, `Category`, and `Content`.
- `conn log:` access records containing `Users`, `Source IP`, `Computer name`, `Connection type`, `Accessed resources`, and `Action`.

Recommended production onboarding is a dedicated TCP syslog listener or source tag so QNAP messages do not overmatch unrelated BSD syslog. UDP is documented for compatibility but is not recommended for critical audit trails.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20094` with source tag `QNAP_NAS`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `infraops` and sourcetype(s) `qnap:nas:event`, `qnap:nas:conn`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Fixture semantics

`test-events/qnap_nas_test_events.txt` contains four one-line BSD/RFC3164-style syslog events. Each event includes a unique `SC4S_QNAP_NAS_*` marker exactly once.

- Wire format: BSD/RFC3164-style syslog with PRI, hostname, `qulogd[pid]`, and QNAP payload.
- Envelope: `bsd_rfc3164_or_headerless` for repository enum compatibility; fixtures include a BSD-style header.
- Event splitting: one event per line, `
` separator, no multiline.
- Timestamp policy: BSD timestamps contain no year or timezone; production read-back must configure source timezone or rely on receiver/source metadata.
- Field delimiting: comma-separated label/value pairs. Values can contain spaces, backslashes, quoted names, and file paths; this pack only extracts conservative top-level fields.

## Splunk usage

Search example after replay:

```spl
index=infraops "SC4S_QNAP_NAS_" earliest=-2h
| table _time index sourcetype source vendor product user src qnap_application qnap_category qnap_connection_type qnap_resource action signature _raw
```

## Disposable SC4S TEST -> Splunk TEST harness

This pack includes `scripts/e2e_docker_compose.sh`, an idempotent Docker/Compose harness requirements for a permitted disposable lab. The harness can write a temporary Compose file, start Splunk TEST and SC4S TEST containers, create `index=infraops`, replay all four QNAP NAS fixture events through the dedicated TCP `20094` listener, and run summary/detail read-back SPL for `qnap:nas:conn` and `qnap:nas:event`.

Use `packs/qnap_nas/scripts/e2e_docker_compose.sh plan` to inspect the intended stages without Docker. A successful future `run` is still scoped to synthetic-equivalent fixture replay/read-back only. It is not live QNAP appliance or QTS/QuTS source-version validation, not complete QuLog catalogue coverage, not UDP/TLS/file-tail/collector-wrapper proof, and not a trust or quality promotion unless retained evidence is captured and reviewed.

## Dashboard

This pack includes `splunk/default/data/ui/views/qnap_nas_overview.xml`, a fixture-backed onboarding and first-triage dashboard for the two covered QNAP QuLog/syslog source shapes:

- `qnap:nas:conn` connection/access rows: event volume, failed-login counter, users/source IPs, connection type, accessed resource, action, and raw context.
- `qnap:nas:event` system/event rows: application/category distribution, user/source context, message text, host/source/sourcetype coverage, and raw context.

The dashboard intentionally uses only fields present in the synthetic-equivalent fixtures and exposed by `splunk/default/props.conf`: `user`, `src`, `qnap_computer_name`, `qnap_application`, `qnap_category`, `qnap_connection_type`, `qnap_resource`, `action`, `signature`, `signature_id`, `message`, `marker`, and raw syslog context. It does not state full QuLog catalogue coverage, official QNAP source-version validation, collector health, or replay/read-back validation.

## Known limitations

- Not lab validated. Keep `quality_status=curated`, `trust_level=unverified`, and `is_verified=false` until QNAP NAS replay through SC4S and Splunk read-back evidence is captured.
- Public samples come from Elastic integration tests rather than QNAP official emitted-message documentation. They are credible parser evidence, but not field validation.
- Fixture coverage is intentionally small: representative event/access families only, not the full QuLog catalog.
- The SC4S parser is intended for a dedicated listener/source tag. Do not deploy it as a broad global body match without source identification.
- No reduction or drop rules are included.
