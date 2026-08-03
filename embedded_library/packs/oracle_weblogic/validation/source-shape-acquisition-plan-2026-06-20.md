# Oracle WebLogic source-shape acquisition plan — 2026-06-20

## Purpose

This note turns the current Oracle WebLogic catalogue-only blocker into a concrete evidence-acquisition checklist. It is not validation evidence, does not contain Oracle event samples, and must not be used to promote `quality_status`, `trust_level`, `review_status`, or downloadability.

The `oracle_weblogic` pack remains routing-disabled and catalogue-only until one variant has exact emitted-record evidence, safe fixtures, and replay/read-back or collector read-back.

## Public evidence reviewed

- Oracle WebLogic Server 14.1.2 logging services documentation: `https://docs.oracle.com/en/middleware/fusion-middleware/weblogic-server/14.1.2/wllog/logging_services.html`.
  - Retrieved 2026-06-20 during this maintenance run.
  - Supports structural planning for server logs: Oracle states that the first line of each server log message begins with `####`, followed by message attributes contained between angle brackets.
  - Also confirms WebLogic HTTP access logs are text files and that access log behavior can be configured per server or virtual host.
- Oracle WebLogic Server 12.2.1.3 log configuration documentation: `https://docs.oracle.com/middleware/12213/wls/WLLOG/config_logs.htm`.
  - Retrieved 2026-06-20.
  - Supports operational planning for server/domain/HTTP access log rotation and configuration, but does not by itself provide redistributable source samples.
- Oracle WebLogic Kubernetes Operator documentation: `https://oracle.github.io/weblogic-kubernetes-operator/`.
  - Retrieved 2026-06-20.
  - Useful as public evidence that WebLogic logs are often collected through Kubernetes/file-forwarding patterns, but not proof of a canonical SC4S/syslog envelope.
- Oracle WebLogic Logging Exporter repository: `https://github.com/oracle/weblogic-logging-exporter`.
  - Retrieved 2026-06-20.
  - Useful forwarding-pattern evidence only. Exporter output is configuration-dependent and must not be treated as native WebLogic syslog proof.

Redistribution posture: Oracle documentation is copyrighted; use links and derived field/source-shape analysis only. Do not copy Oracle documentation examples into fixtures unless the exact source licence/permission permits redistribution. For GitHub-hosted Oracle projects, verify the specific repository/file licence before reusing sample configs or output.

## Evidence classification

The public evidence is sufficient for **source-shape planning** only:

- Server/domain logs have a documented distinctive first-line shape using `####` plus angle-bracket-delimited message attributes.
- HTTP access logs are a separate source family and may follow configurable text access-log layouts.
- Node Manager and Fusion Middleware diagnostic logs still require exact emitted examples before required-field coverages or fixtures can be authored.
- No exact native WebLogic syslog/SC4S relay envelope was verified.
- No redistributable real WebLogic sample events were acquired.

## Acceptable evidence for fixture authoring

For a selected WebLogic variant, collect one of the following before writing parser fixtures:

1. **Sanitized lab capture from a known WebLogic version**
   - Record WebLogic version, domain/server role, log type, log configuration, timezone settings, and collector command/path.
   - Preserve the exact record boundary. For server logs this must show how multiline message bodies continue after the `####<...>` first line.
   - Sanitize domains, hosts, users, thread identifiers if sensitive, request paths/parameters, application names, stack traces, IP addresses, and business data while preserving delimiters, angle-bracket fields, timestamps, null placeholders, multiline behavior, and severity/message identifiers.
2. **Vendor-certified or licence-permitted exact emitted example**
   - Must show complete records with boundaries, not only a field dictionary or prose description.
   - Must include redistribution/licence handling or be summarized into synthetic-equivalent rows without copying restricted sample text.
3. **Collector/exporter output with raw source retained**
   - JSON/Fluentd/Elastic/Splunk/HEC/syslog wrappers are acceptable only when both the collector envelope and the embedded raw WebLogic record are captured.
   - The fixture must state whether SC4S/SecHub sees the raw WebLogic line, a collector JSON wrapper, or both.

Oracle documentation statements about log services, access log configuration, or file locations are useful for planning, but not sufficient by themselves for parser fixtures because they do not prove selected deployment serialization, record boundaries after forwarding, timestamp rendering, multiline joining, or collector envelope.

## Variant-specific unblock checklist

### `oracle_weblogic_server`

Minimum capture:

- Exact server or domain log records from a known WebLogic version.
- At least one normal lifecycle/operational message, one warning/error message, and one message with a longer body or continuation if multiline messages are in scope.
- Required context when present: timestamp, severity, subsystem, machine, server, thread, user ID, transaction ID, diagnostic context ID, raw time, message ID, and message text.
- Event-boundary rule for `####` first lines and continuation lines.
- Timestamp timezone and raw-time semantics.

### `oracle_weblogic_access`

Minimum capture:

- Exact configured access log pattern for the server or virtual host.
- At least one successful request, one client/server error response, and one request with query/path structure that has been safely sanitized.
- Required context when present: client IP, authenticated user, method, URI/path, query handling policy, status, bytes, referer, user-agent, server/virtual-host context, and timestamp/timezone.
- Explicit statement whether the format is common, extended, JSON/custom, or another configured pattern.

### `oracle_weblogic_audit`

Minimum capture:

- Exact Security/audit provider output mode and configuration.
- At least one authentication/authorization success and one failure/denial if those are stated.
- Required context when present: user/subject, action, resource, result/status, severity, server/domain, and timestamp.
- Clear separation between WebLogic security audit records and generic server log messages.

### `oracle_weblogic_node_manager`

Minimum capture:

- Exact Node Manager log file records from a known WebLogic version.
- At least one server start/stop/lifecycle event and one error/failure event if stated.
- Required context when present: machine, domain, managed server, command/action, status/result, timestamp, and message ID/severity if emitted.

### `oracle_fusion_middleware`

Minimum capture:

- Exact source family first: SOA Suite, Service Bus, BPM, or other Fusion Middleware diagnostic/audit source.
- One variant at a time; do not merge unrelated Fusion Middleware product logs into generic fixtures.
- At least one operational message and one error/fault/security-relevant message for the selected component.
- Component, composite/service/application, user/correlation/ECID context, severity, timestamp, and message/fault tokens where present.

## Minimum implementation gate after evidence arrives

Before this source definition becomes a deployable pack, update all of the following together:

- Replace the placeholder marker with sanitized/synthetic-equivalent records for the selected variant only.
- Add SC4S/parser or collector-relay artifacts only for the proven envelope and source mode.
- Update `source_delivery`, `pack_variants`, `event_families`, `test_event_sets`, `validation_harness`, README, artifact hashes, and known limitations.
- Keep trust conservative (`catalogued` or `curated`, `unverified`) until replay/read-back or production-equivalent evidence passes.
- Run focused marker/family/hash checks and `scripts/run_ci.sh`.

## Rejected shortcuts

Do not unblock fixtures from any of these alone:

- Oracle documentation prose that describes fields without a complete record boundary.
- Generic web access-log knowledge without the exact WebLogic access log pattern.
- Logging Exporter, Fluentd, Elastic, or Splunk examples that omit the raw source record or selected collector envelope.
- Screenshots or blog prose that omit complete records.
- Invented JSON wrappers around WebLogic message attributes.
- CI/schema success, placeholder test events, or blocked preflight notes.
