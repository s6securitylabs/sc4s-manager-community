# TrueNAS storage platform telemetry pack

Comprehensive SecHub Resources SC4S pack for TrueNAS storage platform telemetry. Scope covers TrueNAS middleware, storage health, snapshot, replication, disk/SMART, and host authentication syslog-style records with dedicated routing, Splunk props/transforms/eventtypes/tags, an operator dashboard, synthetic-equivalent fixtures, a send helper, reduction guidance, and a validation harness with S6 lab replay/read-back evidence for the fixture route.

Trust is `s6_verified` and quality is `validated` for the 2026-06-14 S6 lab SC4S TEST -> Splunk TEST replay/read-back of the synthetic-equivalent fixture set. It is not `field_validated`; real TrueNAS product/source-version telemetry or vendor-certified equivalent is still required for field validation.

## Scope

- Listener: dedicated TCP syslog example on port `20087` with source tag `TRUENAS`.
- Payloads: one event per line; collector wrappers should be normalized before SC4S where practical.
- Routed sourcetypes: `truenas:middleware:auth`, `truenas:storage:pool`, `truenas:storage:snapshot`, `truenas:hardware:disk`, `truenas:replication`, `truenas:host:auth`.
- Default index: `infraops`.
- Dashboard: `splunk/default/data/ui/views/truenas_overview.xml`.

## Ingestion and collection notes

Typical ingestion is **syslog, journald/file collector relay, or appliance/controller forwarding** into the dedicated TCP listener. API/export/ZIP/TGZ paths may be useful for historical pull-based collection, but this pack assumes operational log records are split to one event per line before SC4S. Collector credentials and checkpoints belong to the relay/collector layer, not SC4S.

Safe ingestion-time manipulation is limited to envelope normalization, archive decompression, record splitting, host/source correction, timestamp preservation, source tagging, and default index/sourcetype routing. Keep raw operational/security context by default; any lossy redaction, suppression, or field removal must be optional, documented, and validated with replay/read-back.

## Fixture semantics

- File: `test-events/truenas_test_events.txt`.
- Event count: 6.
- Event splitting: one event per line; multiline and collector-specific wrapper formats are out of scope.
- Markers: `SC4S_TRUENAS_TEST_*` values each occur exactly once.
- Sanitisation: synthetic-equivalent values only; no customer logs, public secrets, or production endpoints.

Validation SPL smoke pattern:

```spl
index=infraops "SC4S_TRUENAS_TEST_" earliest=-2h
| table _time index sourcetype source vendor product host action result status marker _raw
```

## Dashboard coverage

The dashboard is a SOC/operator triage surface. It was XML-read-back in Splunk TEST during `validation/replay-readback-2026-06-14.md`, but dashboard availability is not field validation or production readiness. Local searches should still be tuned after real TrueNAS data is observed.

## Disposable E2E harness

`packs/truenas/scripts/e2e_docker_compose.sh` provides an idempotent Docker/Compose path for refreshed pack-aware SC4S TEST -> Splunk TEST evidence. It writes `.tmp/e2e/truenas/compose.yaml`, starts disposable Splunk and SC4S containers, creates `index=infraops`, replays all six fixture rows through the dedicated TCP `TRUENAS` listener on port `20087`, samples SC4S/syslog-ng movement, and fails closed unless Splunk read-back returns all six `SC4S_TRUENAS_TEST_` markers.

Useful commands:

```bash
packs/truenas/scripts/e2e_docker_compose.sh plan
packs/truenas/scripts/e2e_docker_compose.sh run
packs/truenas/scripts/e2e_docker_compose.sh down
```

A passing disposable harness run is replay/read-back evidence for the fixture-backed source shapes only. It is not field validation for real TrueNAS appliances, product versions, collector wrappers, API/export/archive paths, or production routing.

## Reduction stance

No event drops or field deletion are enabled by default. `docs/truenas_reduction_candidates.csv` is advisory only. Preserve actor, host/device, result/status, identifiers, and raw message context by default.

## Known limitations

- S6 lab replay/read-back evidence in `validation/replay-readback-2026-06-14.md` captured 6/6 synthetic-equivalent fixture events through TCP `20087` into Splunk TEST index `infraops` with expected TrueNAS sourcetypes; historical blocked preflight evidence remains in `validation/preflight-2026-06-14.md`.
- Fixtures are synthetic-equivalent and conservative; exact product versions, collector envelopes, API/export modes, and local timestamp behavior need site validation.
- Dashboard panels may need local tuning once real sourcetypes, volume, and field extractions are observed.

## Promotion gate

Do not promote this pack to `field_validated` / `field_verified` from CI/schema success or synthetic fixture replay alone. Field validation still requires real TrueNAS product/source-version telemetry or vendor-certified equivalent plus retained read-back proving count, index, sourcetype, source, timestamps, event family fields, eventtypes/tags, dashboard searches, normalized fields, and production sender attribution.
