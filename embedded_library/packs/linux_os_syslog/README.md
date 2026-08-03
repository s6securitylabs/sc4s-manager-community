# Linux common OS syslog relay

Curated SecHub Resources SC4S pack for common Linux `/var/log` and syslog relay records shipped through a dedicated listener. The pack covers fixture-backed sshd authentication failure and success, sudo command execution, su/PAM session activity, cron job execution, kernel packet/warning context, systemd service stop/failure-style messages, PAM authentication failures, syslog-wrapped package-manager changes, and shadow-utils account/group lifecycle rows.

## Scope and posture

- Vendor/product: Linux common OS syslog.
- Intended source modes: rsyslog, syslog-ng, journald-to-syslog, file-agent, or collector relay preserving one physical syslog message per line.
- Current fixture shape: headerless RFC3164-style message payloads beginning with `Mon DD HH:MM:SS host program[pid]: ...`.
- Default index: `osnix`.
- Trust/quality: `curated` / `unverified`. This is not validated or S6 verified.

The pack is deliberately a broad OS telemetry foundation rather than a complete Unix/Linux TA replacement. It routes a small set of high-value common families through a dedicated listener/source tag so it does not hijack unrelated syslog.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20065` with source tag `LINUX_OS_SYSLOG`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `osnix` and sourcetype(s) `linux:os:auth:sshd`, `linux:os:auth:sudo`, `linux:os:cron`, `linux:os:kernel`, and 1 more declared sourcetype(s).

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Evidence and provenance

The fixture and required-field coverage are grounded in public Linux/OpenSSH/sudo/cron/systemd/kernel syslog conventions and common public parser expectations for Unix/Linux logs. Fixtures are synthetic-equivalent and use generic hosts, generic users, and RFC5737 documentation addresses. No customer records, tenant identifiers, secrets, or proprietary TA content are included.

Additional hardening used public OpenSSH source templates for accepted authentication messages, Linux-PAM source templates plus public examples for `su` session records and PAM authentication-failure templates, Debian/Red Hat public package-log documentation for package-change semantics, and shadow-utils public source templates for `useradd` / `groupadd` / `userdel` / `usermod` account lifecycle syslog rows. The committed package fixture is intentionally a syslog-wrapped synthetic-equivalent row; native dpkg/apt/yum file formats remain separate source-shape work until exact relay handling is added. See `docs/evidence/linux-os-syslog-evidence-scan-20260614.md`.

## Event families

| Family | Example program/source | Sourcetype | Notes |
| --- | --- | --- | --- |
| SSH authentication failure | `sshd` | `linux:os:auth:sshd` | Preserves failed password login source user/IP/port and sshd PID. |
| SSH authentication success | `sshd` | `linux:os:auth:sshd` | Preserves accepted public-key/password-style auth method, user, source IP/port, and sshd PID. |
| Sudo command | `sudo` | `linux:os:auth:sudo` | Preserves invoking user, target user, working directory, and command. |
| su/PAM session | `su` / `pam_unix` | `linux:os:auth:su` | Preserves PAM service, session open/close event, source/target users, and UIDs where emitted. |
| PAM authentication failure | `su` / `pam_unix(su:auth)` | `linux:os:auth:su` | Preserves failed PAM authentication logname, invoking/target users, UID/effective UID, TTY, and remote host where emitted. |
| Cron execution | `CRON` | `linux:os:cron` | Preserves scheduled user and command context. |
| Kernel warning | `kernel` | `linux:os:kernel` | Preserves kernel subsystem/message context; initial fixture covers firewall-style packet text. |
| Systemd service state | `systemd` | `linux:os:systemd` | Preserves service unit and state/action text for service triage. |
| Package-manager change | `apt`/`dpkg`/`yum`/`dnf`/`rpm` syslog wrapper | `linux:os:package` | Preserves package action/name/version/architecture when a collector relays package changes as syslog messages. |
| Account/group lifecycle | `useradd` / `groupadd` / `userdel` / `usermod` | `linux:os:account` | Preserves shadow-utils create/delete/change object name, UID/GID, home, shell, source command, changed attribute, and old/new values where emitted. |

## Fixture semantics

`test-events/linux_os_syslog_test_events.txt` contains thirteen synthetic-equivalent records. Each physical line is one complete headerless RFC3164-style payload with a unique marker:

- `SC4S_LINUX_OS_SYSLOG_TEST_SSHD_001`
- `SC4S_LINUX_OS_SYSLOG_TEST_SUDO_002`
- `SC4S_LINUX_OS_SYSLOG_TEST_CRON_003`
- `SC4S_LINUX_OS_SYSLOG_TEST_KERNEL_004`
- `SC4S_LINUX_OS_SYSLOG_TEST_SYSTEMD_005`
- `SC4S_LINUX_OS_SYSLOG_TEST_SSHD_SUCCESS_006`
- `SC4S_LINUX_OS_SYSLOG_TEST_SU_PAM_007`
- `SC4S_LINUX_OS_SYSLOG_TEST_PACKAGE_008`
- `SC4S_LINUX_OS_SYSLOG_TEST_PAM_AUTH_FAILURE_009`
- `SC4S_LINUX_OS_SYSLOG_TEST_USERADD_010`
- `SC4S_LINUX_OS_SYSLOG_TEST_GROUPADD_011`
- `SC4S_LINUX_OS_SYSLOG_TEST_USERDEL_012`
- `SC4S_LINUX_OS_SYSLOG_TEST_USERMOD_013`

The fixture file is intentionally headerless for repository validation. `scripts/send_tcp_20065.sh` wraps each line in an RFC5424 syslog envelope for the dedicated TCP listener. Fixture payload timestamps are RFC3164 month/day/time values without a timezone or year; production deployments should prefer a timezone-qualified relay envelope where available, otherwise Splunk/receiver-time policy must be documented.

## Validation harness

Current status: blocked preflight only. On 2026-06-07 this host had no listener on TCP 20065 and no local Splunk TEST management/web reachability. See `validation/preflight-2026-06-07.md`.

A disposable Docker/Compose harness is now provided for a future lab run:

```bash
packs/linux_os_syslog/scripts/e2e_docker_compose.sh plan
packs/linux_os_syslog/scripts/e2e_docker_compose.sh run
```

The harness writes an ephemeral compose file under `.tmp/e2e/linux_os_syslog/`, generates or accepts a Splunk HEC token at run time, creates/uses index `osnix`, replays all 13 fixture rows through TCP 20065, samples SC4S/syslog-ng counters, and runs summary/detail Splunk read-back SPL. It requires a live `syslog-ng` process, usable control socket, TCP 20065 listener, Splunk management and HEC health endpoints, and exactly 13 indexed fixture markers. Empty or partial read-back fails the run. The disposable Splunk app mount is writable only so the TEST container can complete first-boot ownership setup. A passing run would be SC4S TEST -> Splunk TEST fixture replay/read-back evidence for the declared source shapes only; it would still not be field validation or production readiness without retained evidence and source-version review.

Validation SPL once a non-production SC4S/Splunk testbed is available:

```spl
index=osnix "SC4S_LINUX_OS_SYSLOG_TEST_" earliest=-2h
| table _time index sourcetype source vendor product program process_id action signature signature_id result user auth_method src src_ip src_port dest_user pam_service pam_event pam_logname effective_uid terminal ruser rhost user_uid dest_user_uid package_action package_name package_version package_arch account_action account_name account_uid account_gid account_home account_shell account_source account_attribute account_old_value account_new_value dest_port transport service command marker _raw
```

Expected count: 13 events, with the declared sourcetypes listed above and no dropped markers.

## Dashboard scope

`linux_os_syslog_overview.xml` is a fixture-backed Splunk SimpleXML overview for onboarding and first triage across the thirteen covered Linux OS syslog source rows. It includes data-arrival health, event-family distribution, SSH success/failure counters, sudo/cron command context, su/PAM session and authentication-failure review, package-change and account/group lifecycle triage, kernel packet/warning context, systemd service state review, source/sourcetype/host coverage, and recent raw-event drilldown.

The dashboard only uses fields proven by `test-events/linux_os_syslog_test_events.txt` and `splunk/default/props.conf`: `program`, `process_id`, `action`, `result`, `auth_method`, `user`, `dest_user`, `user_uid`, `dest_user_uid`, `pam_service`, `pam_event`, `pam_logname`, `effective_uid`, `ruser`, `rhost`, `src_ip`, `src_port`, `dest_ip`, `dest_port`, `transport`, `terminal`, `working_directory`, `command`, `service`, `service_message`, `package_action`, `package_name`, `package_version`, `package_arch`, `account_action`, `account_name`, `account_uid`, `account_gid`, `account_home`, `account_shell`, `account_source`, `account_attribute`, `account_old_value`, `account_new_value`, `signature`, `signature_id`, and `marker`. It does not state coverage for PAM modules beyond the documented `su` session/auth-failure examples, shadow-utils account lifecycle rows beyond the fixture-backed `useradd`/`groupadd`/`userdel`/`usermod` examples, native non-syslog `/var/log/dpkg.log` or `apt history.log` file formats, journald JSON, distro-specific wrappers, multiline application logs, or live replay/read-back validation.

## Reduction posture

No default drops, field deletion, null queues, or privacy transforms are shipped. `docs/linux_os_syslog_reduction_candidates.csv` documents review-required reduction thinking. Command lines, user identifiers, process IDs, service names, source IPs/ports, and kernel packet context can be sensitive/noisy, but they are high-value incident-reconstruction evidence and are retained by default.

## Known limitations

- No live Linux syslog relay, SC4S runtime replay, HEC delivery, Splunk indexed read-back, or Manager apply evidence has been captured.
- Fixtures are synthetic-equivalent and documentation-shaped; they are not real production captures.
- Initial parser routes selected common families only; PAM modules beyond the documented `su` session/auth-failure examples, broader shadow-utils variants beyond the fixture-backed create/delete/shell-change rows, native non-syslog package log files, journald JSON, distro-specific secure/auth variants, and multiline application logs remain future work.
- RFC3164 payload timestamps have no timezone/year; production operators should prefer timezone-qualified relay envelopes or document receiver-time assumptions.
