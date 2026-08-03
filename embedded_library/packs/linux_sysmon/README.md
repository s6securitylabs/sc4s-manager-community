# Microsoft Sysmon for Linux pack

Conservative SecHub Resources SC4S pack for Microsoft Sysmon for Linux records relayed as one-line XML through Linux syslog or an equivalent file/collector relay. Initial scope is fixture-backed Event ID 1 process creation, Event ID 2 file creation-time change, Event ID 3 network connection, Event ID 5 process termination, Event ID 11 file creation, Event ID 16 Sysmon configuration state change, Event ID 22 DNS query, Event ID 23 archived file deletion, and Event ID 26 file delete detected without archiving.

This is curated intake guidance, not live Linux Sysmon validation. Trust remains `unverified` and quality remains `curated` until real Linux Sysmon relay replay and Splunk indexed read-back evidence exists. Event ID 2 is grounded in Microsoft SysmonCommon and SysmonForLinux integration-test evidence for file creation-time changes; Event ID 22 is schema/parser-evidence-backed only; Microsoft Linux tests note DNS generation can depend on kernel/build support, so QueryStatus/QueryResults formatting still needs local replay/read-back.

## Evidence searched

- `docs/evidence/linux-sysmon-evidence-scan-20260608.md` records Microsoft Sysmon for Linux repository evidence, SysmonCommon manifest Event ID 22 schema, Elastic `sysmon_linux` parser evidence, and OSSEM/Splunk/Sigma field corroboration for supported event IDs; the 2026-06-15 follow-up adds Microsoft SysmonCommon/SysmonForLinux-grounded Event ID 26 file-delete-detected coverage.
- Public evidence supports Sysmon for Linux XML output to `/var/log/syslog` and the documented/tested field shapes used for synthetic-equivalent fixtures.
- Event ID 2 file creation-time change is included conservatively from Microsoft SysmonCommon manifest fields (`TargetFilename`, `CreationUtcTime`, `PreviousCreationUtcTime`) plus SysmonForLinux integration-test coverage. Event ID 22 DNS query is included conservatively from public schema/parser evidence (`QueryName`, `QueryStatus`, `QueryResults`, `Image`, `User`), but no real Linux DNS event from this environment has been replayed or read back.

## Scope

- Listener: dedicated TCP syslog example on port `20072` with source tag `LINUX_SYSMON`.
- Payloads: one complete `<Event>...</Event>` XML record per line from Sysmon for Linux syslog/file/collector relay paths that preserve Event XML.
- Routed sourcetypes: `linux:sysmon:process`, `linux:sysmon:file_time`, `linux:sysmon:network`, `linux:sysmon:process_terminate`, `linux:sysmon:file_create`, `linux:sysmon:config`, `linux:sysmon:dns_query`, `linux:sysmon:file_delete`, and `linux:sysmon:file_delete_detected`.
- Default index: `osnix`.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20072` with source tag `LINUX_SYSMON`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `osnix` and sourcetype(s) `linux:sysmon:process`, `linux:sysmon:file_time`, `linux:sysmon:network`, `linux:sysmon:process_terminate`, `linux:sysmon:file_create`, and 4 more declared sourcetype(s).

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Fixture semantics

- File: `test-events/linux_sysmon_test_events.txt`.
- Format: Sysmon for Linux XML, one event per physical line.
- Wire/envelope: headerless fixture payloads; `scripts/send_tcp_20072.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; journald-specific envelopes, multiline/large-event handling, and collector JSON wrappers are out of scope for this initial pack.
- Timestamp: XML `TimeCreated SystemTime` values and `UtcTime` fields use UTC; production relays must preserve timezone-qualified time or document collector timezone.
- Markers: `SC4S_LINUX_SYSMON_TEST_*` values each occur exactly once.
- Sanitisation: fixtures use `EXAMPLE\alice`, `example.test` hostnames, RFC5737 addresses, and synthetic GUID/hash values; no customer events are included.

Validation SPL smoke pattern:

```spl
index=osnix "SC4S_LINUX_SYSMON_TEST_" earliest=-2h
| table _time index sourcetype source vendor product event_id provider channel record_id computer user process_guid process_id process_path process_name command_line parent_process_guid parent_process_path parent_command_line hashes sha256 md5 src_ip src_port dest_ip dest_port dest_host transport initiated query_name query_status query_results dns_question dns_answers target_filename file_path file_name creation_utc_time previous_creation_utc_time configuration configuration_hash hashes sha256 md5 is_executable archived action signature signature_id marker _raw
```

## Disposable E2E harness requirements

`scripts/e2e_docker_compose.sh` now provides an idempotent Docker/Compose harness requirements for a disposable SC4S TEST -> Splunk TEST run. Use `packs/linux_sysmon/scripts/e2e_docker_compose.sh plan` to review the stages without Docker, or `... run` in a permitted lab to write `.tmp/e2e/linux_sysmon/compose.yaml`, start Splunk and SC4S containers, create/search `index=osnix`, replay all 9 Linux Sysmon XML fixture records through TCP `20072`, and run summary/detail read-back SPL.

A passing harness run would prove only fixture-backed replay/read-back for the declared one-line Sysmon for Linux XML relay shape and Event IDs 1, 2, 3, 5, 11, 16, 22, 23, and 26. It still does not prove live Sysmon for Linux emission, Sysmon policy/configuration behavior, Linux kernel/build DNS support, journald/syslog/file-agent wrappers, multiline XML handling, production readiness, or field validation.

## Reduction stance

No event drops or field deletion are enabled by default. `docs/linux_sysmon_reduction_candidates.csv` lists advisory-only candidates for known-good process noise, benign internal network connections, repetitive config-state lines, and hash-subset review. Command lines, parent/child process context, hashes, user IDs, network tuples, file paths, raw EventID/provider/channel, configuration state, and collector envelope metadata are risky to drop and must be retained by default.

## Dashboard scope

`linux_sysmon_overview.xml` is a fixture-backed Splunk SimpleXML overview for onboarding and first triage across the nine covered Sysmon for Linux XML families. It includes data-arrival health, event-family distribution, process creation/termination counters, file creation-time changes, network and DNS activity, file/configuration-change review, user/process/destination context, source/sourcetype/host coverage, and recent raw XML drilldown.

The dashboard is intentionally limited to fields proven by `test-events/linux_sysmon_test_events.txt` and `splunk/default/props.conf`: EventID/provider/channel context, user, computer, process and parent-process fields, command lines, hashes, network tuples, DNS query fields, file paths, file-delete archive/executable flags, configuration state, action/signature fields, and marker context. It does not state coverage for unrepresented Sysmon for Linux Event IDs, local file creation-time/timestomp workflow validation, journald or collector JSON wrappers, multiline XML, local DNS runtime behavior beyond the fixture shape, or replay/read-back validation.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-08.md` shows port `20072` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from public documentation/repository evidence, not real endpoint captures.
- Only Event IDs 1, 2, 3, 5, 11, 16, 22, 23, and 26 are parser/fixture-backed. Event ID 22 DNS query coverage is schema/parser-evidence-backed only and still needs local Linux runtime confirmation; broader event IDs, collector JSON wrappers, journald-specific envelopes, and distro-specific syslog packaging remain future work.
- Reduction candidates are advisory only and require local replay/read-back plus rollback review before enablement.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real Linux Sysmon relay replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, EventID/provider/channel, endpoint/process/network/file creation-time/file-delete archive flag/config fields, eventtypes/tags, and normalized fields.
