# Kubernetes Audit pack

Conservative SecHub Resources SC4S pack for Kubernetes API server audit events (`audit.k8s.io/v1`) relayed one JSON event per line through a dedicated SC4S listener.

This pack is for Kubernetes control-plane audit intake, not Kubernetes validation. It preserves full audit records, routes fixture-backed high-value families, and exposes durable analyst fields while keeping trust `curated`/`unverified` until real cluster audit replay/read-back evidence exists.

## Evidence searched

- Kubernetes documentation: Auditing, audit policy, audit event stages and metadata.
- Kubernetes audit API source/API reference for audit event shape (`audit.k8s.io/v1 Event`), including `impersonatedUser`, `objectRef`, request/response status, timestamps, and annotations.
- Kubernetes TokenRequest API and service-account administration documentation for the service-account token request source shape.
- Hardening evidence note: `docs/evidence/kubernetes-audit-hardening-20260615.md`.
- Common SOC requirements for Kubernetes audit logs: RBAC changes, secret/configmap access, workload changes, pod exec, impersonation, service-account token issuance, and authorization failures.

## Scope

- Listener: dedicated TCP syslog example on port `20069` with source tag `KUBERNETES_AUDIT`.
- Payloads: newline-delimited Kubernetes audit JSON records; relay wrappers may be headerless or syslog-wrapped.
- Routed families: RBAC changes, secret access, workload changes, pod exec subresource usage, impersonated API requests, service-account token requests, and authorization failures.
- Default index: `main` until an environment-specific Kubernetes/security index is selected.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20069` with source tag `KUBERNETES_AUDIT`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `main` / sourcetype(s) `kubernetes:audit`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Fixture semantics

- File: `test-events/kubernetes_audit_test_events.txt`.
- Format: one compact JSON audit event per line.
- Wire/envelope: fixture file is headerless application payload; `scripts/send_tcp_20069.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; no multiline records.
- Timestamp: `requestReceivedTimestamp` is the primary UTC timestamp; `stageTimestamp` is retained as event-stage context.
- Markers: `SC4S_KUBERNETES_AUDIT_TEST_*` values each occur exactly once.
- Fixtures use reserved/example users and documentation IP ranges only; no cluster, tenant, or customer data is present.

Validation SPL smoke pattern:

```spl
index=main "SC4S_KUBERNETES_AUDIT_TEST_" earliest=-2h
| table _time index sourcetype source vendor product kubernetes_audit_family kubernetes_namespace kubernetes_resource kubernetes_resource_name kubernetes_subresource user impersonated_user user_agent src_ip action status response_code authorization_decision audit_stage audit_level signature signature_id request_kind token_audience token_expiration_seconds bound_object_kind bound_object_name marker eventtype _raw
```

## Dashboard scope

The Splunk dashboard at `splunk/default/data/ui/views/kubernetes_audit_overview.xml` is a fixture-backed onboarding and first-triage view for the currently declared Kubernetes audit families: RBAC changes, secret access, workload changes, pod exec requests, impersonated API requests, service-account token requests, and authorization denials. It uses only fields preserved by the synthetic-equivalent fixtures and `props.conf`: `kubernetes_audit_family`, actor/user, impersonated user, user agent, source IP, action/verb, status, response code, authorization decision, audit stage/level, namespace/resource/name/subresource, TokenRequest metadata where audit policy captures it, audit ID, request URI, marker, and raw JSON context.

The dashboard is intentionally conservative. It does not prove complete Kubernetes audit policy coverage, kubelet/container runtime telemetry, admission-controller detail, service-account token value capture, cloud-managed Kubernetes wrapper schemas, collector health/checkpointing, or replay/read-back validation. Add panels for additional audit families only after fixture/schema coverage and Splunk extraction logic prove the fields.

## Disposable E2E harness

An idempotent disposable Docker/Compose harness is included at `scripts/e2e_docker_compose.sh` for a future lab run. Use `packs/kubernetes_audit/scripts/e2e_docker_compose.sh plan` to review the planned Splunk TEST + SC4S TEST stages without Docker, or `run` to create the stack, replay all 7 fixtures through TCP/20069, sample SC4S counters, and query Splunk for the expected Kubernetes audit fields. A passing run would be fixture-scope SC4S TEST -> Splunk TEST evidence only; it would not prove a live Kubernetes cluster, audit-policy completeness, webhook backend behavior, cloud-managed audit wrappers, collector envelope/checkpointing, or field validation.

## Reduction stance

No event drops or field deletions are enabled by default. `docs/kubernetes_audit_reduction_candidates.csv` lists advisory candidates only. Actor identity, groups, source IPs, verb/action, request URI, object reference, namespace, resource, subresource, response status, authorization decision, user agent, and timestamps are retained by default because Kubernetes incident reconstruction depends on the API actor/object/action chain.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-07.md` shows port `20069` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from public Kubernetes audit schemas; they are not real cluster records.
- Collector wrappers may nest records or alter timestamp/source fields; compare local delivery output before promotion.
- Audit policy level affects payload detail; this pack starts with high-value metadata/request examples and does not prove complete Kubernetes audit coverage.
- Service-account TokenRequest coverage preserves audit metadata only; fixtures and public artifacts must never contain issued bearer tokens.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real Kubernetes audit relay replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, namespace/resource/subresource identity, actor/source IP, action/status semantics, eventtypes/tags, and normalized fields.
