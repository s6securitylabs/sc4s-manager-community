# Cisco IOS / IOS-XE Network Syslog SecHub Resources Pack

Conservative curated pack for Cisco IOS / IOS-XE-style `%IDENTIFIER-SEVERITY-MNEMONIC:` syslog messages routed as `cisco:ios`.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tcp` listener on port `20062` with source tag `CISCO_IOS_SYSLOG`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netops` and sourcetype(s) `cisco:ios`.

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Evidence and scope

This pack is based on upstream SC4S `v3.43.0` (`5206370a6e9e5a2f3389b82291f68f86fc91c337`) Cisco IOS source documentation and the generic Cisco syslog parser route. The upstream documentation names a broader Cisco Networking compatibility set, but this curated pack is intentionally scoped to IOS / IOS-XE-style `cisco:ios` fixtures only.

Out of scope until separate fixtures and replay evidence exist: IOS-XR (`cisco:xr`), NX-OS, ACI, WLC, FX-OS, and platform-specific variants that need their own source mapping or parser constraints.

## Quality and trust

- `quality_status`: `curated`
- `trust_level`: `unverified`
- Relationship to upstream: `extends_upstream`

Do not promote this pack to `validated` or `field_validated` until real Cisco IOS/IOS-XE replay through SC4S and Splunk read-back evidence confirms event counts, sourcetype, source, fields, timestamps, raw preservation, and no unwanted drops.

## Transport and event boundaries

Fixtures are one BSD/Cisco-style syslog event per line:

```text
*Mar  1 00:00:01 router-a IOS: %SYS-5-CONFIG_I: ...
```

- Event boundary: one physical line.
- Envelope: BSD/RFC3164-like Cisco syslog header, including `*` and `.` timestamp status marker examples.
- Payload format: Cisco IOS-style custom message text beginning with `%IDENTIFIER-SEVERITY-MNEMONIC:`.
- Timestamp policy: fixture timestamps omit year and timezone; configure source timezone handling for production and review Cisco time-sync marker semantics.
- Recommended transport: TCP syslog on a dedicated onboarding listener; UDP/514 is a legacy deployment consideration only.

## Artifacts

- `sc4s/app_parsers/syslog/app-cisco_ios_syslog.conf` routes dedicated-listener and Cisco-token-matched network-source messages to `index=netops`, `sourcetype=cisco:ios`, `vendor=cisco`, `product=ios`, without drops.
- `splunk/default/props.conf` extracts Cisco identifier, severity, mnemonic, message body, timestamp status marker, selected interface/login/config fields (`config_source`, `terminal`, `login_result`, `login_reason`), severity label, signature/signature_id, source aliases, and conservative action labels.
- `eventtypes.conf` and `tags.conf` add non-lossy searches for base IOS, config changes, interface/line protocol state, broad login, explicit login success/failure, and platform events.
- `test-events/cisco_ios_syslog_test_events.txt` contains six synthetic-equivalent smoke fixtures.
- `scripts/send_tcp_20062.sh` sends the fixture file to a line-delimited TCP syslog listener.

## Fixture semantics

1. `%SYS-5-CONFIG_I` config change with marker `SC4S_CISCO_IOS_TEST_CONFIG_001`.
2. `%LINK-3-UPDOWN` interface state with marker `SC4S_CISCO_IOS_TEST_LINK_002`.
3. `%LINEPROTO-5-UPDOWN` line protocol state with marker `SC4S_CISCO_IOS_TEST_LINEPROTO_003`.
4. `%SEC_LOGIN-5-LOGIN_SUCCESS` login success with marker `SC4S_CISCO_IOS_TEST_LOGIN_SUCCESS_004`.
5. `%SEC_LOGIN-4-LOGIN_FAILED` login failure with marker `SC4S_CISCO_IOS_TEST_LOGIN_FAIL_005`.
6. `%PLATFORM-6-FRU_PS_OK` platform message with marker `SC4S_CISCO_IOS_TEST_PLATFORM_006`.

These are smoke fixtures for routing and basic field extraction only. They are not a complete Cisco IOS message catalogue.

## Validation SPL

```spl
index=netops "SC4S_CISCO_IOS_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product vendor_product cisco_identifier cisco_severity severity severity_label cisco_mnemonic cisco_message signature signature_id action timesync_marker interface interface_state line_protocol_state config_source terminal user login_result login_reason src src_ip dest_port eventtype _raw
```

Expected after real lab replay/read-back:

- 6 events returned.
- `sourcetype=cisco:ios`, `index=netops`, `vendor=Cisco`, `product=IOS`.
- `cisco_identifier`, `cisco_severity`, `cisco_mnemonic`, and `cisco_message` match the raw Cisco token.
- `severity_label` maps Cisco severities 3/4/5/6 in the fixture set.
- Interface, login, and config fields (`interface`, `interface_state`, `line_protocol_state`, `config_source`, `terminal`, `user`, `login_result`, `login_reason`, `src`, `src_ip`, and `dest_port`) appear only where the source message carries them.
- `timesync_marker` preserves `*`/`.` marker examples where present.
- No events are dropped by the basic/standard presets.
- Timestamp interpretation is reviewed against source timezone and Cisco time-sync-marker configuration.

## Known limitations

- No live Cisco IOS/IOS-XE replay or Splunk read-back evidence is committed yet. The latest local preflight is captured in `validation/preflight-2026-06-07.md`; it found no dedicated TCP listener on `127.0.0.1:20062` and no local Splunk TEST management/web access on `127.0.0.1:8089`/`8000`.
- Fixture coverage is intentionally narrow; routing protocols, AAA variants, SNMP, DHCP, environmental, stack, and platform-specific messages need more fixtures before broader statements.
- IOS-XR is explicitly out of scope because upstream maps it to `cisco:xr`.
- No reduction/drop rule is included or default-enabled.

## Splunk dashboard

`splunk/default/data/ui/views/cisco_ios_soc.xml` — SOC overview dashboard covering ingestion health, configuration changes, login events (success/failure), interface state changes, high-severity alerts (0-3), and drilldown SPL. Not field-validated; panels use synthetic-equivalent fixture evidence only.

## Disposable E2E harness

`pack.json` references `scripts/e2e_docker_compose.sh` as an idempotent Docker/Compose harness for disposable SC4S TEST -> Splunk TEST replay/read-back. Use:

```bash
packs/cisco_ios_syslog/scripts/e2e_docker_compose.sh plan
packs/cisco_ios_syslog/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/cisco_ios_syslog/compose.yaml`, generates or accepts an ephemeral Splunk HEC token at run time, mounts this pack's SC4S parser and Splunk knowledge, creates and verifies index `netops`, replays all six fixture rows through TCP listener `20062`, samples SC4S/syslog-ng counters, and runs Splunk read-back SPL for `SC4S_CISCO_IOS_TEST_` markers. It fails closed when Splunk or syslog-ng is not healthy, TCP `20062` is not listening, the indexed marker count is not exactly six, or any marker event differs from index `netops`, sourcetype `cisco:ios`, or source `cisco_ios_syslog`.

A passing harness run would be route-local replay/read-back evidence for the declared synthetic-equivalent Cisco IOS / IOS-XE BSD/syslog token fixture shape only. It does not prove a real switch/router, IOS/IOS-XE release, source timezone, collector wrapper, UDP/514 deployment, other Cisco platform families, proprietary Splunk TA deployment, or field-validation scope without retained real product/source-version evidence.
