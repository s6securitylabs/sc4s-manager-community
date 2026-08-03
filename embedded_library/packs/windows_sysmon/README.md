# Microsoft Windows Sysmon pack

Conservative SecHub Resources SC4S pack for Microsoft Sysmon records relayed as one-line Windows Event XML. Current scope is fixture-backed Event ID 1 process creation, Event ID 2 file creation-time change, Event ID 3 network connection, Event ID 6 driver load, Event ID 7 image load, Event ID 8 CreateRemoteThread/process-create remote thread, Event ID 9 raw access read, Event ID 10 process access, Event ID 11 file creation, Event IDs 12/13/14 registry activity, Event IDs 17/18 named-pipe activity, Event IDs 19/20/21 WMI filter/consumer/binding activity, Event ID 22 DNS query, Event ID 23 file deletion, Event ID 24 clipboard change, Event ID 25 process tampering, and Event ID 26 file-delete-detected records from the 2026-06-08 evidence scan plus additional OSSEM/Microsoft documentation checks.

This is curated intake guidance, not live Sysmon validation. Trust remains `unverified` and quality remains `curated` until real Sysmon relay replay and Splunk indexed read-back evidence exists.

## Evidence searched

- `docs/evidence/windows-sysmon-evidence-scan-20260608.md` records Microsoft Sysinternals Sysmon documentation and OSSEM field dictionaries for Event IDs 1, 3, 11, and 22. Follow-up expansions also checked public OSSEM dictionaries for Event IDs 7, 10, 12, 13, 14, 17, 18, and 23, plus the Microsoft SysmonCommon manifest for Event IDs 2, 6, 8, 9, 19, 20, 21, 24, 25, and 26, before adding fixtures.
- Public documentation supports the field shapes used for synthetic-equivalent fixtures: process identity, command line, hashes, parent context, file creation-time change context, network endpoints, loaded module/signature context, remote-thread source/target/start context, driver image/signature context, raw device access context, clipboard session/client context, WMI filter query/consumer destination/binding context, process-access target/access-mask context, registry target/details/new-name context, named-pipe name/process context, file target path and deletion/detected-deletion context, process-tampering type context, DNS query/result, provider/channel, and timestamps.
- SwiftOnSecurity and Sysmon Modular configuration repositories were reachable but are treated only as reduction/event-selection context; no rules or proprietary content are copied.

## Scope

- Listener: dedicated TCP syslog example on port `20071` with source tag `WINDOWS_SYSMON`.
- Payloads: one complete `<Event>...</Event>` XML record per line from WEF/WEC, NXLog, Fluent Bit, Cribl, or a similar relay that preserves Sysmon Event XML.
- Routed sourcetypes: `windows:sysmon:process`, `windows:sysmon:network`, `windows:sysmon:driver_load`, `windows:sysmon:image_load`, `windows:sysmon:remote_thread`, `windows:sysmon:raw_access`, `windows:sysmon:process_access`, `windows:sysmon:file_create`, `windows:sysmon:registry`, `windows:sysmon:pipe`, `windows:sysmon:dns`, `windows:sysmon:file_delete`, `windows:sysmon:file_delete_detected`, `windows:sysmon:clipboard`, and `windows:sysmon:tampering`.
- Default index: `oswinsec`.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20071` with source tag `WINDOWS_SYSMON`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `oswinsec` and the declared `windows:sysmon:*` sourcetypes for process, network, driver/image load, remote thread, raw access, process access, file create/time-change/delete/delete-detected, registry, pipe, DNS, clipboard, WMI, and tampering families.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Fixture semantics

- File: `test-events/windows_sysmon_test_events.txt`.
- Format: Windows Event XML, one event per physical line.
- Wire/envelope: headerless fixture payloads; `scripts/send_tcp_20071.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; multiline EVTX/XML exports are out of scope for this initial pack.
- Timestamp: XML `TimeCreated SystemTime` values and `UtcTime` fields use UTC; production relays must preserve timezone-qualified time or document collector timezone.
- Markers: `SC4S_WINDOWS_SYSMON_TEST_*` values each occur exactly once.
- Sanitisation: fixtures use `EXAMPLE\alice`, `example.test` hostnames, RFC5737 addresses, and synthetic GUID/hash values; no customer events are included.

Validation SPL smoke pattern:

```spl
index=oswinsec "SC4S_WINDOWS_SYSMON_TEST_" earliest=-2h
| table _time index sourcetype source vendor product event_id provider channel record_id computer user process_guid process_id process_path process_name command_line parent_process_guid parent_process_path parent_command_line hashes sha256 md5 src_ip src_port dest_ip dest_port dest_host transport initiated image_loaded loaded_driver signed file_signature signature_status source_process_guid source_process_id source_process_path source_process_name target_process_guid target_process_id target_process_path target_process_name new_thread_id start_address start_module start_function granted_access call_trace target_filename file_path file_name creation_utc_time previous_creation_utc_time query_name query_status query_results is_executable archived delete_detected target_object registry_event_type registry_details registry_new_name pipe_name device clipboard_session client_info wmi_event_type wmi_operation wmi_namespace wmi_name wmi_query wmi_type wmi_destination wmi_consumer wmi_filter tamper_type action signature signature_id marker _raw
```

