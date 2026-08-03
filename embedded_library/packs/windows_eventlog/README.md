# Microsoft Windows Event Log relay

Curated SecHub Resources SC4S pack for Windows Event Log records relayed as one-line Windows Event XML through a dedicated SC4S listener. The pack covers fixture-backed Security logon success/failure, Kerberos TGT/TGS/pre-authentication failure, NTLM credential validation failure, Security account creation/deletion/change, group membership, Security process creation, PowerShell script block, Microsoft Defender detection, object access, audit log clearing, audit-policy change, service-installation, and scheduled-task creation examples.

## Scope and posture

- Vendor/product: Microsoft Windows Event Log relay.
- Intended source modes: WEF/WEC XML, NXLog/Winlogbeat/Fluent Bit/Cribl relay that preserves Windows Event XML or equivalent event fields.
- Current fixture shape: one XML `<Event>...</Event>` per physical line, wrapped by the send helper in RFC5424-over-TCP syslog.
- Default index: `oswinsec` for the current security/endpoint fixture families.
- Trust/quality: `curated` / `unverified`. This is not validated or S6 verified.

The pack intentionally does not prove complete Windows TA parity, full EVTX parsing, or native Windows collection. It is a Library parsing/routing requirements for relay paths that hand SC4S one record per line.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20063` with source tag `WINDOWS_EVENTLOG`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `oswinsec` and sourcetype(s) `windows:eventlog:security`, `windows:eventlog:process`, `windows:eventlog:powershell`, `windows:eventlog:defender`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Event families

| Family | Event ID examples | Sourcetype | Notes |
| --- | --- | --- | --- |
| Security logon/authentication | 4624, 4625, 4768, 4769, 4771, 4776 | `windows:eventlog:security` | Fixtures prove successful and failed logon XML structures plus Kerberos TGT/TGS/pre-authentication context, NTLM credential-validation failure context, source IP/port, logon type, failure/status tokens, package, ticket option/encryption/pre-auth tokens, and workstation context. |
| Security account management and group membership | 4720, 4726, 4732, 4738 | `windows:eventlog:security` | Fixtures prove account-created/deleted/changed context and local-group membership context with subject, target account/group, member, domain, and SID fields. |
| Security object/policy/service/log/task changes | 4663, 4719, 4697, 1102, 4698 | `windows:eventlog:security` | Fixtures prove object access path/type/mask context, audit-log clearing subject context, audit-policy change context, service-installation fields, and scheduled-task name/content fields. |
| Process creation | 4688 | `windows:eventlog:process` | Preserves process path, command line, parent process. |
| PowerShell script block | 4104 | `windows:eventlog:powershell` | Preserves script block text; high-value but sensitive. |
| Microsoft Defender detection | 1116 | `windows:eventlog:defender` | Preserves threat name, path, and severity text. |

## Fixture semantics

`test-events/windows_eventlog_test_events.txt` contains eighteen synthetic-equivalent events. Each line is one complete XML event record with a unique marker:

- `SC4S_WINDOWS_EVENTLOG_TEST_LOGON_001`
- `SC4S_WINDOWS_EVENTLOG_TEST_PROCESS_002`
- `SC4S_WINDOWS_EVENTLOG_TEST_POWERSHELL_003`
- `SC4S_WINDOWS_EVENTLOG_TEST_DEFENDER_004`
- `SC4S_WINDOWS_EVENTLOG_TEST_LOGON_FAIL_005`
- `SC4S_WINDOWS_EVENTLOG_TEST_ACCOUNT_CREATE_006`
- `SC4S_WINDOWS_EVENTLOG_TEST_OBJECT_ACCESS_007`
- `SC4S_WINDOWS_EVENTLOG_TEST_AUDIT_POLICY_008`
- `SC4S_WINDOWS_EVENTLOG_TEST_SERVICE_INSTALL_009`
- `SC4S_WINDOWS_EVENTLOG_TEST_ACCOUNT_DELETE_010`
- `SC4S_WINDOWS_EVENTLOG_TEST_GROUP_MEMBER_ADD_011`
- `SC4S_WINDOWS_EVENTLOG_TEST_LOG_CLEARED_012`
- `SC4S_WINDOWS_EVENTLOG_TEST_SCHEDULED_TASK_013`
- `SC4S_WINDOWS_EVENTLOG_TEST_ACCOUNT_CHANGE_014`
- `SC4S_WINDOWS_EVENTLOG_TEST_NTLM_CREDENTIAL_015`
- `SC4S_WINDOWS_EVENTLOG_TEST_KERBEROS_TGT_016`
- `SC4S_WINDOWS_EVENTLOG_TEST_KERBEROS_TGS_017`
- `SC4S_WINDOWS_EVENTLOG_TEST_KERBEROS_PREAUTH_FAIL_018`

The fixture file is intentionally headerless XML payload. `scripts/send_tcp_20063.sh` wraps each line in an RFC5424 syslog envelope for the dedicated TCP listener. Fixture timestamps use UTC `SystemTime` values; production relays must preserve timezone-qualified `TimeCreated/SystemTime` or document the collector timezone.

## Validation harness

Current status: blocked preflight only. On 2026-06-07 this host had no listener on TCP 20063 and no local Splunk TEST management/web reachability. See `validation/preflight-2026-06-07.md`.

This pack now includes `scripts/e2e_docker_compose.sh`, an idempotent Docker/Compose harness requirements for a disposable SC4S TEST -> Splunk TEST replay/read-back path. The harness can write a local Compose file, start Splunk/SC4S containers, create `index=oswinsec`, replay all 18 Windows Event XML fixtures through TCP `20063`, and run summary/detail SPL read-back checks. Run `packs/windows_eventlog/scripts/e2e_docker_compose.sh plan` for the exact stages. A passing harness run would be lab replay/read-back evidence for the fixture-backed XML relay shape only; it would not prove a live Windows host/domain-controller feed, WEF/WEC/NXLog/Fluent Bit/Cribl wrapper behavior, native EVTX, collector-normalized JSON, multiline XML exports, or field validation.

Validation SPL once a non-production SC4S/Splunk testbed is available:

```spl
index=oswinsec "SC4S_WINDOWS_EVENTLOG_TEST_" earliest=-2h
| table _time index sourcetype source vendor product event_id signature signature_id provider user user_domain src_user src_user_domain src_ip src_port logon_type workstation package_name service_sid ticket_options ticket_encryption_type pre_auth_type failure_code logon_guid transmitted_services failure_reason status sub_status object_name object_type access_mask access_list object_process audit_policy_changes policy_category policy_subcategory service_name service_file_name service_type service_start_type service_account target_sid member_name member_sid subject_logon_id task_name task_content display_name user_principal_name sam_account_name user_account_control dest process process_command_line parent_process script_block_text threat_name file_path severity marker _raw
```

Expected count: 18 events, with the four sourcetypes listed above and no dropped markers.

## Dashboard scope

`splunk/default/data/ui/views/windows_eventlog_overview.xml` provides a conservative onboarding and first-triage overview for the fixture-backed Windows Event XML relay families in this pack: Security logon/authentication success and failure, Kerberos TGT/TGS/pre-authentication events, Security account creation/change, Security object access, audit-policy change, service installation, process creation, PowerShell script block, and Microsoft Defender detection records.

Panels use only the `windows:eventlog:*` sourcetypes plus fields proven by the fixtures and `props.conf`: `event_id`, `provider`, `user`, `user_domain`, `src_user`, `src_user_domain`, `src_ip`, `src_port`, `logon_type`, `workstation`, `package_name`, `service_sid`, `ticket_options`, `ticket_encryption_type`, `pre_auth_type`, `failure_code`, `logon_guid`, `transmitted_services`, `failure_reason`, `status`, `sub_status`, `object_name`, `object_type`, `access_mask`, `access_list`, `object_process`, `audit_policy_changes`, `policy_category`, `policy_subcategory`, `service_name`, `service_file_name`, `service_type`, `service_start_type`, `service_account`, `target_sid`, `member_name`, `member_sid`, `subject_logon_id`, `task_name`, `task_content`, `display_name`, `user_principal_name`, `sam_account_name`, `user_account_control`, `dest`, `process`, `process_command_line`, `parent_process`, `script_block_text`, `threat_name`, `file_path`, `severity`, `signature`, `signature_id`, and `marker`. The dashboard includes event-arrival health, failed-logon/Kerberos/account/group/log-clear/task/policy/service/object counters, Kerberos ticket/pre-authentication context, family distribution, process/PowerShell and Defender counters, user/source-IP context, family-specific triage tables, onboarding coverage, and raw XML drilldown.

The dashboard is not replay/read-back validation and does not expand scope to native EVTX parsing, multiline XML exports, collector-normalized JSON, full Windows TA parity, or unrepresented Windows providers/Event IDs. Event 4738 coverage is limited to Microsoft Learn account-change fields in the synthetic-equivalent fixture; no domain-controller replay/read-back is published. Kerberos coverage is limited to Microsoft Learn Event 4768/4769/4771 field structures in synthetic-equivalent fixtures; no domain-controller relay/read-back, Kerberos policy behavior, or complete authentication workflow validation is published.

## Reduction posture

No default drops, field deletion, null queues, or privacy transforms are shipped. `docs/windows_eventlog_reduction_candidates.csv` documents review-required reduction thinking. Command line and PowerShell script block content can be sensitive, but they are high-value security evidence and are retained by default.

## Known limitations

- No live Windows relay, SC4S runtime replay, HEC delivery, Splunk indexed read-back, or Manager apply evidence has been captured.
- Fixtures are synthetic-equivalent and documentation-shaped; they are not real product captures.
- XML extraction is intentionally narrow and fixture-backed. Windows event providers differ widely; add families only with evidence and unique fixtures.
- WEF/NXLog/Winlogbeat/Cribl JSON variants are recorded as future-compatible variants but are not validated by this initial XML fixture set.

## Splunk Edge Processor template candidates

This pack now includes file-backed Splunk Edge Processor candidate artifacts under `edge-processor/`:

- `edge-processor/modules/windows_eventlog_success_noise_reduce.spl2` — conservative SPL2 module candidate that annotates and routes events unchanged by default.
- `edge-processor/templates/windows_eventlog_success_noise_reduce.json` — metadata for source-type definitions, transforms, destination placeholders, lossy behavior, required validation, rollback, and review status.
- `edge-processor/samples/windows_eventlog_success_noise_reduce.raw.txt` and `.parsed.jsonl` — synthetic-equivalent snippets for preview/review only.
- `edge-processor/validation/windows_eventlog_success_noise_reduce-preflight.md` — explicit preflight and rollback checklist.

No Edge Processor validation/read-back is published. Any reduction remains opt-in and must pass non-production preview, replay/read-back, detection impact review, and rollback approval before use.
