# Microsoft Defender XDR pack

Conservative SecHub Resources SC4S pack for Microsoft Defender XDR advanced-hunting and security-alert JSON records relayed one event per line through Cribl, Event Hub, API export, HEC-style relay, or another collector into a dedicated SC4S listener. Fixture-backed coverage includes Defender for Endpoint, Defender XDR alerts/evidence, Defender for Identity, and Defender for Cloud Apps table shapes.

This is an endpoint/identity/SaaS/security-alert intake pack, not full Microsoft Defender validation. It preserves full JSON records, routes fixture-backed high-value families, and exposes durable analyst fields while keeping trust `curated`/`unverified` until real replay/read-back evidence exists.

## Evidence searched

- Microsoft Learn: Advanced hunting schema tables for Microsoft Defender XDR (`DeviceProcessEvents`, `DeviceNetworkEvents`, `DeviceFileEvents`, `DeviceRegistryEvents`, `AlertInfo`, `AlertEvidence`, `IdentityLogonEvents`, `IdentityDirectoryEvents`, `IdentityQueryEvents`, `EmailEvents`, `EmailUrlInfo`, `EmailAttachmentInfo`, `DeviceTvmSoftwareVulnerabilities`, and `CloudAppEvents`).
- Microsoft Learn: Microsoft Defender XDR streaming/API export concepts and Microsoft 365 Defender advanced hunting schema naming.
- Existing Library Microsoft cloud/Event Hub pack boundaries, to keep this pack focused on endpoint/security-alert/email-security telemetry rather than broad M365 management logs.

## Scope

- Listener: dedicated TCP syslog example on port `20067` with source tag `MICROSOFT_DEFENDER_XDR`.
- Payload: newline-delimited JSON, either headerless or syslog-wrapped by the relay.
- Routed families: device process, device network, device file, device registry, alert metadata/evidence, identity logon, identity directory, identity query, Defender for Office 365 email/message URL/attachment context, TVM software vulnerability rows, and cloud app activity.
- Default index: `epintel` as a conservative security-telemetry landing index for the fixture-backed endpoint, email, alert, identity, and cloud app families.

## Dashboard scope

`packs/microsoft_defender_xdr/splunk/default/data/ui/views/microsoft_defender_xdr_overview.xml` is a fixture-backed SimpleXML overview for safe onboarding and first triage. It covers only the declared/tested Defender XDR sourcetypes: `microsoft:defender:xdr:device_process`, `microsoft:defender:xdr:device_network`, `microsoft:defender:xdr:file_event`, `microsoft:defender:xdr:device_registry`, `microsoft:defender:xdr:alert_info`, `microsoft:defender:xdr:alert_evidence`, `microsoft:defender:xdr:identity_logon`, `microsoft:defender:xdr:identity_directory`, `microsoft:defender:xdr:identity_query`, `microsoft:defender:xdr:email_event`, `microsoft:defender:xdr:email_url`, `microsoft:defender:xdr:email_attachment`, `microsoft:defender:xdr:vulnerability`, and `microsoft:defender:xdr:cloud_app`.

The dashboard panels use fields present in the fixtures and exposed by JSON extraction or `props.conf`: `defender_table`, `device_name`/`DeviceName`, `device_id`, `user`/`AccountUpn`/`InitiatingProcessAccountUpn`, `target_user`/`TargetAccountUpn`, `action`/`ActionType`, process command-line fields, local/remote/IP tuple fields, file path/hash/object fields, registry key/value context, email sender/recipient/subject/delivery/threat/URL/attachment context, TVM `CveId`/software/severity/update context, `alert_id`/`AlertId`, `severity`, `category`, `signature`, `entity_type`, `evidence_role`, identity query fields, cloud application/object fields, `marker`, and raw JSON. It intentionally does not chart unrepresented Defender tables, native Event Hub envelope fields, incidents, Secure Score, post-delivery tables, exposure-score/device assessment joins, or collector checkpoint health.

