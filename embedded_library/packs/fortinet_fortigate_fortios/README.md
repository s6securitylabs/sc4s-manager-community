# Fortinet FortiGate/FortiOS SecHub Resources SC4S pack

This pack curates the generated upstream SC4S `fortigate_fortios` catalogue source into a conservative Fortinet FortiGate/FortiOS onboarding bundle.

## Scope and evidence

- **Vendor/product:** Fortinet / FortiGate running FortiOS.
- **Upstream SC4S evidence:** `catalogue/generated/upstream/sc4s-inbuilt.json` contains Fortinet FortiOS documentation (`docs/sources/vendor/Fortinet/fortios.md`) and parser inventory (`package/etc/conf.d/conflib/syslog/app-syslog-fortigate_fortios.conf`). `sc4s-inbuilt-lite.json` also contains the Lite addon parser.
- **Official example-event source:** Fortinet FortiOS 7.4.0 Log Message Fields documents example key=value records, including a traffic event beginning `date=2017-11-15 time=11:44:16 logid="0000000013" type="traffic" subtype="forward" ... srcip=10.1.100.155 ... dstip=35.197.51.42 ... action="close"`: <https://docs.fortinet.com/document/fortigate/7.4.0/fortios-log-message-reference/357866/log-message-fields>.
- **Current quality:** `curated`, `unverified`. The parser and fixtures are grounded in upstream SC4S inventory plus official Fortinet example-event shape, but no live FortiGate replay and Splunk read-back evidence is stored yet.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tls` listener on port `20032` with source tag `FORTINET_FORTIGATE_FORTIOS`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netfw` and sourcetype(s) `fortinet:fortigate`.

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Transport and listener

Recommended production transport is TLS syslog on the dedicated pack listener:

```bash
SC4S_LISTEN_FORTINET_FORTIGATE_FORTIOS_TLS_PORT=20032
SOURCE_ALL_SET=DEFAULT,FORTINET_FORTIGATE_FORTIOS
```

TCP or UDP syslog may be used for lab/legacy sources, but UDP can lose events and should not be considered production validation.

## Event families and sourcetypes

All curated fixtures route to `fortinet:fortigate`. The pack declares three evidence-backed families from common FortiGate key=value fields:

| Family | Sourcetype | Match basis |
| --- | --- | --- |
| `traffic` | `fortinet:fortigate` | `type="traffic"` or `type=traffic` with source/destination fields |
| `utm` | `fortinet:fortigate` | `type="utm"` or threat fields such as `virus`/`threat` |
| `vpn` | `fortinet:fortigate` | `subtype="vpn"` or VPN tunnel fields |

The parser uses a dedicated listener/source tag and a conservative Fortinet key=value signature. It avoids broad vendor-only matching without `date`, `time`, `logid`, and `type` markers.

## Fixture semantics

`test-events/fortinet_fortigate_fortios_test_events.txt` contains three synthetic-equivalent, headerless key=value payloads using RFC5737 documentation IP ranges and example identities:

1. Traffic/forward accept event.
2. UTM virus/threat blocked event.
3. VPN tunnel-up event.

Each physical line is one event. The fixture file has no syslog envelope; `scripts/send_tls_20032.sh` wraps each payload in an RFC5424 message and RFC5425 octet-count frame for the dedicated TLS listener. Fixture payload timestamps include `date`, `time`, `eventtime`, and `tz="+0000"`; deployments should confirm source timezone handling before relying on payload time over the syslog envelope timestamp.

## Splunk knowledge

The pack ships search-time props, eventtypes, and tags for JSON events emitted by SC4S:

- `vendor`, `product`, and `vendor_product` defaults.
- Network Traffic CIM-oriented fields: `src`, `src_port`, `dest`, `dest_port`, `transport`, `action`, `signature`, `signature_id`, `user`.
- Interface/device context fields: `src_interface` from `srcintf`, `dest_interface` from `dstintf`, `dvc` from `devname`, and `serial` from `devid`, preserving fixture-backed FortiGate appliance and ingress/egress identity for audit/read-back.
- Eventtypes for FortiGate traffic, UTM, and VPN records.

The mapping is intentionally partial. It does not state full Fortinet TA parity or complete CIM coverage for every FortiOS log type.

