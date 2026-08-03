# Juniper SRX / Junos Structured Syslog SecHub Resources Pack

Conservative pack for Juniper SRX security events emitted as RFC5424 structured syslog (`RT_FLOW`, `RT_IDP`, and `RT_UTM`).

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tcp` listener on port `20044` with source tag `JUNIPER_SRX_JUNOS`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netfw` and sourcetype(s) `juniper:junos:firewall`, `juniper:junos:idp`, `juniper:junos:utm`.

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Evidence and selection

This pack was selected from the generated upstream SC4S catalogue because Juniper SRX is a high-impact firewall/VPN/security gateway source, was present in upstream SC4S inventory, and was not yet represented in `packs/*`. Recent autonomous runs already covered SonicWall, QNAP, Cisco ASA, NetApp, Check Point, Veeam, Dell storage, Fortinet, pfSense, and PAN-OS; Juniper gives the library another common enterprise firewall family without repeating PAN-OS.

Public evidence scanned for this run:

- Upstream SC4S source documentation: `docs/sources/vendor/Juniper/junos.md` in `splunk/splunk-connect-for-syslog`, which documents Junos sourcetypes and links Juniper syslog configuration guidance.
- Upstream SC4S parser: `package/etc/conf.d/conflib/syslog/app-syslog-juniper_junos_structured.conf`, which routes RFC5424 structured Junos messages and splits `RT_FLOW`, `RT_IDP`, and `RT_UTM` into Juniper sourcetypes.
- Official Juniper documentation was reachable at `https://www.juniper.net/documentation/us/en/software/junos/network-mgmt/topics/topic-map/system-logging.html` and the upstream-linked syslog configuration example page. It was used to confirm Junos system logging/syslog configuration, not to statement complete SRX event-field coverage.
- GitHub public evidence: Elastic Beats/Filebeat Juniper SRX module sample logs at `x-pack/filebeat/module/juniper/srx/test/{flow,idp,utm}.log`, plus expected-output files. These provide concrete RFC5424 structured-data example event shapes for `RT_FLOW_SESSION_CREATE`, `RT_FLOW_SESSION_DENY`, `IDP_ATTACK_LOG_EVENT`, and `WEBFILTER_URL_BLOCKED`.

Fixtures in this repository are synthetic-equivalent and derived from those public event shapes. They use RFC5737 documentation IP ranges, `example.test` hostnames, and neutral usernames. No customer samples, private tenant data, or proprietary Splunk TA content are included.

## Quality and trust

- `quality_status`: `curated`
- `trust_level`: `unverified`
- Relationship to upstream: `extends_upstream`

Do not promote this pack to `validated` or `field_validated` until real SRX/Junos replay through SC4S and Splunk read-back evidence confirms event counts, sourcetypes, source, fields, timestamps, and no unwanted drops.

## Transport and event boundaries

The fixtures are one RFC5424 syslog event per line:

```text
<14>1 2019-11-14T09:37:51.184+01:00 srx-fw-a RT_FLOW - RT_FLOW_SESSION_CREATE [junos@2636 ...]
```

- Event boundary: one physical line.
- Envelope: RFC5424 with structured data.
- Payload format: Junos structured-data key/value parameters.
- Timestamp policy: RFC5424 timestamps include timezone/offset in the fixture; production devices should preserve timezone-qualified timestamps or document receiver-time fallback.
- Recommended transport: TCP syslog on a dedicated onboarding listener for lab/onboarding; TLS/RFC5425 is preferred when available. UDP/514 remains legacy/lab-compatible only.

## Artifacts

- `sc4s/app_parsers/syslog/app-juniper_srx_junos.conf` routes `RT_FLOW`, `RT_IDP`, and `RT_UTM` RFC5424 events to Juniper SRX sourcetypes.
- `sc4s/env.example` provides a dedicated TCP listener example.
- `splunk/default/props.conf` extracts core RFC5424/Junos fields and common structured-data key/value pairs used by SRX flow, IDP, and UTM events.
- `splunk/default/transforms.conf` contains parser notes; no masking/drop/routing transforms are enabled.
- `splunk/default/eventtypes.conf` and `splunk/default/tags.conf` add non-lossy search tags, including Juniper/SRX product-family discovery tags for every pack eventtype.
- `splunk/default/data/ui/views/juniper_srx_junos_overview.xml` provides a fixture-backed onboarding and first-triage dashboard for flow, IDP, and UTM smoke rows.
- `test-events/juniper_srx_junos_test_events.txt` contains four synthetic-equivalent smoke fixtures.
- `scripts/send_tcp_20044.sh` sends the fixture file to a line-delimited TCP syslog listener.

