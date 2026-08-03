# VMware vSphere / ESXi / vCenter

Curated SecHub Resources SC4S pack for VMware vSphere, ESXi, vCenter, VSAN, and NSX syslog routing. This pack promotes the upstream SC4S VMware vSphere inventory into a conservative SecHub Resources pack with explicit provenance, fixture semantics, Splunk knowledge, and validation gaps.

## Scope

- Vendor: VMware
- Product: vSphere / ESXi / vCenter
- Covered families:
  - ESXi host/program logs (`vmware:esxlog:*`)
  - vCenter service logs (`vmware:vclog:*`)
  - NSX logs (`vmware:nsxlog:*`)
  - NSX distributed firewall packet logs (`vmware:nsxlog:dfwpktlogs`)
  - RFC5424 structured-data events carrying VMware `Originator@6876` data
- Recommended transport: TLS/RFC5425 to a dedicated listener or relay.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tls` listener on port `20051` with source tag `VMWARE_VSPHERE`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `infraops` and sourcetype(s) `vmware:esxlog:hostd`, `vmware:esxlog:vmkernel`, `vmware:vclog:vpxd`, `vmware:nsxlog:dfwpktlogs`, and 1 more declared sourcetype(s).

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. The SC4S parser marks matched VMware events as source-identified after setting the pack-specific index/source/sourcetype metadata so later generic routes should not overwrite the dedicated VMware route. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Provenance and evidence

Public evidence used:

- Upstream SC4S generated catalogue entries for `vmware_vsphere`, `vmware_esx_json`, and `vmware_esx_invalidmultiline` from SC4S `v3.43.0` (`5206370a6e9e5a2f3389b82291f68f86fc91c337`).
- Upstream SC4S source documentation `docs/sources/vendor/VMWare/vsphere.md`, including known malformed syslog caveats, sourcetype/index guidance, and parser options.
- Upstream SC4S parser source paths under `package/etc/conf.d/conflib/syslog/`, `package/etc/conf.d/conflib/netsource/`, and related postfilters for VMware vSphere routing semantics.
- Public upstream SC4S VMware tests (`splunk-connect-for-syslog/tests/test_vmware.py`) include NSX DFW `dfwpktlogs` packet examples using `INET match PASS ... TCP src/port->dest/port`; public VMware NSX Log Insight content-pack patterns also recognise `PASS`, `DROP`, and `REJECT` firewall decisions. These prove packet-log action tokens, not field-validation of this SecHub Resources pack.

The fixtures are synthetic-equivalent and sanitized. They preserve parser-relevant structure from upstream SC4S documentation/parser behavior but are **not** captured from a real VMware environment. Keep `quality_status=curated` and `trust_level=unverified` until real ESXi/vCenter/NSX replay and Splunk read-back evidence exists.

## Fixture semantics

`test-events/vmware_vsphere_test_events.txt` contains six one-line syslog fixtures:

1. ESXi `hostd` RFC3164 event (`SC4S_VMWARE_VSPHERE_TEST_ESX_HOSTD_001`).
2. vCenter `vpxd` RFC3164 event (`SC4S_VMWARE_VSPHERE_TEST_VCENTER_VPXD_002`).
3. ESXi `vmkernel` RFC3164 event (`SC4S_VMWARE_VSPHERE_TEST_ESX_VMKERNEL_005`).
4. NSX distributed firewall `dfwpktlogs` RFC3164 `INET match PASS ... TCP src/port->dest/port` event (`SC4S_VMWARE_VSPHERE_TEST_NSX_DFW_003`) shaped from public upstream SC4S test evidence.
5. NSX distributed firewall `dfwpktlogs` RFC3164 `INET match DROP ... TCP src/port->dest/port` event (`SC4S_VMWARE_VSPHERE_TEST_NSX_DFW_006`) using the same documented/content-pack action-token family.
6. RFC5424 event with VMware `Originator@6876` structured data (`SC4S_VMWARE_VSPHERE_TEST_SDATA_004`).

Each physical line is one event. BSD/RFC3164 fixtures depend on syslog header time plus receiver/source timezone. The RFC5424 fixture includes an explicit UTC timestamp. The send helper wraps lines over TLS/RFC5425 with octet-counting when used against an SC4S TLS listener.

## Expected sourcetypes

| Family | Expected sourcetype | Notes |
| --- | --- | --- |
| `esx_hostd` | `vmware:esxlog:hostd` | ESXi host/service logs. |
| `esx_vmkernel` | `vmware:esxlog:vmkernel` | ESXi kernel/storage/network service logs; props derive fixture-backed `severity=warning` and `signature="Storage path APD timeout"` for the storage-path warning fixture. |
| `vcenter_vpxd` | `vmware:vclog:vpxd` | vCenter service logs. |
| `nsx_dfw` | `vmware:nsxlog:dfwpktlogs` | NSX distributed firewall packet logs; default index `netfw`; public evidence uses `PASS`/`DROP`/`REJECT` action tokens rather than raw `allowed`/`blocked` fields. Splunk props extract the upstream-shaped `IN/OUT TCP src/port->dest/port` packet tuple, preserve the raw destination token as `dst`, alias it to both `dest_ip` and common `dest`, preserve the raw action in `vmware_nsx_raw_action`, preserve the raw packet direction in `vmware_nsx_raw_direction`, normalize `PASS` to `action=allowed` and `DROP`/`REJECT` to `action=blocked`, normalize the explicit packet direction token to lowercase `direction`, and surface the rule token as both `signature` and `signature_id`. Current fixtures include one PASS sample and one DROP sample to prove both non-lossy normalization branches. |
| `vsphere_sdata` | `vmware:esxlog:sdata` | Structured-data fallback for VMware `Originator@6876` events; props surface the fixture-backed `eventID` as `signature_id`/`signature` and derive `severity=warning` from the explicit structured-data fixture text until real routing evidence is captured. |

## Analyst knowledge

- `vmware_vsphere_authentication_success` tags fixture-backed ESXi/vCenter login-success events where `user`, `op=Login`, `target`, and `result=success` are extracted by Splunk KV parsing. `target` is aliased to the common `dest` field for ESXi/vCenter task/authentication-style searches. This is intentionally narrow and does not prove complete VMware authentication CIM coverage.
- `vmware_vsphere_vcenter_tasks` tags fixture-backed vCenter `TaskEvent` completion events with `change` and `success` for analyst discovery of completed vCenter tasks. This is intentionally narrow and does not prove complete VMware Change CIM coverage.
- `vmware_vsphere_vmkernel_storage_warning` tags the fixture-backed ESXi vmkernel storage-path APD warning with `storage`, `error`, `vmware`, and `virtualization` for analyst discovery. This is intentionally narrow and does not prove complete VMware storage or availability CIM coverage.
- `vmware_vsphere_structured_data` tags fixture-backed VMware `Originator@6876` RFC5424 structured-data events that expose an `eventID`; props also surface that value as `signature_id`/`signature` and derive `severity=warning` from the explicit fixture text. Narrow `vmware_vsphere_structured_data_warning` adds `error`, `vmware`, and `virtualization` tags only when the structured-data fallback has both the fixture-backed identifier and explicit warning severity. This makes the structured-data fallback route discoverable without stating product/version validation.
- `vmware_vsphere_nsx_firewall` remains the network-traffic eventtype for NSX distributed firewall packet fixtures and now carries VMware/virtualization discovery tags alongside network/communicate context. Narrow fixture-backed `vmware_vsphere_nsx_firewall_allowed` and `vmware_vsphere_nsx_firewall_blocked` eventtypes split explicit raw `PASS`/`DROP`/`REJECT` decisions after normalization to `action=allowed`/`blocked` and require an NSX `rule` value; tags add non-lossy `success` or `block` discovery facets plus VMware/virtualization product-family facets without stating complete firewall CIM coverage. NSX DFW props also preserve the explicit `rule` value as `signature_id` for stable analyst grouping; this is fixture-backed field coverage, not a validation promotion.

## Validation SPL

After importing through SC4S Manager or local SC4S validation, replay fixtures and query:

```spl
index IN (infraops, netfw) "SC4S_VMWARE_VSPHERE_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product action vmware_nsx_raw_action vmware_nsx_raw_direction direction signature signature_id severity src dest src_ip dest_ip dst src_port dest_port transport proto sport dport rule target user src_user result eventtype _raw
```

Expected count: 6 events with one marker per line and no drops. NSX DFW fixtures should include one raw `PASS`/normalized `action=allowed` event matching `eventtype=vmware_vsphere_nsx_firewall_allowed` and one raw `DROP`/normalized `action=blocked` event matching `eventtype=vmware_vsphere_nsx_firewall_blocked`; both fixture lines carry the explicit upstream-shaped `IN` packet direction token, which props preserve as `vmware_nsx_raw_direction=IN` and normalize to `direction=in`. The validation table includes both analyst aliases (`transport`, `src_port`, `dest_port`, `dest_ip`, `dest`) and raw packet tuple fields (`proto`, `sport`, `dport`, `dst`) so reviewers can prove normalization did not hide the vendor packet tokens. These remain fixture-backed analyst discovery aids, not real NSX validation evidence.

Latest dedicated lab replay attempt (2026-06-26) reached healthy Splunk TEST and SC4S TEST containers on `sc4s-validation-lab`, created `infraops` and `netfw`, and attempted to replay all six fixture rows through TLS/RFC5425 `127.0.0.1:20051`. Splunk summary/detail read-back returned no matching fixture fields, and the explicit count assertion observed `0` of `6` expected marker events. SC4S stats did not show VMware/vSphere/NSX fixture movement. This is blocked indexed-readback evidence, not validation. Command output is recorded in `validation/e2e-lab-2026-06-26.md`.

Earlier local replay preflight (2026-06-22) was blocked at the listener/testbed layer: `ss -ltn sport = :20051` returned only the header row for `127.0.0.1:20051`, `openssl s_client -connect 127.0.0.1:20051` returned `connect:errno=111` connection refused, and local Splunk management port `8089` refused TCP connections. Local Splunk Web `8000` accepted TCP, but no authenticated search or indexed read-back was performed. No VMware fixture replay, SC4S/syslog-ng counter check, HEC delivery, or Splunk indexed read-back was performed. Command-grounded blocker evidence is recorded in `validation/preflight-2026-06-22.md`.

## Disposable SC4S/Splunk TEST harness

`packs/vmware_vsphere/scripts/e2e_docker_compose.sh` now provides an idempotent Docker/Compose harness for the dedicated validation lab. Use `plan` to inspect the stages without Docker, or `run` on the disposable SC4S/Splunk lab to create `infraops` and `netfw`, replay all six fixture rows through TLS/RFC5425 port `20051`, and run summary/detail Splunk read-back SPL.

The harness is a replay/read-back requirements path only until a lab run produces retained evidence. A passing run would prove only the synthetic-equivalent fixture shapes for ESXi hostd/vmkernel, vCenter vpxd, NSX DFW, and RFC5424 structured-data events through SC4S TEST into Splunk TEST. It does not prove live ESXi, vCenter, NSX, VSAN, collector wrapper, malformed/split syslog, UDP/BSD forwarding, production TLS forwarding, or field/source-version validation.

## Known limitations

- No real VMware lab replay or Splunk read-back evidence is included yet.
- VMware vSphere syslog can be malformed: upstream SC4S documents GUID timestamps, improper RFC5424 timestamps, missing PRI/header, and split/mismatched multiline events. This pack keeps grouping/postfilter behavior out of the default path until local validation proves it is safe.
- Program-to-sourcetype coverage is intentionally conservative and fixture-backed only for `hostd`, `vmkernel`, `vpxd`, `dfwpktlogs`, and structured-data examples.
- NSX, ESXi, and vCenter can each warrant deeper pack families once real events and Splunk TA expectations are captured.

## Next validation step

Capture real ESXi/vCenter/NSX events from a lab or approved field source, replay through the dedicated listener, verify Splunk read-back fields/sourcetypes, and store sanitized evidence before promoting beyond curated/unverified quality.

## Splunk dashboard

`splunk/default/data/ui/views/vmware_vsphere_soc.xml` — SOC overview dashboard covering ingestion health, NSX DFW blocked/allowed traffic, vmkernel errors, authentication events (hostd/vpxd), vCenter task completions, structured-data events, and drilldown SPL. Not field-validated; panels use synthetic-equivalent fixture evidence only.
