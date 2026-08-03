# Dell SonicWall Firewall SecHub Resources SC4S pack

This pack curates the upstream SC4S `dell_sonicwall_firewall` inventory plus the community `community_sonicwall_pr_candidate` into a conservative SonicWall firewall onboarding bundle.

## Scope and evidence

- **Vendor/product:** Dell / SonicWall firewall syslog records.
- **Upstream SC4S references:**
  - `package/etc/conf.d/conflib/syslog/app-syslog-dell_sonicwall-firewall.conf`
  - `docs/sources/vendor/Dell/sonicwall.md`
  - `package/lite/etc/addons/dell/app-syslog-dell_sonicwall-firewall.conf`
- **Community source:** `catalogue/generated/community/community-extra.json` entry `community_sonicwall_pr_candidate`.
- **Current quality:** `curated`, `unverified`. Public upstream SC4S material confirms the sourcetype and key=value parser shape, but no live SonicWall appliance replay and Splunk read-back evidence is stored yet.

The upstream SC4S parser treats SonicWall payloads as MSG-format key=value text, parses `time` as `%Y-%m-%d %H:%M:%S`, sets `vendor=dell`, `product=sonicwall-firewall`, and emits `sourcetype=dell:sonicwall`. This pack keeps that conservative behavior and adds pack metadata, fixtures, Splunk knowledge, explicit transport guidance, and evidence gaps.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tls` listener on port `20031` with source tag `DELL_SONICWALL_FIREWALL`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netfw` and sourcetype(s) `dell:sonicwall`.

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Transport and listener

Recommended production transport is TLS syslog on the dedicated pack listener:

```bash
SC4S_LISTEN_DELL_SONICWALL_FIREWALL_TLS_PORT=20031
SOURCE_ALL_SET=DEFAULT,DELL_SONICWALL_FIREWALL
```

TCP or UDP syslog may be used for lab/legacy sources, but UDP can lose events and should not be considered production validation.

## Event families and sourcetypes

| Family | Sourcetype | Match basis |
| --- | --- | --- |
| `firewall_kv` | `dell:sonicwall` | key=value message containing `time=` and a firewall identity key such as `fw=` or `sn=` |

The pack intentionally does not split into multiple family sourcetypes until product-version samples or vendor-certified examples prove stable event-type fields.

## Fixture semantics

`test-events/dell_sonicwall_firewall_test_events.txt` contains two synthetic-equivalent, headerless key=value payloads using RFC5737 documentation IP ranges and example hostnames. Each fixture has a per-event marker token that appears exactly once so pack validation and Splunk read-back can distinguish families without relying on repeated shared markers:

1. TCP connection-open style event: `SC4S_DELL_SONICWALL_FIREWALL_TEST_OPEN_001`.
2. UDP connection-denied style event: `SC4S_DELL_SONICWALL_FIREWALL_TEST_DENY_002`.

Each physical line is one event. The fixture file has no syslog envelope; `scripts/send_tls_20031.sh` wraps each payload in an RFC5424 message and RFC5425 octet-count frame for the dedicated TLS listener. Timestamp validation should use the `time` key only after a deployment confirms appliance timezone semantics; the TLS wrapper timestamp remains available as a timezone-qualified envelope time.

## Splunk knowledge

The pack ships props, eventtypes, and tags for JSON events emitted by SC4S:

- `vendor`, `product`, and `vendor_product` defaults.
- Network Traffic CIM-oriented aliases/evals for `src`, `src_port`, `dest`, `dest_port`, `transport`, `action`, `signature`, and `signature_id` where the parsed key=value payload supplies them.
- Appliance identity aliases for fixture-backed `fw AS dvc` and `sn AS serial` so read-back can prove the raw SonicWall firewall context was preserved.
- Eventtypes/tags for generic SonicWall network events.

The mapping is intentionally partial. It does not state full CIM coverage or event-family completeness for all SonicWall firmware versions or log categories.

## Dashboard scope

`splunk/default/data/ui/views/dell_sonicwall_firewall_overview.xml` provides a conservative onboarding and first-triage dashboard for the fixture-backed `dell:sonicwall` key=value source shape. It covers event arrival, opened/denied counters, top source/destination pairs, protocol/application/destination-port coverage, appliance identity (`fw`/`sn` surfaced as `dvc`/`serial`), source/host coverage, and raw fixture/read-back context.

The dashboard intentionally does not state full SonicWall firmware/event-category coverage, exact appliance timezone validation, collector health, or SC4S/Splunk replay/read-back validation. Trust and quality remain `curated`/`unverified` until real SonicWall appliance replay/read-back evidence is captured.

## Validation SPL

After installing/exporting the pack and sending marked fixtures:

```spl
index=netfw ("SC4S_DELL_SONICWALL_FIREWALL_TEST_OPEN_001" OR "SC4S_DELL_SONICWALL_FIREWALL_TEST_DENY_002") earliest=-2h
| table _time index sourcetype source host vendor product vendor_product eventtype action src src_port dest dest_port transport signature signature_id dvc serial id m msg fw sn proto app marker sport dport _raw
```

Expected read-back for the shipped fixtures:

- 2 events in `index=netfw`.
- Sourcetype `dell:sonicwall`.
- `vendor="Dell"`, `product="sonicwall-firewall"` after Splunk props/evals.
- Standard analyst knowledge can surface `dell_sonicwall_firewall` / `dell_sonicwall_firewall_network` eventtypes, but these tags remain discovery metadata rather than validation evidence.
- Raw SonicWall tokens (`id`, `m`, `msg`, `fw`, `sn`, `proto`, `sport`, `dport`, and fixture `marker`) remain tabled next to normalized aliases so reviewers can prove the required-field coverage did not hide vendor payload context.
- No event drops in basic/standard presets.

## Disposable E2E harness

`packs/dell_sonicwall_firewall/scripts/e2e_docker_compose.sh` provides an idempotent Docker/Compose lab requirements for the pack-local SC4S TEST -> Splunk TEST path:

```bash
packs/dell_sonicwall_firewall/scripts/e2e_docker_compose.sh plan
packs/dell_sonicwall_firewall/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/dell_sonicwall_firewall/compose.yaml`, starts disposable Splunk and SC4S containers, creates `index=netfw`, replays both fixture events through the dedicated TLS/RFC5425 listener on TCP `20031`, and runs summary/detail read-back SPL over the `SC4S_DELL_SONICWALL_FIREWALL_TEST_` markers. It is ready for a permitted Docker lab run, but the script itself is a harness requirements only until executed and retained with SC4S/syslog-ng counter, HEC, and Splunk indexed read-back evidence.

Passing the harness would prove only the fixture-backed SonicWall key=value source shape through SC4S TEST and Splunk TEST. It would not prove a live SonicWall appliance, firmware version, log-category mix, collector wrapper, source-local timezone handling, TCP/UDP deployment variants, production readiness, or field validation.

## Known limitations

- This pack has not yet been validated against a live SonicWall appliance and Splunk read-back, so it remains `curated`/`unverified`.
- The exact event schema can vary by SonicWall firmware, log category, and syslog configuration. This pack only asserts the upstream-confirmed key=value parser shape plus common network fields used in synthetic smoke fixtures.
- Timezone handling for the `time` payload field requires source-local timezone confirmation. Do not promote to `validated` until replay/read-back evidence proves timestamp behavior.
- No default reduction/drop rules are included.