## Dashboard scope

The `Juniper SRX / Junos Structured Syslog Overview` dashboard is limited to the source shapes proven by this pack's fixtures and Splunk props: RT_FLOW session create/deny, RT_IDP attack, and RT_UTM web-filter blocked records. It includes arrival health, sourcetype/family coverage, blocked/denied and IDP counters, source/destination tuple review, policy/zone/category context, source/sourcetype/host onboarding coverage, and raw structured-syslog drilldown.

The dashboard does **not** add validation evidence. It does not prove complete Junos event-catalogue coverage, Splunk Add-on parity, exact appliance/version validation, collector health, API/export variants, or SC4S/Splunk replay/read-back.

## Fixture semantics

`test-events/juniper_srx_junos_test_events.txt` contains four unique events:

1. `RT_FLOW_SESSION_CREATE` with marker `SC4S_JUNIPER_SRX_TEST_FLOW_CREATE_001`.
2. `RT_FLOW_SESSION_DENY` with marker `SC4S_JUNIPER_SRX_TEST_FLOW_DENY_002`.
3. `IDP_ATTACK_LOG_EVENT` with marker `SC4S_JUNIPER_SRX_TEST_IDP_ATTACK_003`.
4. `WEBFILTER_URL_BLOCKED` with marker `SC4S_JUNIPER_SRX_TEST_UTM_WEB_004`.

These are smoke fixtures for routing and basic field extraction only. They are not a complete Junos/SRX message catalog.

## Validation harness and SPL

`pack.json` now carries a blocked `validation_harness` requirements for this pack. It is a runbook/status requirements, not validation evidence: replay is expected to use `scripts/send_tcp_20044.sh` against the dedicated line-delimited TCP syslog listener on port `20044`, produce four `SC4S_JUNIPER_SRX_TEST_*` events in `index=netfw`, and verify Splunk read-back for count, index, sourcetype, source, host, timestamp, raw preservation, and normalized Juniper fields. The latest local preflight (`validation/preflight-2026-06-22.md`) found no TCP syslog listener on `127.0.0.1:20044`; `ss` returned only the header row, TCP connect returned `Connection refused`, and local Splunk management port `8089` refused TCP connections. Local Splunk Web `8000` accepted TCP, but no authenticated search or indexed read-back was performed. No fixture replay, SC4S/syslog-ng counter check, HEC delivery, or Splunk indexed read-back was performed.

After replay into a lab SC4S/Splunk pipeline, query for the markers:

```spl
index=netfw "SC4S_JUNIPER_SRX_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product vendor_product juniper_program juniper_event action signature signature_id severity src src_ip src_port dest dest_ip dest_port transport user url policy_name source_zone destination_zone eventtype _raw
```

Expected until real validation exists:

- 4 events returned.
- `index=netfw`, `vendor=Juniper`, `product=SRX`.
- Flow events use `sourcetype=juniper:junos:firewall`, IDP events use `juniper:junos:idp`, and UTM events use `juniper:junos:utm`.
- No events are dropped by the basic/standard pack.
- Timestamp interpretation is reviewed against source timezone and Splunk props.

## Known limitations

- No live SRX/Junos replay or Splunk read-back evidence is committed yet.
- Fixture coverage is limited to common SRX flow, IDP, and web-filter structured syslog shapes.
- Official vendor docs confirm syslog/logging capability, but complete emitted field semantics still need product-version-specific review.
- Splunk field extractions are intentionally narrow and do not replace the Splunk Add-on for Juniper for full production enrichment.
- No reduction/drop rule is included or default-enabled.
