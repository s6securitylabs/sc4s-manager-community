# Proxmox VE control-plane pack

Conservative SecHub Resources SC4S pack for Proxmox VE control-plane syslog/task telemetry. Initial scope is intentionally narrow: authentication success/failure, service lifecycle task lines, and node/task summary lines with UPID context where public source evidence supports the emitted message shape.

This pack now has S6 lab SC4S TEST -> Splunk TEST replay/read-back evidence for the synthetic-equivalent fixture set. Trust is `s6_verified` and quality is `validated` for that lab route only; it is not `field_validated` because no real Proxmox product/source-version telemetry has been retained.

## Evidence searched

- `docs/evidence/proxmox-evidence-scan-20260608.md` records reachable Proxmox VE/PBS public docs plus source references for realm-qualified users, authentication messages, service task messages, task IDs/UPIDs, and node task summary messages.
- Initial fixtures use synthetic-equivalent values derived from documented/source-observed structure only.
- Proxmox Backup Server, HA/quorum, migration, storage/network changes, firewall logs, collector JSON wrappers, and broad VM/CT lifecycle parsing remain deferred until exact emitted-record evidence or a testbed is available.

## Scope

- Listener: dedicated TCP syslog example on port `20074` with source tag `PROXMOX`.
- Payloads: one Proxmox syslog/journal relay message per line.
- Routed sourcetypes: `proxmox:ve:auth`, `proxmox:ve:service:task`, and `proxmox:ve:task:summary`.
- Default index: `infraops`.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20074` with source tag `PROXMOX`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `infraops` and sourcetype(s) `proxmox:ve:auth`, `proxmox:ve:service:task`, `proxmox:ve:task:summary`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Fixture semantics

- File: `test-events/proxmox_test_events.txt`.
- Format: raw syslog payload lines with synthetic Proxmox program/message bodies.
- Wire/envelope: headerless fixture payloads; `scripts/send_tcp_20074.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per physical line; multiline journal entries, task logs fetched through the API, and collector JSON wrappers are out of scope.
- Timestamp: fixtures use UTC ISO-8601 timestamps with `Z`; production relays should preserve timezone-qualified syslog/journal time or document receiver-time fallback.
- Markers: `SC4S_PROXMOX_TEST_*` values each occur exactly once.
- Sanitisation: fixtures use example users/domains, RFC5737 addresses, and synthetic UPIDs/nodes only.

Validation SPL smoke pattern:

```spl
index=infraops "SC4S_PROXMOX_TEST_" earliest=-2h
| table _time index sourcetype source vendor product host process process_id user src_ip action result service upid proxmox_node task_type task_object signature signature_id marker _raw
```

## Disposable E2E harness

`pack.json` references `scripts/e2e_docker_compose.sh` as an idempotent Docker/Compose harness for disposable SC4S TEST -> Splunk TEST replay/read-back. Use:

```bash
packs/proxmox/scripts/e2e_docker_compose.sh plan
packs/proxmox/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/proxmox/compose.yaml`, generates or accepts an ephemeral Splunk HEC token at run time, mounts this pack's SC4S parser and Splunk knowledge, creates/preflights index `infraops`, replays all six fixture rows through TCP listener `20074`, samples SC4S/syslog-ng counters, and runs Splunk read-back SPL for `SC4S_PROXMOX_TEST_` markers.

A passing harness run would be route-local replay/read-back evidence for the declared synthetic-equivalent Proxmox VE fixture shapes only. It does not prove PBS, HA/quorum, VM/CT lifecycle, migration, storage/network/firewall, collector-wrapper, or field-validation scope without retained real product/source-version evidence.

## Reduction stance

No event drops or field deletion are enabled by default. `docs/proxmox_reduction_candidates.csv` lists advisory-only candidates for repetitive task progress and benign service-health chatter. Authentication, admin/service actions, UPIDs, node, user/realm, task object/VMID where present, result/failure text, and raw message payload are risky to drop and must be retained by default.

## Known limitations

- Quality is `validated` and trust is `s6_verified` based on `validation/replay-readback-2026-06-14.md`, which captured 6/6 synthetic-equivalent fixture events through the dedicated TCP `20074` SC4S TEST listener and Splunk TEST indexed read-back.
- Historical blocked preflight evidence remains in `validation/preflight-2026-06-08.md`; it is superseded for the current lab route by the 2026-06-14 replay/read-back evidence.
- Fixtures are synthetic-equivalent examples shaped from public Proxmox docs/source evidence, not real tenant or appliance exports.
- PBS backup/restore/datastore tasks, HA/quorum, migration, storage/network/firewall changes, and collector wrapper variants remain deferred.
- Reduction candidates are advisory only and require local replay/read-back plus rollback review before enablement.

## Promotion gate

Do not promote this pack to `field_validated` / `field_verified` from CI/schema success or synthetic fixture replay alone. Field validation still requires real Proxmox product/source-version telemetry or vendor-certified equivalent plus retained Splunk read-back proving count, index, sourcetype, source, timestamps, auth/task/UPID fields, eventtypes/tags, normalized fields, and production sender attribution.
