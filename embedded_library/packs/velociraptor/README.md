# Velociraptor endpoint and DFIR telemetry pack

Conservative SecHub Resources SC4S pack for Velociraptor JSON/JSONL monitoring, hunt-management, and artifact-result relay rows. Initial scope is intentionally limited to documented relay/export shapes and synthetic-equivalent fixtures.

This is curated intake guidance, not live Velociraptor validation. Trust remains `unverified` and quality remains `curated` until real Velociraptor relay replay and Splunk indexed read-back evidence exists.

## Evidence searched

- `docs/evidence/velociraptor-evidence-scan-20260608.md` records public Velocidex repository/docs references for client/server monitoring, upload artifacts, hunt list/result APIs, and JSONL watch/write semantics.
- Public evidence supports row-shaped JSON/JSONL relay with `Artifact`, `Hostname`, `ClientId`, timestamps, and hunt identifiers.
- The 2026-06-15 hardening pass used public Velociraptor artifact definitions for `Windows.Network.Netstat`, `Windows.System.Services`, `Windows.Detection.Yara.Process`, and `Windows.Forensics.Prefetch` to add concrete artifact-result fixtures for network-socket, service-inventory, and YARA process-hit triage.
- Arbitrary `hunt_results()` rows are artifact-specific; this pack preserves pass-through rows and only surfaces structured fields for cited artifact references.

## Scope

- Listener: dedicated TCP syslog example on port `20073` with source tag `VELOCIRAPTOR`.
- Payloads: one complete JSON object per line from Velociraptor monitoring/export/collector relay paths.
- Routed sourcetypes: `velociraptor:monitoring:json`, `velociraptor:hunt:json`, and `velociraptor:artifact:result:json`.
- Default index: `oswinsec`.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20073` with source tag `VELOCIRAPTOR`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `oswinsec` / sourcetype(s) `velociraptor:monitoring:json`, `velociraptor:hunt:json`, `velociraptor:artifact:result:json`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Fixture semantics

- File: `test-events/velociraptor_test_events.jsonl`.
- Format: JSONL, one event per physical line.
- Wire/envelope: headerless fixture payloads; `scripts/send_tcp_20073.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one JSON object per line; multiline result blobs, API pagination, and credentialed collection are out of scope.
- Timestamp: fixture `timestamp` values are UTC ISO-8601 strings where present; hunt list rows may use `Created` and otherwise fall back to receiver time.
- Markers: `SC4S_VELOCIRAPTOR_TEST_*` values each occur exactly once. Current fixtures include monitoring, hunt lifecycle, a generic artifact pass-through row, and concrete `Windows.Network.Netstat`, `Windows.System.Services`, `Windows.Detection.Yara.Process`, and `Windows.Forensics.Prefetch` artifact-result rows.
- Sanitisation: fixtures use example.test hostnames/users, synthetic client/hunt/flow IDs, and no customer/server exports.

Validation SPL smoke pattern:

```spl
index=oswinsec "SC4S_VELOCIRAPTOR_TEST_" earliest=-2h
| table _time index sourcetype source vendor product artifact Artifact client_id ClientId host Hostname user hunt_id HuntId flow_id FlowId Pid Name ProcessName Rule Executable ExecutablePath Hash RunCount PrefetchFileName ExecutionTime Laddr.IP Laddr.Port Raddr.IP Raddr.Port Status State StartMode PathName ExePath CommandLine action signature signature_id marker _raw
```

## Disposable SC4S TEST -> Splunk TEST harness

`packs/velociraptor/scripts/e2e_docker_compose.sh` defines an idempotent Docker/Compose lab harness for this pack. `plan` prints the required evidence stages without Docker; `write-compose` writes `.tmp/e2e/velociraptor/compose.yaml`; `run` starts disposable Splunk and SC4S containers, creates `index=oswinsec`, replays all eight Velociraptor JSONL fixtures through TCP `20073`, and executes summary/detail read-back SPL.

The harness is a runnable lab requirement, not validation evidence by itself. A passing run would prove only the synthetic-equivalent fixture path from SC4S TEST to Splunk TEST for the declared monitoring, hunt, artifact-result, Netstat, Services, YARA process, and Prefetch rows. It does not prove live Velociraptor server/client source-version emission, API or collector credential custody, pagination/checkpoint handling, export completeness, multiline/large artifact payload behavior, arbitrary `hunt_results()` schemas, HEC delivery in production, or field validation.

## Splunk dashboard

`packs/velociraptor/splunk/default/data/ui/views/velociraptor_overview.xml` provides a fixture-backed onboarding and first-triage overview for the three declared sourcetypes: `velociraptor:monitoring:json`, `velociraptor:hunt:json`, and `velociraptor:artifact:result:json`.

The dashboard is intentionally conservative. It covers arrival health, volume by sourcetype, artifact/action distribution, hunt/result state review, endpoint/client monitoring coverage, artifact-result flow context, source/sourcetype/host onboarding coverage, and raw JSON drilldown. Panels use only fields represented in `test-events/velociraptor_test_events.jsonl` and preserved or derived by `splunk/default/props.conf`, including `Artifact`, `artifact`, `ClientId`, `client_id`, `Hostname`, `host`, `User`/`Creator`, `hunt_id`/`HuntId`, `FlowId`, `flow_id`, `state`/`result`, `CPUPercent`, `MemoryRSS`, `ArtifactRow.*`, network socket fields (`Laddr.IP`, `Laddr.Port`, `Raddr.IP`, `Raddr.Port`, `Status`), service fields (`Name`, `State`, `StartMode`, `PathName`), YARA hit fields (`ProcessName`, `ExePath`, `Rule`, `YaraString`, `HitOffset`), Prefetch execution-history fields (`Executable`, `ExecutablePath`, `Hash`, `RunCount`, `PrefetchFileName`, `ExecutionTime`), `action`, `signature`, `signature_id`, and `marker`.

The dashboard does not prove complete Velociraptor artifact-result schemas, API collection/checkpoint coverage, multiline result handling, server/client export completeness, or SC4S/Splunk replay-readback validation. Trust remains `curated`/`unverified` until real Velociraptor relay replay and indexed Splunk read-back evidence is captured.

## Reduction stance

No event drops or field deletion are enabled by default. `docs/velociraptor_reduction_candidates.csv` lists advisory-only candidates for heartbeat/status noise, very large artifact payloads, and duplicate enrichment fields. Client identity, artifact name, hunt/flow IDs, timestamps, actor/user, host, result state, detection/artifact context, and raw row payload are risky to drop and must be retained by default.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-08.md` shows port `20073` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from public documentation/repository evidence, not real Velociraptor exports.
- Arbitrary artifact result rows remain pass-through unless a concrete artifact schema is cited; only `Windows.Network.Netstat`, `Windows.System.Services`, `Windows.Detection.Yara.Process`, and `Windows.Forensics.Prefetch` get structured artifact-result triage in this pass, and no universal Velociraptor hunt-result schema is published.
- Reduction candidates are advisory only and require local replay/read-back plus rollback review before enablement.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real Velociraptor relay replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, Artifact/client/hunt/flow identity, eventtypes/tags, and normalized fields.