## Dashboard scope

`fortinet_fortigate_fortios_overview.xml` provides a fixture-backed onboarding and first-triage view for the three currently covered FortiGate/FortiOS source shapes: traffic/forward rows, UTM/threat rows, and VPN tunnel rows. It includes arrival volume, family distribution, blocked/threat/VPN counters, top source/destination pairs, traffic session context, UTM/threat review, VPN tunnel review, device/policy/service coverage, source/sourcetype/host coverage, and raw event context.

Dashboard panels use only fields present in the synthetic-equivalent fixtures and Splunk props/search-time extraction, including `type`, `subtype`, `level`, `action`, `status`, `src`/`srcip`, `dest`/`dstip`, `dest_port`/`dstport`, `transport`/`proto`, `service`, `policyid`, `sessionid`, `threat`, `virus`, `tunnelid`, `tunneltype`, `dvc`, `serial`, `signature`, `signature_id`, `marker`, and raw FortiGate key=value context. The dashboard does not prove complete FortiOS log-family coverage, Fortinet TA parity, firmware-specific field completeness, collector health, exact timezone validation, or SC4S/Splunk replay/read-back validation.

## Pack-aware replay/read-back harness

This pack now carries an explicit `validation_harness` requirements for the intended SC4S TEST -> Splunk TEST path. The required route is the dedicated TLS/RFC5425 listener on port `20032`, using `scripts/send_tls_20032.sh` to wrap the three headerless key=value fixtures, with read-back from `index=netfw` for the `SC4S_FORTINET_FORTIGATE_TEST_` marker prefix.

Current status remains **blocked**, not validated. A 2026-06-07 local preflight found no TCP listener on `127.0.0.1:20032`; command-level evidence is stored in `validation/preflight-2026-06-07.md`. A 2026-06-27 dedicated-lab attempt started Splunk TEST and SC4S TEST but fixture replay failed with `write:errno=104`; follow-up listener inspection showed only the SC4S health endpoint listening and no syslog-ng listener bound on TCP/20032. Evidence is stored in `validation/e2e-lab-2026-06-27.md`. This blocked harness state is operator/agent requirements evidence only and must not be treated as validation evidence or used to raise trust/quality.

## Disposable E2E harness

An idempotent Docker/Compose harness is included at `scripts/e2e_docker_compose.sh` for a future lab run. Use `packs/fortinet_fortigate_fortios/scripts/e2e_docker_compose.sh plan` to review the planned Splunk TEST + SC4S TEST stages without Docker, or `run` to create the disposable stack, replay all 3 fixtures through TLS/RFC5425 on port 20032, sample SC4S counters, and query Splunk for the expected FortiGate/FortiOS fields.

A passing run would be fixture-scope SC4S TEST -> Splunk TEST evidence only. It would not prove a real FortiGate/FortiOS appliance, firmware-version field completeness, FortiAnalyzer relay behavior, collector wrapping, API/export source shapes, or the full FortiOS log taxonomy. Do not promote quality or trust labels until replay/read-back evidence is captured, stored, and reviewed.

## Validation SPL

After installing/exporting the pack and sending marked fixtures:

```spl
index=netfw "SC4S_FORTINET_FORTIGATE_TEST_" earliest=-2h
| table _time index sourcetype source vendor product type subtype action src src_port dest dest_port src_interface dest_interface transport signature signature_id user dvc serial _raw
```

Expected read-back for the shipped fixtures:

- 3 events in `index=netfw`.
- Sourcetype `fortinet:fortigate`.
- `vendor="Fortinet"`, `product="fortigate-fortios"`.
- No event drops in basic/standard presets.

## Known limitations

- This pack has not yet been validated against a live FortiGate/FortiOS device and Splunk read-back, so it remains `curated`/`unverified`.
- FortiOS has many log families and firmware-dependent fields. The current fixtures cover representative traffic, UTM, and VPN shapes only.
- The parser intentionally performs conservative key=value parsing and metadata routing rather than attempting Fortinet TA-equivalent deep extraction in SC4S.
- Timezone handling needs live-source confirmation across configured FortiGate timezone and syslog transport settings.
- No default reduction/drop rules are included.
