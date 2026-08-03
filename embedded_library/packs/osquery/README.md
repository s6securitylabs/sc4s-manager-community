# osquery Result and Status Logs

Curated SecHub Resources pack for osquery result and status logs emitted as newline-delimited JSON and relayed to a dedicated SC4S listener. The scope is conservative and fixture-backed for differential result rows, snapshot result rows, status/error rows, process inventory results, listening-port inventory results, selected evented-table endpoint activity rows (`process_events`, `file_events`, and `socket_events`), hardware device change rows (`hardware_events`), user account inventory (`users`), logged-in user sessions (`logged_in_users`), scheduled task rows (`crontab`), SSH authorized-key inventory (`authorized_keys`), SUID binary inventory (`suid_bin`), and startup item inventory (`startup_items`).

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20085` with source tag `OSQUERY`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `osnix` / sourcetype(s) `osquery:results`, `osquery:status`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Evidence and provenance

Primary public evidence:

- osquery logging documentation: `https://osquery.readthedocs.io/en/stable/deployment/logging/` documents result logs, status logs, line-oriented logging, differential `added`/`removed` rows, snapshot rows, `name`, `hostIdentifier`, `calendarTime`, `unixTime`, `epoch`, `counter`, `action`, and `columns` fields.
- osquery schema/browser and official docs/source corroborate query-dependent table schemas and the fact that `columns` content depends on the scheduled query.
- Public osquery table specifications in the Apache-2.0 upstream repository document selected evented tables used by this pack: `process_events` (process execution path/cmdline/pid/uid context), `file_events` (target path/category/action/ownership/size context), and `socket_events` (bind/connect/accept, local/remote address and port context). These specs support conservative synthetic-equivalent fixture structure only; local event publisher/auditing configuration still requires validation.
- Public upstream osquery table specs also document `hardware_events`, `users`, `logged_in_users`, and `crontab` fields used in the current fixtures. These ground hardware/device, local account, active-login, and scheduled-task source shapes but do not prove that a local endpoint has those query packs enabled or that privacy handling is acceptable.
- Public upstream osquery table specs for `authorized_keys`, `suid_bin`, and `startup_items` document SSH authorized-key file, privileged executable, and startup-item fields used by this hardening pass. These support conservative synthetic-equivalent fixture structure only; local OS support, query scheduling, key-material handling, and privacy review remain deployment tasks.
- Parser ecosystem corroboration only: Elastic osquery integration, Wazuh osquery integration, and the Splunk Add-on for osquery show common operational handling for osquery result/status telemetry. No third-party parser or app code is copied into this pack.

Fixtures are synthetic-equivalent records shaped from public osquery logging documentation. They use `example.test` hostnames, documentation IP addresses, harmless process/port values, and explicit marker fields. No production hostnames, usernames, command lines, tenant identifiers, tokens, or customer data are included.

## Source shape

- **Delivery model:** one JSON object per line from osquery filesystem/TLS logging or a collector relay.
- **Wire/envelope:** fixture file is headerless NDJSON; helper script wraps each payload in an RFC5424-style line for the dedicated TCP listener. Production deployments may relay file logs through Fluent Bit, Vector, Cribl, syslog-ng, or another collector.
- **Timestamp:** osquery `calendarTime` is the documented human-readable source time. `unixTime` is preserved for audit/ordering. Local timezone and string formatting must be checked against the deployed osquery version and logger.
- **Event boundary:** one JSON object per line. Batched result lines, RocksDB buffering/replay effects, and query-specific nested columns remain local-validation concerns.
- **Default index/sourcetype:** `osnix` / `osquery:results` and `osquery:status`.

## Included event families

| Family | Evidence-backed fields | Notes |
| --- | --- | --- |
| `result_added` | `name`, `hostIdentifier`, `calendarTime`, `unixTime`, `epoch`, `counter`, `action=added`, `columns` | Differential result row for newly observed query output. |
| `result_removed` | same top-level result fields with `action=removed` | Differential removal row. |
| `snapshot` | `action=snapshot`, `columns` snapshot row/object context | Snapshot query output; local osquery version/options may alter shape. |
| `status` | `severity`, `filename`, `line`, `message`, host/time metadata | Operational osquery status/error log context. |
| `inventory` | result rows with query names such as process/listening-port inventory and query-dependent `columns` | Useful endpoint inventory context, not a complete endpoint telemetry model. |
| `endpoint_activity` | evented-table rows for `process_events`, `file_events`, and `socket_events` with `columns.path`, `columns.cmdline`, `columns.target_path`, `columns.local_address`, `columns.remote_address`, and port context where present | Public table specs ground the field names; local osquery event-publisher/audit configuration and OS-specific availability still require validation. |
| `hardware_change` | `hardware_events` rows with `columns.action`, `columns.path`, `columns.type`, `columns.driver`, `columns.vendor`, `columns.vendor_id`, `columns.model`, `columns.model_id`, `columns.serial`, `columns.revision`, and `columns.time` | Public osquery `hardware_events` table spec grounds field names for USB/PCI/HID-style add/remove/change telemetry; local UDEV/IOKit event publisher behavior still requires validation. |
| `user_account` | `users` rows with `columns.uid`, `columns.gid`, `columns.username`, `columns.directory`, `columns.shell`, and optional description | Public `users` table spec grounds local account inventory fields; this is not a complete identity inventory or password/audit validation. |
| `user_session` | `logged_in_users` rows with `columns.type`, `columns.user`, `columns.tty`, `columns.host`, `columns.time`, and `columns.pid` | Public `logged_in_users` table spec grounds active shell/session fields; local OS support and privacy handling need validation. |
| `scheduled_task` | `crontab` rows with schedule columns and `columns.command` / `columns.path` | Public `crontab` table spec grounds scheduled task command and schedule fields; command text is sensitive and retained by default for audit. |
| `ssh_authorized_key` | `authorized_keys` rows with `columns.uid`, `columns.algorithm`, `columns.options`, `columns.comment`, and `columns.key_file` | Public `authorized_keys` table spec grounds SSH key inventory fields. Fixtures use a placeholder key string; real key material/comments require local privacy review. |
| `suid_binary` | `suid_bin` rows with `columns.path`, `columns.username`, `columns.groupname`, and `columns.permissions` | Public `suid_bin` table spec grounds privileged executable inventory; not complete file-integrity validation. |
| `startup_item` | `startup_items` rows with `columns.name`, `columns.path`, `columns.args`, `columns.type`, `columns.source`, `columns.status`, and `columns.username` | Public `startup_items` table spec grounds autorun/startup item context; arguments may be sensitive and are retained by default for audit. |