## Disposable E2E harness requirements

`packs/windows_sysmon/scripts/e2e_docker_compose.sh` defines an idempotent Splunk TEST + SC4S TEST Docker/Compose harness for the fixture-backed one-line Sysmon XML relay shape. Use `plan` to inspect the exact command requirements without Docker:

```bash
packs/windows_sysmon/scripts/e2e_docker_compose.sh plan
```

The one-shot `run` mode is intended to start disposable Splunk and SC4S containers, create/search `index=oswinsec`, replay all 22 Sysmon XML fixtures through TCP `20071`, sample SC4S/syslog-ng counters, and query Splunk for the expected `windows:sysmon:*` sourcetypes and detailed required-field coverage. The harness is ready for a permitted Docker lab run, but it is not replay/read-back evidence until it is actually executed and the Splunk read-back output is retained.

Evidence boundaries: the harness does not prove live Windows endpoint emission, Sysmon configuration policy, WEF/WEC/NXLog/Fluent Bit/Cribl wrapper behavior, native EVTX, collector-normalized JSON, multiline XML exports, complete Sysmon provider coverage, production readiness, or field validation. Trust remains `curated`/`unverified` until sanctioned real-source or production-equivalent replay/read-back evidence exists.

## Reduction stance

No event drops or field deletion are enabled by default. `docs/windows_sysmon_reduction_candidates.csv` lists advisory-only candidates for known-good process noise, benign internal network connections, repetitive DNS queries, and hash-subset review. Command lines, parent/child process context, remote-thread source/target/start context, hashes, user/logon context, network tuples, DNS query/results, driver image/signature context, raw-access device paths, clipboard session/client context, registry paths/details, named-pipe names, process-tampering type, file paths and creation-time-change fields, raw EventID/provider/channel, and collector envelope metadata are risky to drop and must be retained by default.

## Dashboard scope

The Splunk overview dashboard at `splunk/default/data/ui/views/windows_sysmon_overview.xml` is scoped to the same fixture-backed XML relay families as this pack: Event ID 1 process creation, Event ID 2 file creation-time changes, Event ID 3 network connections, Event ID 6 driver loads, Event ID 7 image loads, Event ID 8 remote-thread creation, Event ID 9 raw access reads, Event ID 10 process access, Event ID 11 file creation, Event IDs 12/13/14 registry activity, Event IDs 17/18 named-pipe activity, Event ID 22 DNS queries, Event ID 23 file deletion, Event ID 24 clipboard changes, Event ID 25 process tampering, and Event ID 26 file-delete-detected rows. It provides arrival health, family/action distribution, user/endpoint/process context, network and DNS triage, image-load/signature review, remote-thread source/target/start review, process-access target review, process-tampering triage, driver/raw-access/clipboard review, file create/time-change/delete/delete-detected context, registry and named-pipe triage, source/sourcetype/host onboarding coverage, and raw XML drilldown.

Dashboard SPL uses only fields present in the synthetic-equivalent fixtures and exposed by `splunk/default/props.conf`, including `event_id`, `action`, `user`, `computer`, `process_path`, `process_name`, `command_line`, `src_ip`, `src_port`, `dest_ip`, `dest_port`, `dest_host`, `query_name`, `query_status`, `query_results`, `target_filename`, `file_name`, `creation_utc_time`, `previous_creation_utc_time`, `image_loaded`, `signed`, `file_signature`, `signature_status`, `source_process_path`, `source_process_name`, `target_process_path`, `target_process_name`, `new_thread_id`, `start_address`, `start_module`, `start_function`, `granted_access`, `call_trace`, `target_object`, `registry_event_type`, `registry_details`, `registry_new_name`, `pipe_name`, `device`, `clipboard_session`, `client_info`, `loaded_driver`, `delete_detected`, `tamper_type`, `hashes`, `sha256`, `md5`, `marker`, and raw XML. The dashboard does not state coverage for unrepresented Sysmon Event IDs, native EVTX parsing, multiline XML exports, JSON collector wrappers, or live replay/read-back validation.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-08.md` shows port `20071` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from public documentation, not real endpoint captures.
- Only Event IDs 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23, 24, 25, and 26 are parser/fixture-backed. Other newer or less common Sysmon events remain future work.
- JSON collector wrappers are documented as future variants only; this pack currently covers one-line XML payloads.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real Sysmon relay replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, EventID/provider/channel, process/file-time/network/driver-load/remote-thread/raw-access/image-load/process-access/file/DNS/registry/pipe/WMI/clipboard/tampering fields, eventtypes/tags, and normalized fields.
