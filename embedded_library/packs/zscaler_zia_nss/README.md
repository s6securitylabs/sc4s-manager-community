# Zscaler Internet Access NSS pack

Conservative SecHub Resources SC4S pack for Zscaler Internet Access (ZIA) Nanolog Streaming Service (NSS) JSON feeds. This pack covers the public Elastic `zscaler_zia` integration's web and firewall sample shapes and the upstream SC4S Zscaler NSS/LSS inventory, without stating lab replay or field validation.

## Evidence searched

- Generated SecHub Resources upstream catalogue entries for `zscaler_nss_proxy`, `zscaler_nss_alerts`, `zscaler_lss_md`, `zscaler_nss_md`, and SC4S Lite Zscaler addon artifacts.
- Public GitHub search for `Zscaler NSS`, `zscaler_nss_proxy`, and `zscaler_nss_alerts`, which confirmed upstream SC4S parser paths and Elastic/Sumo/CrowdStrike community documentation references.
- Official Zscaler help routes for NSS feed output formats (`/zia/nss-feed-output-format-web-logs`, `/zia/nss-feed-output-format-firewall-logs`, `/zia/nss-feed-output-format-alert-logs`, and `/zia/about-nss-feeds`) were reachable but rendered as a JavaScript application during this cron run, so their page body was not used as fixture truth.
- Public Elastic `elastic/integrations` package `packages/zscaler_zia` provided JSON sample logs and ingest pipeline field schemas for `web` and `firewall` data streams. Fixtures here are synthetic-equivalent reductions of those public sample shapes with documentation IP ranges and example identities.

## Scope

- Listener: dedicated TCP syslog example on port 20046.
- Web family: JSON events with `sourcetype=zscalernss-web`, routed to `zscaler:zia:web` and default index `netproxy`.
- Firewall family: JSON events with `sourcetype=zscalernss-fw`, routed to `zscaler:zia:firewall` and default index `netfw`.
- The SC4S parser intentionally only routes by dedicated source tag plus strong JSON sourcetype markers. Splunk `KV_MODE=json` and field aliases expose common analyst fields.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tcp` listener on port `20046` with source tag `ZSCALER_ZIA_NSS`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netproxy` and sourcetype(s) `zscaler:zia:web`, `zscaler:zia:firewall`.

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Fixture semantics

- File: `test-events/zscaler_zia_nss_test_events.txt`
- Format: one compact JSON object per line.
- Wire/envelope: fixture file is headerless JSON payload; `scripts/send_tcp_20046.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; no multiline records.
- Timestamp: ZIA payload times are timezone ambiguous unless a feed-specific `tz`/deployment setting is applied. Web fixture includes `event.time` and `event.tz=GMT`; firewall fixture includes `event.datetime` only. Production validation must confirm actual feed timezone handling.
- Markers: `SC4S_ZSCALER_ZIA_NSS_TEST_WEB_001` and `SC4S_ZSCALER_ZIA_NSS_TEST_FIREWALL_002` each occur exactly once.

Validation SPL smoke pattern:

```spl
(index=netproxy OR index=netfw) ("SC4S_ZSCALER_ZIA_NSS_TEST_WEB_001" OR "SC4S_ZSCALER_ZIA_NSS_TEST_FIREWALL_002") earliest=-2h
| table _time index sourcetype source vendor product action user src src_ip src_port dest dest_ip dest_port transport rule app url_host severity event.recordid event.sc4s_marker _raw
```

## Disposable SC4S TEST / Splunk TEST harness

`packs/zscaler_zia_nss/scripts/e2e_docker_compose.sh` defines an idempotent Docker Compose harness for a permitted disposable testbed. Use `plan` to inspect the intended evidence path without starting Docker:

```bash
packs/zscaler_zia_nss/scripts/e2e_docker_compose.sh plan
```

The harness writes a local compose file, starts Splunk TEST plus SC4S TEST, creates `netproxy` and `netfw`, replays the two fixture events through TCP `20046`, and runs summary/detail Splunk searches for `SC4S_ZSCALER_ZIA_NSS_TEST_` markers. It is a runnable replay/read-back requirements only. Until it is actually run and evidence is retained, it is not SC4S listener proof, HEC delivery proof, Splunk indexed read-back evidence, Zscaler tenant/source-version validation, complete NSS/LSS coverage, or trust/quality promotion.

## Dashboard scope

`packs/zscaler_zia_nss/splunk/default/data/ui/views/zscaler_zia_nss_overview.xml` provides a fixture-backed Splunk SimpleXML overview for the two covered NSS JSON feeds. It includes data-arrival health, feed/index coverage, blocked/drop decision counts, web threat/severity review, firewall rule and destination context, top users and client/source IPs, onboarding coverage, and raw-event drilldown.

The dashboard intentionally uses only fields present in the synthetic-equivalent fixtures and exposed by Splunk JSON search-time extraction or explicit field aliases: `sourcetype`, `event.action`, `event.login`, `event.user`, `event.cltip`, `event.csip`, `event.cltsourceport`, `event.csport`, `event.serverip`, `event.cdip`, `event.cdport`, `event.proto`, `event.rulelabel`, `event.appname`, `event.nwapp`, `event.host`, `event.threatseverity`, `event.recordid`, and `event.sc4s_marker`, plus the normalized aliases `user`, `src`/`src_ip`, `src_port`, `dest`/`dest_ip`, `dest_port`, `transport`, `action`, `severity`, `app`, `rule`, and `url_host`.

This dashboard is an onboarding and first-triage aid. It is not SC4S/Splunk replay/read-back validation and does not prove customer NSS template completeness.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: no real ZIA NSS feed replay, SC4S runtime syntax check, or Splunk read-back evidence has been captured.
- Zscaler supports many NSS/LSS feed families beyond these two examples. Audit, DNS, tunnel, SaaS, endpoint DLP, alerts, and sandbox report streams are backlog until fixtures and routing are added deliberately.
- The public Elastic package provides schema/sample evidence, not proof that every customer NSS template emits exactly these JSON fields.
- Dashboard coverage is limited to fixture-backed web and firewall JSON fields; it does not cover ZPA, LSS audit, DNS, tunnel, sandbox, DLP, collector health, or template-specific optional fields.
- No default drops or reductions are included.