## Splunk fields and validation SPL

Expected non-lossy fields after Splunk search-time extraction include:

```spl
index=osnix "SC4S_OSQUERY_TEST_" earliest=-2h
| table _time index sourcetype source vendor product osquery_log_type query_name hostIdentifier action severity status result process_name pid file_path cmdline uid local_address remote_address local_port remote_port port protocol hardware_action hardware_path hardware_type hardware_driver hardware_vendor hardware_vendor_id hardware_model hardware_model_id hardware_serial hardware_revision user_name user_home user_shell session_tty session_host session_time cron_schedule cron_command cron_path ssh_key_algorithm ssh_key_comment ssh_key_file ssh_key_options suid_path suid_owner suid_group suid_permissions startup_name startup_path startup_args startup_type startup_source startup_status startup_user marker _raw
```

The validation harness in `pack.json` uses the same read-back field set. It is a requirements only; it has not passed because no local SC4S/Splunk testbed was available in this run.

## Disposable E2E harness

`packs/osquery/scripts/e2e_docker_compose.sh` is an idempotent Docker/Compose harness requirements for a permitted lab run. `plan` and `write-compose` do not require Docker; `run` creates disposable Splunk TEST and SC4S TEST containers, creates `index=osnix`, replays all 15 fixture records through TCP `20085`, and runs summary/detail read-back SPL for the declared `osquery:results` and `osquery:status` sourcetypes.

Evidence boundary: a passing harness run would prove only the fixture-backed SC4S TEST -> Splunk TEST route for the one-line osquery JSON relay shape. It does not prove live endpoint osquery emission, deployed query-pack coverage, logger buffering/replay, filesystem/TLS logger configuration, collector wrapping, local OS event publisher behaviour, or privacy handling for command lines, hardware serials, SSH key comments, startup arguments, and user/session context. Trust remains `curated` / `unverified` until replay/read-back evidence is captured and reviewed.

## Splunk dashboard

`osquery_overview.xml` is a fixture-backed SimpleXML dashboard for first-pass onboarding and analyst triage. It intentionally uses only fields already proven by this pack's fixtures and Splunk JSON/search-time knowledge: `osquery_log_type`, `query_name`, `hostIdentifier`, `action`, `severity`, `status`, `result`, `process_name`, `pid`, `file_path`, `cmdline`, `uid`, `local_address`, `remote_address`, `local_port`, `remote_port`, `port`, `protocol`, `hardware_action`, `hardware_path`, `hardware_type`, `hardware_driver`, `hardware_vendor`, `hardware_vendor_id`, `hardware_model`, `hardware_model_id`, `hardware_serial`, `hardware_revision`, `user_name`, `user_home`, `user_shell`, `session_tty`, `session_host`, `session_time`, `cron_schedule`, `cron_command`, `cron_path`, `ssh_key_algorithm`, `ssh_key_comment`, `ssh_key_file`, `ssh_key_options`, `suid_path`, `suid_owner`, `suid_group`, `suid_permissions`, `startup_name`, `startup_path`, `startup_args`, `startup_type`, `startup_source`, `startup_status`, `startup_user`, `signature`, `signature_id`, `marker`, and preserved raw JSON.

Dashboard panels cover event volume over time, result/status distribution, top query names, endpoint coverage, process and listening-port inventory/change rows, evented process/file/socket activity, hardware device change context, local account/session/scheduled-task context, SSH authorized keys, SUID binaries, startup items, status/error messages, onboarding coverage, and recent raw-event context. The dashboard does not introduce new parser statements, does not prove osquery deployment completeness, and is not replay/read-back validation.

## Reduction posture

No default drops, null queues, lossy redaction, or field trimming are shipped. `docs/osquery_reduction_candidates.csv` is advisory only and covers review-required candidates such as noisy scheduled inventory queries, low-severity status chatter, and high-cardinality `columns` values. Any reduction must be enabled outside the basic/standard presets only after local replay/read-back proves event counts, query names, host identifiers, action/status fields, critical security query output, and rollback behavior.

## Current validation status

- Quality: `curated`.
- Trust: `unverified`.
- Local schema/fixture/pack validation: handled by repository CI.
- Live SC4S replay and Splunk indexed read-back: **not performed**.
- Blocked preflight evidence: `validation/preflight-2026-06-13.md` records that no local listener/Splunk TEST route was available in this repository run.

This pack must not be described as validated, S6 verified, field validated, or deployment-approved until replay/read-back evidence proves the intended route with real or production-equivalent osquery data.
