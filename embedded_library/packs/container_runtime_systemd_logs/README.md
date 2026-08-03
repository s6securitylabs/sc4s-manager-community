# Docker/container runtime and systemd service pack

Conservative SecHub Resources SC4S pack for container runtime and systemd/journald relay records. Initial scope covers Docker `json-file` container log JSON records, Kubernetes/CRI-style runtime log lines, Docker Engine event JSON records, systemd/journald service JSON records, and Docker journald-driver container metadata records.

This is curated intake guidance, not live Docker/containerd/systemd validation. Trust remains `unverified` and quality remains `curated` until real runtime relay replay and Splunk indexed read-back evidence exists.

## Evidence searched

- `docs/evidence/docker-container-systemd-evidence-scan-20260608.md` records reachable Docker, Kubernetes/CRI, systemd/journald, Splunk, Elastic, Fluent Bit, Vector, and Logstash evidence.
- Docker `json-file`, Docker Engine events, CRI log lines, and journald field names are public enough for synthetic-equivalent fixtures.
- Docker syslog-driver exact serialization, Docker journald-driver full record shape, daemon-message text, collector wrapper enrichment, and live replay/read-back remain future work.

## Scope

- Listener: dedicated TCP syslog example on port `20080` with source tag `CONTAINER_RUNTIME_SYSTEMD`.
- Payloads: one record per line. Some records are JSON, CRI records are raw text lines.
- Routed sourcetypes: `docker:container:json_file`, `container:cri:runtime`, `docker:engine:event`, `systemd:journald:service`, and `docker:journald:container`.
- Default index: `osnix`.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20080` with source tag `CONTAINER_RUNTIME_SYSTEMD`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `osnix` and sourcetype(s) `docker:container:json_file`, `container:cri:runtime`, `docker:engine:event`, `systemd:journald:service`, and 1 more declared sourcetype(s).

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Dashboard scope

The pack includes `splunk/default/data/ui/views/container_runtime_systemd_logs_overview.xml`, a fixture-backed onboarding and first-triage dashboard for the currently declared source shapes:

- Docker `json-file` stdout/stderr records (`docker:container:json_file`) with stream, message/container-log, and error/stderr review.
- CRI stdout/stderr runtime lines (`container:cri:runtime`) with stream, `F`/`P` flag, message, source-mode coverage, and a partial-fragment triage eventtype. Partial records are preserved as individual records; this pack does not stitch multi-fragment messages.
- Docker Engine lifecycle event JSON (`docker:engine:event`) with event type/action and container/image context where the fixture and props expose it.
- systemd/journald service JSON (`systemd:journald:service`) with service unit, program, severity, host, and message context.
- Docker journald-driver container metadata records (`docker:journald:container`) with container ID/name, image name, stream, host, and raw message context.

Dashboard panels cover data-arrival health, sourcetype/source-mode distribution, stderr/error counters, Docker lifecycle events, journald service/container context, onboarding coverage by source/host, and raw event drilldown. Panels intentionally use only fields grounded in the synthetic-equivalent fixtures and `splunk/default/props.conf` (`vendor`, `product`, `stream`, `cri_flag`, `event_type`, `action`, `container_id`, `container_name`, `image_name`, `service_unit`, `program`, `severity`, `message`, `container_log`, `signature`, `signature_id`, and `marker_family`). The dashboard does not state coverage for Docker syslog-driver serialization, complete journald-driver export shapes, daemon/containerd text variants, partial CRI-line stitching, Kubernetes pod metadata enrichment, Docker Compose labels, CRI-O variants, collector wrappers, or live replay/read-back validation.

## Fixture semantics

- File: `test-events/container_runtime_systemd_logs_test_events.txt`.
- Format: mixed custom application payloads, one event per line.
- Wire/envelope: headerless fixture payloads; `scripts/send_tcp_20080.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per physical line. CRI `P` partial fragments are preserved with `cri_flag=P`; multiline application-log reassembly, CRI fragment stitching, and stack-trace reconstruction are out of scope until collector/runtime replay evidence exists.
- Timestamp policy: Docker JSON and CRI fixtures include RFC3339Nano UTC timestamps; journald JSON fixtures include `__REALTIME_TIMESTAMP` microsecond epoch-style fields.
- Delimiting: JSON object per line for Docker/journald/event records; CRI records use `<timestamp> <stream> <flags> <message>`.
- Markers: `SC4S_CONTAINER_RUNTIME_SYSTEMD_TEST_*` values each occur exactly once; the fixture currently has 9 records including one Kubernetes/CRI partial-line row grounded in the public CRI log-line flag documentation.
- Sanitisation: fixtures use example domains, synthetic IDs, RFC-safe hostnames, and non-customer values only.

Validation SPL smoke pattern:

```spl
index=osnix "SC4S_CONTAINER_RUNTIME_SYSTEMD_TEST_" earliest=-2h
| table _time index sourcetype source vendor product stream cri_flag event_type action container_id container_name image_name service_unit program severity message signature signature_id marker_family _raw
```

## Disposable E2E harness requirements

`scripts/e2e_docker_compose.sh` now provides an idempotent Docker/Compose harness requirements for a disposable SC4S TEST -> Splunk TEST run. Use `packs/container_runtime_systemd_logs/scripts/e2e_docker_compose.sh plan` to review the exact stages without Docker, or `... run` in a permitted lab to write `.tmp/e2e/container_runtime_systemd_logs/compose.yaml`, start Splunk and SC4S containers, create/search `index=osnix`, replay all 9 fixture records through TCP `20080`, and run summary/detail read-back SPL.

A passing harness run would prove only fixture-backed replay/read-back for the declared Docker `json-file`, CRI runtime, Docker Engine event, systemd/journald service, and Docker journald-driver metadata relay shapes. It still does not prove real Docker/containerd/Kubernetes/systemd output, collector wrapper enrichment, Docker syslog-driver serialization, Docker journald-driver completeness, daemon-message text variants, CRI multiline/partial reassembly, production readiness, or field validation.

## Reduction stance

No event drops or field deletion are enabled by default. `docs/container_runtime_systemd_logs_reduction_candidates.csv` lists advisory-only candidates for high-volume successful container stdout, repetitive service health chatter, and known low-value status lines. Container stderr/errors, Docker Engine lifecycle events, container/image identity, service units, host context, request/correlation markers, and raw payloads are retained by default because they are needed for incident reconstruction and audit challenge.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-08.md` shows port `20080` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from public documentation and parser ecosystem evidence, not real host/container exports.
- Docker syslog-driver exact serialization, Docker journald-driver complete export shape, Docker daemon/containerd daemon text variants, CRI partial-line stitching/reassembly beyond preserving the `P` flag, Kubernetes pod metadata enrichment, Docker Compose labels, CRI-O variants, and collector wrappers remain deferred.
- Reduction candidates are advisory only and require local replay/read-back plus rollback review before enablement.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires a non-production Docker/containerd/systemd testbed, replay through the intended listener, and Splunk indexed read-back proving count, index, sourcetype, source, timestamps, source-mode separation, container/service identity fields, eventtypes/tags, and normalized fields.