Dashboard presence does not change validation posture: it is operator/onboarding visibility for synthetic-equivalent fixture shapes, not SC4S listener replay, HEC delivery, Splunk indexed read-back, or real Defender tenant validation.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20067` with source tag `MICROSOFT_DEFENDER_XDR`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `epintel` / sourcetype(s) `microsoft:defender:xdr:device_process`, `microsoft:defender:xdr:device_network`, `microsoft:defender:xdr:file_event`, `microsoft:defender:xdr:device_registry`, `microsoft:defender:xdr:alert_info`, `microsoft:defender:xdr:alert_evidence`, `microsoft:defender:xdr:identity_logon`, `microsoft:defender:xdr:identity_directory`, `microsoft:defender:xdr:identity_query`, `microsoft:defender:xdr:email_event`, `microsoft:defender:xdr:email_url`, `microsoft:defender:xdr:email_attachment`, `microsoft:defender:xdr:vulnerability`, and `microsoft:defender:xdr:cloud_app`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Fixture semantics

- File: `test-events/microsoft_defender_xdr_test_events.txt`.
- Format: one compact JSON object per line.
- Wire/envelope: fixture file is headerless JSON payload; `scripts/send_tcp_20067.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; no multiline records.
- Timestamp: fixtures use the Defender `Timestamp` field with UTC ISO-8601 `Z` timestamps.
- Markers: `SC4S_MICROSOFT_DEFENDER_XDR_TEST_*` values each occur exactly once.
- Current fixture set has 14 rows: endpoint process, network, file, registry; alert metadata/evidence; identity logon/directory/query; email message, URL, and attachment context; TVM software vulnerability context; and cloud app activity.

Validation SPL smoke pattern:

```spl
index=epintel "SC4S_MICROSOFT_DEFENDER_XDR_TEST_" earliest=-2h
| table _time index sourcetype source vendor product defender_table action device_name device_id dest dest_device user process_user target_user process process_command_line parent_process parent_process_command_line parent_process_hash src_ip dest_ip dest_port transport url file_name file_path previous_file_name previous_file_path file_type object_name object_type application app_instance_id activity_type query query_type alert_id severity category signature service_source detection_source entity_type evidence_role network_message_id internet_message_id sender mail_from recipient delivery_action delivery_location threat_types detection_methods confidence_level email_direction url_domain url_location registry_key registry_value_name registry_value_data cve software_vendor software_name software_version recommended_security_update recommended_security_update_id marker _raw
```

## Reduction stance

No event drops or field deletions are enabled by default. `docs/microsoft_defender_xdr_reduction_candidates.csv` lists advisory candidates only. Command lines, alert evidence rows, identity query/directory context, email sender/recipient/message/URL/attachment context, TVM vulnerability/software context, registry key/value data, cloud app object context, URL/IP context, file paths, hashes, account identifiers, and device identifiers are high-risk to drop because they are central to endpoint, identity, SaaS, email-security, vulnerability, detection triage, alert/evidence joins, and audit challenge.

## Disposable E2E harness

`packs/microsoft_defender_xdr/scripts/e2e_docker_compose.sh` defines an idempotent Docker/Compose Splunk TEST + SC4S TEST harness for the declared fixture route. Use `plan` for the evidence requirements without Docker, `write-compose` to materialize `.tmp/e2e/microsoft_defender_xdr/compose.yaml`, and `run` only in a permitted disposable lab. The harness pre-creates `index=epintel`, starts SC4S with the `MICROSOFT_DEFENDER_XDR` TCP listener on port `20067`, replays all 14 fixture rows through `scripts/send_tcp_20067.sh`, and queries Splunk for the expected `microsoft:defender:xdr:*` sourcetypes and field table.

A successful harness run would be SC4S TEST -> Splunk TEST replay/read-back evidence for the synthetic-equivalent fixture path only. It would still not prove a live Defender tenant, Advanced Hunting export completeness, Event Hub/streaming API envelope fidelity, collector pagination/checkpoint custody, or field validation from real source-version telemetry.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-07.md` shows port `20067` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked. The disposable E2E harness is a runnable requirements for a permitted Docker lab, not replay/read-back evidence until executed and retained.
- Fixtures are synthetic-equivalent examples shaped from public Defender XDR schema documentation; they are not real tenant records.
- Exact collector wrapper fields, export table names, and schema coverage must be compared against the local Defender export/Cribl/Event Hub pipeline before promotion.
- Email coverage is limited to selected `EmailEvents`, `EmailUrlInfo`, and `EmailAttachmentInfo` message/URL/attachment context. Post-delivery, mailbox/audit, incidents, and complete Defender for Office 365 schemas remain future work.
- TVM coverage is limited to selected `DeviceTvmSoftwareVulnerabilities` software/CVE rows. It does not prove device assessment joins, exposure score, remediation status, or complete vulnerability-management workflow coverage.
- Registry coverage is limited to selected `DeviceRegistryEvents` key/value context. It does not prove complete endpoint registry telemetry or live Defender for Endpoint delivery.
- Optional reduction must be tested against production-like endpoint data before enablement.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real Defender XDR fixture or production-equivalent replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, alert/evidence correlation, and normalized fields.
