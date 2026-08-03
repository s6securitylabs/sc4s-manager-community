# Linux auditd relay

Curated SecHub Resources SC4S pack for Linux audit daemon records relayed as one audit record per line through a dedicated SC4S listener. The pack covers fixture-backed `SYSCALL`, `EXECVE`, `USER_LOGIN`, `PATH`, `CWD`, `USER_AUTH`, `CONFIG_CHANGE`, SELinux `AVC`, audit daemon `DAEMON_START`, `DAEMON_END`, and `DAEMON_CONFIG`, plus `USER_CMD`, `TTY`, and `SOFTWARE_UPDATE` records.

## Scope and posture

- Vendor/product: Linux auditd.
- Intended source modes: `/var/log/audit/audit.log`, auditd dispatcher, rsyslog/syslog-ng, or collector relay that preserves one audit record per line.
- Current fixture shape: headerless Linux audit records with `type=... msg=audit(epoch.serial)` and key/value fields.
- Default index: `osnix`.
- Trust/quality: `curated` / `unverified`. This is not validated or S6 verified.

The pack intentionally does not flatten multi-record Linux audit events into one event. `SYSCALL`, `EXECVE`, and `PATH` examples share audit serials where useful so operators can correlate records in Splunk while preserving raw audit semantics.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20064` with source tag `LINUX_AUDITD`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `osnix` and the family sourcetypes listed below.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Evidence and provenance

The fixture and required-field coverage are grounded in public Linux audit documentation and examples: `auditd(8)`, `auditd.conf(5)`, `auditctl(8)`, and public auditd parser/module references such as Elastic/Filebeat auditd documentation. Fixtures are synthetic-equivalent and use RFC5737 documentation addresses plus generic users/paths. No customer records, tenant identifiers, secrets, or proprietary TA content are included.

## Event families

| Family | Audit record type | Sourcetype | Notes |
| --- | --- | --- | --- |
| Syscall | `SYSCALL` | `linux:auditd:syscall` | Preserves syscall number, success/result, auid/uid, process command and executable. |
| Execve | `EXECVE` | `linux:auditd:execve` | Preserves command arguments as investigation evidence. |
| User login | `USER_LOGIN` | `linux:auditd:user_login` | Preserves login operation, result, source IP, terminal, and user identifiers. |
| Path | `PATH` | `linux:auditd:path` | Preserves file path, inode, object type, and audit serial context for watched-file and syscall correlation. |
| Current working directory | `CWD` | `linux:auditd:cwd` | Preserves working-directory context for audit serial correlation. |
| User auth | `USER_AUTH` | `linux:auditd:user_auth` | Preserves PAM/SSH-style authentication operation, result, account, executable, source IP, and terminal. |
| Config change | `CONFIG_CHANGE` | `linux:auditd:config_change` | Preserves audit rule operation, key, rule list, user ID, and result. |
| SELinux AVC | `AVC` | `linux:auditd:avc` | Preserves denied permission, process, path, source/target security contexts, and target class. |
| Audit daemon start | `DAEMON_START` | `linux:auditd:daemon_start` | Preserves auditd daemon version, output format, kernel version, PID, actor UID, and result for lifecycle triage. |
| Audit daemon end | `DAEMON_END` | `linux:auditd:daemon_end` | Preserves auditd terminate operation, actor IDs, PID/session placeholders, subject, and result for lifecycle shutdown triage. |
| Audit daemon config | `DAEMON_CONFIG` | `linux:auditd:daemon_config` | Preserves auditd reconfigure operation/state, actor IDs, PID/subject, and result for configuration-change triage. |
| User command | `USER_CMD` | `linux:auditd:user_cmd` | Preserves working directory, hex command payload, terminal, actor IDs, and result for command-audit triage. |
| TTY activity | `TTY` | `linux:auditd:tty` | Preserves terminal major/minor identifiers, process, and hex TTY data as sensitive source evidence. |
| Software update | `SOFTWARE_UPDATE` | `linux:auditd:software_update` | Preserves package/update context including package name/type, GPG/key result, process, executable, terminal, and result. |

## Fixture semantics

`test-events/linux_auditd_test_events.txt` contains fourteen synthetic-equivalent records. Each physical line is one complete audit record with a unique marker:

- `SC4S_LINUX_AUDITD_TEST_SYSCALL_001`
- `SC4S_LINUX_AUDITD_TEST_EXECVE_002`
- `SC4S_LINUX_AUDITD_TEST_USER_LOGIN_003`
- `SC4S_LINUX_AUDITD_TEST_PATH_004`
- `SC4S_LINUX_AUDITD_TEST_CWD_005`
- `SC4S_LINUX_AUDITD_TEST_USER_AUTH_006`
- `SC4S_LINUX_AUDITD_TEST_CONFIG_CHANGE_007`
- `SC4S_LINUX_AUDITD_TEST_AVC_008`
- `SC4S_LINUX_AUDITD_TEST_DAEMON_START_009`
- `SC4S_LINUX_AUDITD_TEST_USER_CMD_010`
- `SC4S_LINUX_AUDITD_TEST_TTY_011`
- `SC4S_LINUX_AUDITD_TEST_SOFTWARE_UPDATE_012`
- `SC4S_LINUX_AUDITD_TEST_DAEMON_END_013`
- `SC4S_LINUX_AUDITD_TEST_DAEMON_CONFIG_014`

The fixture file is intentionally headerless audit payload. `scripts/send_tcp_20064.sh` wraps each line in an RFC5424 syslog envelope for the dedicated TCP listener. Fixture timestamps use the audit `msg=audit(<epoch>.<millis>:<serial>)` field, which is UTC epoch time. Production relays must preserve the audit timestamp or document the relay timestamp policy.

## Dashboard scope

`linux_auditd_overview.xml` is a fixture-backed Splunk SimpleXML dashboard for onboarding and first triage of the covered audit record families. It shows arrival volume, family distribution, process execution, login/auth failure source/result context, audit rule changes, SELinux AVC denials, audit daemon lifecycle start/stop/configuration context, user command/TTY/software-update context, path/CWD file context, audit serial correlation, onboarding coverage, and raw audit records using only fields present in the synthetic-equivalent fixtures and exposed by `splunk/default/props.conf`.

Dashboard evidence boundaries: it does not validate live Linux audit relay behavior, does not assemble complete multi-record audit events beyond audit-serial grouping, and does not cover AppArmor-specific denial shapes, audit daemon abort/rotate/resume records, audit backlog/lost-event health records, package-manager variants beyond the fixture-backed SOFTWARE_UPDATE row, distro-specific collector wrappers, or every Linux audit record type.

## Validation harness

Current status: blocked preflight only. On 2026-06-07 this host had no listener on TCP 20064 and no local Splunk TEST management/web reachability. See `validation/preflight-2026-06-07.md`.

`validation_harness.e2e_docker_harness` now references `scripts/e2e_docker_compose.sh`, an idempotent disposable Splunk TEST + SC4S TEST harness with `plan`, `write-compose`, `up`, `replay`, `readback`, `run`, and `down` modes. The planned one-shot command is:

```bash
packs/linux_auditd/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/linux_auditd/compose.yaml`, starts Splunk/SC4S containers, creates `index=osnix`, replays all 14 auditd fixture records through TCP `20064`, and runs summary/detail read-back SPL. Passing that harness would be fixture replay/read-back evidence for the declared test route only. It would still not prove live Linux auditd source-version emission, kernel/userspace option behavior, distro-specific wrappers, collector envelopes, or production readiness, and it must not promote trust without retained evidence showing count, index, sourcetype, source, timestamp, and required fields.

Validation SPL once a non-production SC4S/Splunk testbed is available:

```spl
index=osnix "SC4S_LINUX_AUDITD_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product audit_type audit_serial action operation signature signature_id result auid uid user src src_ip process process_id process_path process_command_line cwd file_path audit_key audit_rule_list selinux_permission selinux_source_context selinux_target_context selinux_target_class daemon_operation daemon_state daemon_version kernel_version audit_format user_command_cwd user_command_hex tty_major tty_minor tty_data_hex software_package software_type gpg_result key_enforce root_dir marker _raw
```

Expected count: 14 events, with the fourteen sourcetypes listed above and no dropped markers.

## Reduction posture

No default drops, field deletion, null queues, or privacy transforms are shipped. `docs/linux_auditd_reduction_candidates.csv` documents review-required reduction thinking. Command arguments and file paths can be sensitive, but they are high-value audit and incident-reconstruction evidence and are retained by default.

## Known limitations

- No live Linux audit relay, SC4S runtime replay, HEC delivery, Splunk indexed read-back, or Manager apply evidence has been captured.
- Fixtures are synthetic-equivalent and documentation-shaped; they are not real production captures.
- Multi-record correlation is preserved by audit serial but not assembled by SC4S or Splunk props in this initial pack.
- Parser routes common audit record types represented by fixtures; AppArmor-specific denial shapes, audit daemon abort/rotate/resume records, audit backlog/lost-event health records, and distro-specific collector wrappers remain future work.
