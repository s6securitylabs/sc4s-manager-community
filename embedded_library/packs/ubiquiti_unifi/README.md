# Ubiquiti UniFi network telemetry pack

Comprehensive SecHub Resources SC4S pack for Ubiquiti UniFi network telemetry. Scope covers UniFi network/application syslog-style events for firewall, clients, admin activity, devices, threat/security detections, and VPN/session context with dedicated routing, Splunk props/transforms/eventtypes/tags, an operator dashboard, synthetic-equivalent fixtures, a send helper, reduction guidance, and a validation harness with S6 lab replay/read-back evidence for the fixture route.

Trust is `s6_verified` and quality is `validated` for the 2026-06-14 S6 lab SC4S TEST -> Splunk TEST replay/read-back of the synthetic-equivalent fixture set. It is not `field_validated`; real UniFi product/source-version telemetry or vendor-certified equivalent is still required for field validation.

## Scope

- Listener: dedicated TCP syslog example on port `20086` with source tag `UBIQUITI_UNIFI`.
- Payloads: one event per line; collector wrappers should be normalized before SC4S where practical.
- Routed sourcetypes: `ubiquiti:unifi:firewall`, `ubiquiti:unifi:client`, `ubiquiti:unifi:admin`, `ubiquiti:unifi:device`, `ubiquiti:unifi:threat`, `ubiquiti:unifi:vpn`.
- Default index: `netops`.
- Dashboard: `splunk/default/data/ui/views/unifi_overview.xml`.

## Ingestion and collection notes

Typical ingestion is **syslog, journald/file collector relay, or appliance/controller forwarding** into the dedicated TCP listener. API/export/ZIP/TGZ paths may be useful for historical pull-based collection, but this pack assumes operational log records are split to one event per line before SC4S. Collector credentials and checkpoints belong to the relay/collector layer, not SC4S.

Safe ingestion-time manipulation is limited to envelope normalization, archive decompression, record splitting, host/source correction, timestamp preservation, source tagging, and default index/sourcetype routing. Keep raw operational/security context by default; any lossy redaction, suppression, or field removal must be optional, documented, and validated with replay/read-back.

## Fixture semantics

- File: `test-events/unifi_test_events.txt`.
- Event count: 6.
- Event splitting: one event per line; multiline and collector-specific wrapper formats are out of scope.
- Markers: `SC4S_UNIFI_TEST_*` values each occur exactly once.
- Sanitisation: synthetic-equivalent values only; no customer logs, public secrets, or production endpoints.

Validation SPL smoke pattern:

```spl
index=netops "SC4S_UNIFI_TEST_" earliest=-2h
| table _time index sourcetype source vendor product host action result status marker _raw
```

## Dashboard coverage

The dashboard is a SOC/operator triage surface. It was XML-read-back in Splunk TEST during `validation/replay-readback-2026-06-14.md`, but dashboard availability is not field validation or production readiness. Local searches should still be tuned after real UniFi data is observed.

## Disposable E2E replay/read-back harness

`packs/ubiquiti_unifi/scripts/e2e_docker_compose.sh` provides a rerunnable Docker/Compose SC4S TEST -> Splunk TEST path for the existing synthetic-equivalent fixture set:

```bash
packs/ubiquiti_unifi/scripts/e2e_docker_compose.sh plan
packs/ubiquiti_unifi/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/ubiquiti_unifi/compose.yaml`, starts disposable Splunk and SC4S containers, creates `index=netops`, replays all six fixture rows through the TCP `UBIQUITI_UNIFI` listener on port `20086`, samples SC4S/syslog-ng movement, and fails closed unless all six `SC4S_UNIFI_TEST_` markers index with the expected UniFi sourcetypes. Passing this harness is pack-aware replay/read-back evidence for the fixture route only; it is not field validation for real UniFi controllers/appliances, product versions, collector wrappers, API/export/archive paths, production source-local timezone behavior, or trust promotion.

## Reduction stance

No event drops or field deletion are enabled by default. `docs/unifi_reduction_candidates.csv` is advisory only. Preserve actor, host/device, result/status, identifiers, and raw message context by default.

## Known limitations

- S6 lab replay/read-back evidence in `validation/replay-readback-2026-06-14.md` captured 6/6 synthetic-equivalent fixture events through TCP `20086` into Splunk TEST index `netops` with expected UniFi sourcetypes; historical blocked preflight evidence remains in `validation/preflight-2026-06-14.md`.
- Fixtures are synthetic-equivalent and conservative; exact product versions, collector envelopes, API/export modes, and local timestamp behavior need site validation.
- Dashboard panels may need local tuning once real sourcetypes, volume, and field extractions are observed.

## Promotion gate

Do not promote this pack to `field_validated` / `field_verified` from CI/schema success or synthetic fixture replay alone. Field validation still requires real UniFi product/source-version telemetry or vendor-certified equivalent plus retained read-back proving count, index, sourcetype, source, timestamps, event family fields, eventtypes/tags, dashboard searches, normalized fields, and production sender attribution.
