# Oracle OCI source-shape acquisition plan — 2026-06-20

## Purpose

This note turns the current Oracle Cloud Infrastructure catalogue-only blocker into a concrete evidence-acquisition checklist. It is not validation evidence, does not contain OCI tenant events, and must not be used to promote `quality_status`, `trust_level`, `review_status`, or downloadability.

The `oracle_oci` pack remains routing-disabled and catalogue-only until one variant has exact emitted-record evidence, safe fixtures, and replay/read-back or collector read-back.

## Public evidence checked in this pass

- OCI Audit overview: `https://docs.oracle.com/en-us/iaas/Content/Audit/Concepts/auditoverview.htm` — HTTP 200 from this runtime on 2026-06-20.
- OCI Logging overview: `https://docs.oracle.com/en-us/iaas/Content/Logging/Concepts/loggingoverview.htm` — HTTP 200 from this runtime on 2026-06-20.
- OCI WAF overview: `https://docs.oracle.com/en-us/iaas/Content/WAF/Concepts/overview.htm` — HTTP 200 from this runtime on 2026-06-20.
- OCI Cloud Guard documentation home: `https://docs.oracle.com/en-us/iaas/cloud-guard/home.htm` — HTTP 200 from this runtime on 2026-06-20.
- OCI Bastion overview: `https://docs.oracle.com/en-us/iaas/Content/Bastion/Concepts/bastionoverview.htm` — HTTP 200 from this runtime on 2026-06-20.
- The previously guessed VCN flow-log task URL `https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/vcn-flow-logs.htm` returned HTTP 404 from this runtime on 2026-06-20; do not use that stale URL as source-shape evidence.

Redistribution posture: Oracle documentation is copyrighted; use links and derived field/source-shape analysis only. Do not copy Oracle examples into fixtures unless the exact source licence or permission permits redistribution. OCI tenant exports must be sanitized or converted to synthetic-equivalent rows before committing.

## Evidence classification

The public evidence above is sufficient for **source-family planning** only:

- OCI Audit and Logging docs establish that cloud/API/logging-service delivery is the likely source path, not native appliance syslog.
- WAF, Cloud Guard, Bastion, VCN Flow, Object Storage, and Load Balancer should remain separate variants because their payloads, sensitivity, volume, and analyst fields differ.
- The pack must preserve the collector/logging envelope separately from the embedded service payload when both exist.
- No exact OCI tenant export record, service connector output, Object Storage drop, Streaming payload, Splunk/HEC wrapper, or SC4S relay envelope was captured in this pass.
- No redistributable real OCI events were acquired.

## Acceptable evidence for fixture authoring

For a selected OCI variant, collect one of the following before writing parser fixtures:

1. **Sanitized tenant/lab export from a known OCI tenancy and region**
   - Record source service, region, compartment scope, collection path, export mechanism, collector version/configuration, timezone handling, and whether events came through Audit API, Logging, Service Connector Hub, Streaming, Object Storage, or another relay.
   - Preserve one complete emitted record exactly as the collector or SecHub/SC4S would receive it.
   - Sanitize OCIDs, tenancy/compartment names, users, groups, IPs, hostnames, request parameters, bucket/object names, user agents, and resource names while preserving JSON keys, arrays, nulls, timestamp format, nesting, event boundary, and service-specific payload structure.
2. **Vendor-certified or licence-permitted exact emitted example**
   - Must show a complete record with its boundary and envelope, not only a field dictionary or prose description.
   - Must include redistribution/licence handling or be summarized into synthetic-equivalent rows without copying restricted sample text.
3. **Collector output with raw OCI record retained**
   - JSON/CSV/syslog/HEC/Cribl/Fluent Bit wrappers are acceptable only when both the collector envelope and the embedded OCI record are captured.
   - The fixture must state whether SecHub/SC4S sees the OCI Logging record envelope, a collector wrapper, the service payload, or more than one layer.

Oracle service documentation and API schemas can support field planning, but they are not sufficient by themselves for fixtures because they do not prove selected export serialization, service-specific `data` payloads, record boundaries, timestamp rendering, null handling, or collector envelope.

## Variant-specific unblock checklist

### `oracle_oci_audit`

Minimum capture:

- Exact Audit API / Logging / Service Connector / Object Storage / Streaming record shape for at least IAM/admin action, network/security-list or route action, compute/resource lifecycle action, and a denied/failed action if emitted by the selected path.
- Required context when present: event time, event type/name, event ID, principal OCID/name, request action/path, request ID, source IP, user agent, compartment OCID/name, resource OCID/name/type, response status/code, region, and service-specific `data` payload.
- Explicit treatment of OCIDs and tenant/compartment names in sanitized fixtures.
- Timestamp timezone and any collector-added receive time.

### `oracle_oci_logging`

Minimum capture:

- Exact OCI Logging record envelope as delivered through the chosen path.
- At least one event where the envelope wraps another service payload so parser design can separate envelope fields from service fields.
- Required context when present: log OCID/name, log group, source/service, subject, time, compartment, region, and embedded payload path.
- Clear statement whether the pack indexes the generic envelope, routes by embedded service type, or both.

### `oracle_oci_vcn_flow`

Minimum capture:

- Current VCN Flow Logs emitted record from a supported delivery path; do not rely on the stale 404 URL recorded above.
- At least one allowed/accepted flow and one rejected/denied or otherwise differentiated flow if the selected format exposes action/status.
- Required context when present: VCN/subnet/VNIC/interface identifiers, source/destination IPs and ports, protocol, packets/bytes, start/end time, action/status, compartment/region, and flow direction if emitted.
- Volume/reduction review: flow logs can be high-volume; no default drops are allowed without replay/read-back and rollback guidance.

### `oracle_oci_waf`

Minimum capture:

- Exact WAF access/security event payload from the selected OCI WAF logging/export path.
- At least one allowed/request event and one blocked/detected/security event if those are stated.
- Required context when present: client IP, host, method, URI/path/query handling, action, rule/policy, response status, request ID, user agent, TLS/protocol context, and timestamp.
- Clear privacy handling for URLs, headers, cookies, and request parameters.

### `oracle_oci_cloud_guard`

Minimum capture:

- Exact Cloud Guard problem/detector/responder record from an export/API/logging path.
- At least one detected problem/finding and one status/response/lifecycle update if those are stated.
- Required context when present: detector/rule/problem ID, risk/severity, lifecycle state, resource OCID/type/name, compartment, region, labels, recommendation/remediation, responder/action status, and timestamp.

### `oracle_oci_bastion`

Minimum capture:

- Exact Bastion audit/session/control event shape from Audit/Logging/API export.
- At least one session creation/start and one session end/failure/delete/admin change if those are stated.
- Required context when present: bastion OCID/name, session OCID/name, target resource, principal, source IP, target IP/port, SSH command/session metadata if emitted, result/status, compartment, region, and timestamps.

### `oracle_oci_object_storage`

Minimum capture:

- Exact Object Storage activity source path: audit events, service logs, bucket/object access logs, or collector-derived records.
- At least one read/list, one write/update, and one delete/security-relevant action if those are stated.
- Required context when present: bucket, object/key, namespace, action, request ID, principal, source IP, response status, object size/checksum/version if emitted, compartment, region, and timestamp.
- Sanitization must preserve object-key structure without exposing tenant/business names.

### `oracle_oci_load_balancer`

Minimum capture:

- Exact Load Balancer access/security log record shape for the configured log type.
- At least one successful request and one error/denied/unhealthy-backend case if those are stated.
- Required context when present: client IP/port, backend IP/port, listener, hostname, method, URI/path/query handling, status, bytes, request time/latency, TLS/protocol, request ID, compartment/region, and timestamp.

## Minimum implementation gate after evidence arrives

Before this source definition becomes a deployable pack, update all of the following together:

- Replace the placeholder marker with sanitized/synthetic-equivalent records for the selected variant only.
- Add SC4S/parser or collector-relay artifacts only for the proven envelope and source mode.
- Update `source_delivery`, `pack_variants`, `event_families`, `test_event_sets`, `validation_harness`, README, artifact hashes, and known limitations.
- Keep trust conservative (`catalogued` or `curated`, `unverified`) until replay/read-back or production-equivalent evidence passes.
- Run focused marker/family/hash checks and `scripts/run_ci.sh`.

## Rejected shortcuts

Do not unblock fixtures from any of these alone:

- OCI product overviews without a complete emitted record.
- Field dictionaries or API schemas that omit serialization and record boundaries.
- Invented JSON wrappers around Oracle service fields.
- Collector examples that omit the raw OCI record or omit the wrapper that SecHub/SC4S would receive.
- Screenshots, blog prose, or dashboard examples that omit full records.
- CI/schema success, placeholder test events, generated catalogue rows, or blocked preflight notes.
