# Postfix / Dovecot mail syslog relay

Curated SecHub Resources SC4S pack for common Postfix MTA and Dovecot IMAP mail syslog records shipped through a dedicated listener. The initial pack covers fixture-backed Postfix delivery, postscreen/pre-queue rejection, cleanup/message-id, Dovecot IMAP login, Dovecot authentication failure, Dovecot logout/session-counter, and Dovecot mail-log-plugin session action records.

## Scope and posture

- Vendor/product: Postfix and Dovecot mail syslog.
- Intended source modes: syslog or file/collector relay preserving one physical mail log record per line.
- Current fixture shape: headerless RFC3164-style message payloads beginning with `Mon DD HH:MM:SS host program[pid]: ...` or `dovecot: ...`.
- Default index: `email`.
- Trust/quality: `curated` / `unverified`. This is not validated, S6 verified, field validated, or approved for deployment without local testing.

The pack routes only dedicated listener/source-tag traffic and explicit Postfix/Dovecot program tokens so it does not hijack generic Linux syslog or unrelated mail-gateway products.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20077` with source tag `POSTFIX_DOVECOT_MAIL`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `email` and sourcetype(s) `mail:postfix:delivery`, `mail:postfix:reject`, `mail:postfix:cleanup`, `mail:dovecot:login`, `mail:dovecot:auth_failure`, `mail:dovecot:logout`, and `mail:dovecot:session`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Evidence and provenance

The pack is grounded in the 2026-06-08 evidence scan at `docs/evidence/postfix-dovecot-mail-syslog-evidence-scan-20260608.md`:

- Postfix source/documentation mirror commit `b355ca0c47799c0564357d2b9f7b97f1f5a939a0` for program tokens and delivery/rejection structures.
- Dovecot documentation commit `1f87c243da22c6e1dc50472f6c2b937cdb6f91c7` for login-log format elements and mail-log-plugin structure.

Dovecot documentation is CC BY-NC-SA, so fixtures do not copy examples verbatim. They use synthetic-equivalent users, hosts, message IDs, queue IDs, session IDs, and RFC5737 documentation IP addresses.

## Event families

| Family | Sourcetype | Notes |
| --- | --- | --- |
| Postfix delivery | `mail:postfix:delivery` | Queue ID, recipient, relay, DSN, delay, and raw `status=sent` token. |
| Postfix reject | `mail:postfix:reject` | `NOQUEUE` postscreen/pre-queue connection rejection with source IP/port and reason. |
| Postfix cleanup | `mail:postfix:cleanup` | Queue/message-id context for mail traceability. |
| Dovecot login | `mail:dovecot:login` | User, auth method, `rip`, `lip`, mpid, TLS marker, and session ID. |
| Dovecot auth failure | `mail:dovecot:auth_failure` | `Disconnected: auth failed` login process row with user, method, remote/local IPs, TLS marker, and session ID. |
| Dovecot logout counters | `mail:dovecot:logout` | `Logged out` IMAP row with session byte/message counters from default `imap_logout_format` fields. |
| Dovecot mail-log action | `mail:dovecot:session` | Plugin-scoped mailbox action with user, UID, message ID, and mailbox. |

## Fixture semantics

`test-events/postfix_dovecot_mail_test_events.txt` contains seven synthetic-equivalent records. Each line is one complete headerless RFC3164-style payload with a unique marker:

- `SC4S_POSTFIX_DOVECOT_MAIL_TEST_POSTFIX_DELIVERY_001`
- `SC4S_POSTFIX_DOVECOT_MAIL_TEST_POSTFIX_REJECT_002`
- `SC4S_POSTFIX_DOVECOT_MAIL_TEST_POSTFIX_CLEANUP_003`
- `SC4S_POSTFIX_DOVECOT_MAIL_TEST_DOVECOT_LOGIN_004`
- `SC4S_POSTFIX_DOVECOT_MAIL_TEST_DOVECOT_MAILLOG_005`
- `SC4S_POSTFIX_DOVECOT_MAIL_TEST_DOVECOT_AUTH_FAILURE_006`
- `SC4S_POSTFIX_DOVECOT_MAIL_TEST_DOVECOT_LOGOUT_007`

The fixture file is intentionally headerless for repository validation. `scripts/send_tcp_20077.sh` wraps each line in an RFC5424 syslog envelope for the dedicated TCP listener. Fixture payload timestamps are RFC3164 month/day/time values without timezone or year; production relays should prefer timezone-qualified envelopes or document receiver-time assumptions.

## Validation harness

Current status: blocked preflight only. On 2026-06-08 this host had no listener on TCP 20077 and local Splunk TEST ports 8089/8000 refused connections. See `validation/preflight-2026-06-08.md`.

`./scripts/e2e_docker_compose.sh` now provides an idempotent disposable Splunk TEST + SC4S TEST harness requirements for this pack. Use `packs/postfix_dovecot_mail/scripts/e2e_docker_compose.sh plan` to inspect the required stages without Docker, or `... run` in a permitted lab to write a Compose file, start the test stack, create `index=email`, replay the seven fixture records through TCP `20077`, sample SC4S/syslog-ng counters, and run summary/detail Splunk read-back SPL. A passing harness run would be retained SC4S TEST -> Splunk TEST evidence for the fixture-backed source shapes only; it would still not prove live Postfix/Dovecot source-version emission, collector wrappers, source-local timezone handling, or field validation.

Validation SPL once a non-production SC4S/Splunk testbed is available:

```spl
index=email "SC4S_POSTFIX_DOVECOT_MAIL_TEST_" earliest=-2h
| table _time index sourcetype source vendor product program postfix_daemon dovecot_program queue_id action result vendor_raw_status vendor_raw_action recipient relay_host relay_ip src src_ip src_port rip lip user auth_method session uid message_id mailbox failure_reason logout_in_bytes logout_out_bytes deleted_count expunged_count hdr_count body_count marker _raw
```

Expected count: 7 events, with the seven sourcetypes listed above and no dropped markers. The README SPL intentionally matches `pack.json.validation_harness.readback.spl` so reviewers prove both Dovecot failure/logout counters and the core Postfix/Dovecot routing fields.

## Splunk dashboard

`splunk/default/data/ui/views/postfix_dovecot_mail_overview.xml` provides a fixture-backed onboarding and first-triage view for the seven covered mail syslog fixture rows. It includes event volume and sourcetype/family distribution, Postfix rejection and delivery counters, Dovecot login counts, top users/recipients and remote IPs, delivery/rejection triage tables, Dovecot mailbox-action review, queue/message/session traceability, source/host onboarding coverage, raw-event drilldown, and a manual validation SPL panel.

The dashboard uses only fields proven by `test-events/postfix_dovecot_mail_test_events.txt` and `splunk/default/props.conf`: `program`, `postfix_daemon`, `dovecot_program`, `queue_id`, `recipient`, `relay_host`, `relay_ip`, `dest_port`, `dsn`, `delay`, `vendor_raw_status`, `vendor_raw_action`, `result`, `action`, `reason`, `src_ip`/`src_port`, `rip`/`lip`, `user`, `auth_method`, `session`, `uid`, `message_id`, `mailbox`, `signature`, `signature_id`, `failure_reason`, `logout_in_bytes`, `logout_out_bytes`, `deleted_count`, `expunged_count`, `hdr_count`, `body_count`, and `marker`. It does not state live mail-server replay/read-back validation, Dovecot LMTP/auth-failure/logout variants, Postfix policy-service logs, spam/security gateway products, or exhaustive local deployment coverage.

## Reduction posture

No default drops, field deletion, null queues, or privacy transforms are shipped. `docs/postfix_dovecot_mail_reduction_candidates.csv` documents review-required candidates only. Mail users, recipients, message IDs, source IPs, sessions, queue IDs, and delivery status can be sensitive/noisy, but they are high-value incident-reconstruction evidence and are retained by default.

## Known limitations

- No live Postfix/Dovecot relay, SC4S runtime replay, HEC delivery, Splunk indexed read-back, or Manager apply evidence has been captured.
- Fixtures are synthetic-equivalent and documentation-shaped; they are not real production captures.
- Initial scope excludes Dovecot LMTP, Dovecot disconnect variants beyond the documented `auth failed` and `Logged out` shapes, Postfix policy-service request logs, SpamAssassin/Rspamd/Amavis/OpenDKIM/OpenDMARC, Exchange/Online, Proofpoint, Mimecast, and other gateway products.
- Dovecot mail-log-plugin rows are plugin-scoped and should not be assumed present on every Dovecot deployment.
