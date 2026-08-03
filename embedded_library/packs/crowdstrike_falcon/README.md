# CrowdStrike Falcon Platform JSON relay pack

## Scope

`crowdstrike_falcon` is a conservative SecHub Resources SC4S pack for the CrowdStrike Falcon Platform JSON relay family. It uses the existing pack ID for compatibility, but its display/source identity is Falcon Platform because it covers multiple Falcon platform modules. It now covers the initial Falcon Data Replicator (FDR) / Event Streams-style endpoint rows plus separate API/feed relay variants for Devices host inventory, Spotlight vulnerability records, and Intelligence indicators, plus sample-backed Falcon Event Streams audit/RTR, Identity Protection, detection summary, and firewall policy-match records. It is intended for one JSON object per line delivered through a dedicated SC4S source tag/listener; it does not take custody of CrowdStrike API credentials or validate native S3/SQS collection.

Fixture-backed platform modules and families:

| Family | Sourcetype | Match token | Notes |
|---|---|---|---|
| Process lifecycle | `crowdstrike:falcon:fdr:process` | `ProcessRollup2`, `EndOfProcess` | Preserves command line where present, image path, parent process, process IDs, hash, device and tenant IDs. |
| Network IPv4 | `crowdstrike:falcon:fdr:network` | `NetworkConnectIP4`, `NetworkListenIP4`, `NetworkReceiveAcceptIP4` | Preserves local/remote IPs and ports, protocol token, connection direction/listen context, process context, device IDs. |
| DNS request | `crowdstrike:falcon:fdr:dns` | `DnsRequest`, `SuspiciousDnsRequest` | Preserves domain name, request-type token, and process/device context. |
| File/document activity | `crowdstrike:falcon:fdr:file` | `NewExecutableWritten`, `ExecutableDeleted`, `NewScriptWritten`, `PdfFileWritten`, `OoxmlFileWritten`, `CriticalFileAccessed` | Preserves target file path, SHA256/file identifier/size/access type where present, and process/device context. |
| Sensor/config/identity | `crowdstrike:falcon:fdr:asset` | `SensorHeartbeat`, `ConfigStateUpdate`, `UserIdentity` | Endpoint state, config-state, and identity context only. |
| Devices API host inventory | `crowdstrike:falcon:api:devices` | `device_id`, `agent_version`, `hostname` | Conservative API/collector relay record, not proof of native FDR/Event Streams host inventory emission. |
| Spotlight vulnerability | `crowdstrike:falcon:api:spotlight` | `vulnerability_id`, `cve`, `host_info` | Conservative API/collector relay record preserving vulnerability, CVE, host, application, and remediation context. |
| Intelligence indicator/feed | `crowdstrike:falcon:api:intel` | `indicator_value`, `indicator_type`, `confidence` | Conservative API/feed relay record preserving observable, actor, malware, kill-chain, confidence, target, and vulnerability context; not proof of native Event Streams delivery. |
| Event Streams audit | `crowdstrike:falcon:eventstream:audit` | `AuthActivityAuditEvent`, `UserActivityAuditEvent` | Sample-backed streaming-envelope records preserving actor/API client, source IP, operation, service, result, and audit attributes. |
| Event Streams RTR session | `crowdstrike:falcon:eventstream:rtr` | `RemoteResponseSessionStartEvent`, `RemoteResponseSessionEndEvent` | Sample-backed session lifecycle records preserving session ID, host, user, and start timestamp. |
| Identity Protection | `crowdstrike:falcon:eventstream:identity` | `IdentityProtectionEvent`, `IdpDetectionSummaryEvent` | Sample-backed identity incident/detection records preserving user, endpoint, severity, tactic/technique, and incident/detection IDs. |
| Detection/response summary | `crowdstrike:falcon:eventstream:detection` | `DetectionSummaryEvent`, `EppDetectionSummaryEvent`, `DataProtectionDetectionSummaryEvent` | Sample-backed detection/response rows preserving process/file/user, severity, tactic/technique, disposition, response action, and data-protection context where present. |
| Firewall policy match | `crowdstrike:falcon:eventstream:policy` | `FirewallMatchEvent` | Sample-backed policy-match record preserving local/remote tuple, policy/rule/action, host, process, and match status. |

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20076` with source tag `CROWDSTRIKE_FALCON`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `epintel` / sourcetype(s) `crowdstrike:falcon:fdr:process`, `crowdstrike:falcon:fdr:network`, `crowdstrike:falcon:fdr:dns`, `crowdstrike:falcon:fdr:file`, and 8 more declared sourcetype(s). Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Evidence and provenance

This pack is grounded in the 2026-06-08 deep evidence unblock scans:

- `docs/evidence/crowdstrike-falcon-evidence-unblock-20260608.md` captured the initial FDR/Event Streams-style evidence for the currently implemented fixture-backed pack.
- `docs/evidence/crowdstrike-falcon-platform-evidence-unblock-20260608.md` records a follow-up platform evidence retry for Devices/host inventory, Spotlight vulnerability, Event Streams audit/auth/user activity, RTR session start/end, Identity Protection, selected policy/response events, and Intelligence indicator/feed records.
- Elastic CrowdStrike integration public documentation and FDR data-stream manifest describe Falcon/FDR/Event Streams ingestion as log records.
- Elastic FDR field catalogue and public parser test events expose field structures for `ProcessRollup2`, `EndOfProcess`, `NetworkConnectIP4`, `NetworkListenIP4`, `DnsRequest`, `SuspiciousDnsRequest`, `SensorHeartbeat`, `ConfigStateUpdate`, `NewExecutableWritten`, `NewScriptWritten`, `PdfFileWritten`, `OoxmlFileWritten`, `CriticalFileAccessed`, and `UserIdentity`.
- Official CrowdStrike Developer Center / FalconPy evidence plus Elastic public integration samples now back conservative API-resource relay fixtures for Devices host inventory and Spotlight vulnerability records. Falcon Event Streams audit/auth/user activity, RTR session, Identity Protection, detection summary, data-protection/response, and firewall policy-match rows are implemented from public Elastic sample-backed structures. Intelligence indicator/feed records are implemented as a conservative API/feed relay variant from public FalconPy/XSOAR field-shape evidence.
- CrowdStrike's public FDR repository was reachable and identifies the FDR source area, but did not itself provide enough event rows for fixtures.

Fixture rows in this pack are synthetic-equivalent. They preserve public field names and event-family shape while replacing values with example hostnames, documentation IP ranges, synthetic IDs, and synthetic hashes. No customer tenant values, secrets, tokens, or proprietary samples are included.

## Fixture semantics

Fixture file: `test-events/crowdstrike_falcon_test_events.jsonl`.

- Format: JSON object per line.
- Wire/envelope in fixture file: headerless JSON payload (`envelope=none`).
- Intended relay: line-delimited TCP syslog/source-tag relay on port `20076`; production TLS/RFC5425 can be used if locally configured.
- Event boundary: one event per line, newline separated.
- Multiline: false.
- Timestamps: FDR-style rows use millisecond epoch string in `timestamp`; Event Streams-style rows use `metadata.eventCreationTime`; API/feed rows use their documented ISO8601 timestamp fields. Splunk props use the matching `%s%3N` or ISO8601 parser per sourcetype.
- Markers: each `SC4S_CROWDSTRIKE_FALCON_TEST_*` marker appears exactly once and is safe for read-back SPL.
- Field delimiting/escaping: JSON escaping; command-line and Windows path examples are synthetic.

## Validation status

Current quality/trust is `curated` / `unverified`.

No CrowdStrike tenant, FDR/Event Streams relay, SC4S TEST listener, HEC delivery, or Splunk indexed read-back was available. Local preflight evidence is recorded at `validation/preflight-2026-06-08.md`: the dedicated listener on `127.0.0.1:20076` and local Splunk TEST ports `8089`/`8000` refused connections.

Validation SPL to run after a testbed exists:

```spl
index=epintel "SC4S_CROWDSTRIKE_FALCON_TEST_" earliest=-2h
| table _time index sourcetype source vendor product vendor_product crowdstrike_event_simpleName action signature crowdstrike_aid crowdstrike_cid device_id agent_version device_name host_status platform_name os_version first_seen last_seen external_ip local_ip device_tags vulnerability_id cve_id vulnerability_status severity remediation affected_product affected_version indicator_value indicator_type indicator_confidence indicator_tags threat_actor malware_family kill_chain_phase threat_type target_region published_date last_updated identity_incident_id detect_id detect_name detect_description severity_name tactic technique objective endpoint_ip policy_name rule_name rule_action response_action destination data_volume operation service result session_id session_start session_end event_utc_timestamp os_platform user user_domain process process_id process_command_line parent_process parent_process_id src_ip src_port dest_ip dest_port transport dns_request_type query url file_path file_name file_identifier file_access_type file_size file_hash containment_state sensor_state config_build config_state_hash config_state_data user_id marker _raw
```

Expected count: `23`.

A disposable Docker/Compose harness is now provided at `scripts/e2e_docker_compose.sh` for permitted lab runs. Use `packs/crowdstrike_falcon/scripts/e2e_docker_compose.sh plan` to review the stages without Docker, or `run` to stand up Splunk TEST + SC4S TEST, replay all 23 fixture events through TCP `20076`, and query `index=epintel` for the declared sourcetype and field coverage. This harness is an executable replay/read-back requirements only; until it is run successfully and evidence is retained under `validation/`, it is not replay/read-back validation.

Promotion to `validated` or `s6_verified` requires replay through the intended SC4S route plus Splunk read-back proving event count, index, sourcetypes, source, vendor/product, timestamps, and the listed normalized fields.

## Known limitations

- This pack is intentionally named/displayed as CrowdStrike Falcon Platform rather than a single Falcon product surface. It keeps the `crowdstrike_falcon` pack ID and existing runtime source tag for compatibility. Splitting into separate packs should only happen later if modules need separate listeners, indexes, validation harnesses, or independently downloadable artifacts.
- Devices API host inventory, Spotlight vulnerability, and Intelligence indicator/feed API-resource records are implemented only as conservative API/collector relay variants. This is not native FDR/Event Streams proof for those modules, and it is not replay/read-back validation.
- Event Streams audit/auth/user activity, RTR session, Identity Protection, selected detection/response summary, and firewall policy-match rows are conservatively implemented from public sample-backed streaming structures. This does not prove native delivery for local tenants or collector wrappers.
- RTR command/action rows, admin policy-change audit rows, native FDR/Event Streams proof for API-feed modules, and Intelligence report events remain blocked until exact public samples, official schemas, or sanitized source evidence are available.
- This pack does not validate native FDR S3/SQS collection; it assumes a local collector/relay emits one JSON event per line to SC4S.
- `event_simpleName` is preserved as the raw CrowdStrike action token. Analyst `action` and `signature` are aliases, not a complete normalized taxonomy.
- `cid` may be tenant-sensitive in real deployments; this pack preserves it by default for correlation, and operators should apply tenant-safe controls locally if needed.
- No default drops, null queues, or lossy field redaction are included.

## Reduction review

Default posture is retain-all for the implemented Falcon JSON relay variants. Security-critical fields include `event_simpleName`, `aid`, `cid`, process command line and image path, file path/hash/identifier/access context, DNS query/request type, device/platform identifiers, sensor/config state, user identity context, Devices API host inventory fields, Spotlight vulnerability/CVE/remediation context, Intelligence indicator value/type/confidence/actor/malware/tag context, Event Streams audit operation/result context, RTR session identifiers, Identity Protection incident/detection IDs, detection severity/tactic/technique, data-protection response context, and firewall policy/rule/action fields.

`docs/crowdstrike_falcon_reduction_candidates.csv` lists advisory candidates such as high-volume heartbeat rows or controlled handling of tenant identifiers. These are not enabled by default and require local replay/read-back plus rollback guidance before use.

## Splunk dashboard

`splunk/default/data/ui/views/crowdstrike_falcon_soc.xml` — SOC overview dashboard covering ingestion health, active detections, Identity Protection incident/detection rows, Spotlight open vulnerabilities (requires `crowdstrike:falcon:api:spotlight` from a dedicated API relay — do not confuse with FDR/Event Streams sourcetypes), RTR remote sessions, FDR process/network/DNS/file activity, FDR sensor heartbeat/config/user-identity asset rows, Falcon audit events, firewall policy matches, threat intelligence indicators, and Devices API inventory. The dashboard has been run against Splunk TEST with the pack fixtures and the evidence is recorded at `validation/dashboard-splunk-fixture-validation-2026-06-16.md`. This is dashboard XML + fixture-backed SPL validation only, not live CrowdStrike/SC4S replay-readback or field validation.

The dashboard does **not** statement coverage for the deprecated Falcon Incidents API entity export. Current incident-style dashboard coverage is the fixture-backed Identity Protection incident/detection stream (`crowdstrike:falcon:eventstream:identity`). Add sanitized tenant samples or official schema-backed emitted records before introducing a separate `crowdstrike:falcon:api:incidents` source mode.

## 2026-06-15 operator requirements hardening

This pass aligned the runtime `product`/`vendor_product` values with the Falcon Platform JSON Relay pack identity, added read-back table coverage for already-emitted aliases such as `signature`, `dest`, `url`, `process_id`, `parent_process_id`, `file_name`, `event_utc_timestamp`, and `vendor_product`, and made the dashboard device filter search Splunk metadata `host` plus extracted `device_name`/`dest`. It did not add new CrowdStrike event families or promote validation/trust.
