# Microsoft Cloud / M365 Event Hub + Cribl pack

Conservative SecHub Resources SC4S pack for high-volume Microsoft cloud JSON arriving from Microsoft 365 / Office 365 Management Activity API, Microsoft Purview audit/DLP/label audit, Microsoft Entra ID sign-in/audit/risk feeds, Azure Monitor resource logs, Azure Activity Log, Microsoft Intune audit, Microsoft Defender, Azure Event Hub, or a Cribl pipeline that preserves source-type hints.

This is deliberately a broad intake/routing pack, not a statement that every one of the 47+ Microsoft source types is deeply parsed. Basic ingestion preserves the full JSON event and maps durable analyst fields; routing/reduction controls are opt-in and must be validated against your actual Cribl payloads.

## Evidence searched

- Microsoft Learn: Office 365 Management Activity API schema (`https://learn.microsoft.com/en-us/office/office-365-management-api/office-365-management-activity-api-schema`).
- Microsoft Learn: Azure resource logs supported services and schemas (`https://learn.microsoft.com/en-us/azure/azure-monitor/platform/resource-logs-schema`).
- Microsoft Learn: Microsoft Entra monitoring/sign-in log schemas (`https://learn.microsoft.com/en-us/entra/identity/monitoring-health/reference-azure-monitor-sign-ins-log-schema`) and Identity Protection risky user/risk-detection style fields (`riskLevel`, `riskState`, `riskDetail`, `userPrincipalName`).
- Microsoft Learn: Azure Activity Log / Azure Monitor activity schema field names including `operationName`, `eventName`, `caller`, `correlationId`, `resourceId`, and `status`.
- Microsoft Learn: Microsoft Intune audit and device compliance administration field patterns including `activity`, `activityResult`, `actor`, `targetResources`, and `category`.
- Microsoft Learn: Purview audit detailed activity properties (`https://learn.microsoft.com/en-us/purview/audit-log-detailed-properties`).
- Generated SC4S upstream inventory for the Microsoft Lite addon and CEF Microsoft/MCAS artifacts.
- User requirement: Cribl pipeline reads or pulls Microsoft 365 / Event Hub and emits many source types including `o365:management:*`, Office, Exchange, DLP, Purview, Azure audit/resource logs, and related families.

## Scope

- Listener: dedicated TCP syslog example on port 20061 with source tag `MICROSOFT_CLOUD_M365_EVENTHUB`.
- Payload: newline-delimited JSON, either headerless or syslog-wrapped by Cribl/relay.
- Routing families: `microsoft:365:management`, `microsoft:365:exchange:audit`, `microsoft:365:sharepoint:audit`, `microsoft:entra:audit`, `microsoft:entra:signin`, `microsoft:entra:identityprotection`, `microsoft:azure:resource`, `microsoft:azure:activity`, `microsoft:purview:dlp`, `microsoft:purview:audit`, `microsoft:defender:advancedhunting`, and `microsoft:intune:audit`.
- Original Cribl/source sourcetype is preserved as `ms_source_sourcetype` when the payload carries `sourcetype` or `sourceType`.
- Default indexes use the repository-approved SC4S set: `main` for broad audit/admin records, `netauth` for sign-ins, `infraops` for Azure resource logs, `netdlp` for Purview/DLP, and `epintel` for Defender hunting/security records.

## Dashboard scope

`packs/microsoft_cloud_m365_eventhub/splunk/default/data/ui/views/microsoft_cloud_m365_eventhub_soc.xml` is a fixture-backed SimpleXML SOC overview for safe onboarding and first triage across the pack's declared Microsoft Cloud/M365 fan-in sourcetypes: `microsoft:365:management`, `microsoft:365:exchange:audit`, `microsoft:365:sharepoint:audit`, `microsoft:entra:audit`, `microsoft:entra:signin`, `microsoft:entra:identityprotection`, `microsoft:azure:resource`, `microsoft:azure:activity`, `microsoft:purview:dlp`, `microsoft:purview:audit`, `microsoft:defender:advancedhunting`, and `microsoft:intune:audit`.

The dashboard uses only fixture-backed/common extracted fields plus raw JSON `spath` fields: user/actor, source IP, operation/action, result, risk state/level, object/resource/site/device/file, sensitivity label, app, source sourcetype, marker, and raw context. It has specific panels for M365/Teams-style management activity, Exchange, SharePoint/OneDrive-routed audit, Entra audit/sign-in/Conditional Access/risky users, Azure resource/Key Vault/Activity administrative changes, Purview DLP and label audit, Defender advanced hunting endpoint/security rows, and Intune audit/device compliance administration.

Coverage boundaries are deliberate: this pack/dashboard now includes synthetic-equivalent Azure Activity administrative, Entra risky-user, Purview sensitivity-label audit, and Intune audit examples, but it does **not** prove full Microsoft XDR, Defender for Cloud, Defender for Identity, Defender for Office 365, Defender for Cloud Apps/MCAS, Sentinel, complete Intune operational inventory, complete Identity Protection detections, or complete Conditional Access policy-detail coverage. Those services need explicit source families, example records, extraction/read-back checks, and live Splunk evidence before being represented as validated SOC dashboards.

Dashboard presence does not change validation posture: it is operator/onboarding visibility for synthetic-equivalent fixture shapes, not SC4S listener replay, HEC delivery, Splunk indexed read-back, or real Microsoft tenant validation.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20061` with source tag `MICROSOFT_CLOUD_M365_EVENTHUB`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `main` / `netauth` / `infraops` / `netdlp` / `epintel` with the declared family sourcetypes. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Fixture semantics

- File: `test-events/microsoft_cloud_m365_eventhub_test_events.txt`
- Format: one compact JSON object per line.
- Wire/envelope: fixture file is headerless JSON payload; `scripts/send_tcp_20061.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per line; no multiline records.
- Timestamp: Microsoft event payloads normally use UTC ISO-8601 fields such as `CreationTime`, `time`, `TimeGenerated`, `submissionTimestamp`, `detectedDateTime`, `activityDateTime`, or service-specific equivalents. Production validation must confirm any Cribl renaming.
- Markers: 12 `SC4S_MICROSOFT_CLOUD_TEST_*` values each occur exactly once.

Validation SPL smoke pattern:

```spl
(index=main OR index=netauth OR index=infraops OR index=netdlp OR index=epintel) "SC4S_MICROSOFT_CLOUD_TEST_" earliest=-2h
| table _time index sourcetype source vendor product ms_source_sourcetype operation action user src_ip result status risk_level risk_state risk_detail object app resource_group resource_provider sensitivity_label marker _raw
```

## Disposable E2E harness requirements

`packs/microsoft_cloud_m365_eventhub/scripts/e2e_docker_compose.sh` defines an idempotent disposable Splunk TEST + SC4S TEST harness for the fixture-backed Microsoft Cloud/M365 JSON relay route. It can print a no-Docker plan, write a Compose file under `.tmp/e2e/microsoft_cloud_m365_eventhub/`, start Splunk/SC4S containers, create the routed indexes (`main`, `netauth`, `infraops`, `netdlp`, and `epintel`), replay all 12 fixture records through TCP `20061`, and run summary/detail read-back SPL over the declared Microsoft sourcetypes.

Useful commands:

```bash
packs/microsoft_cloud_m365_eventhub/scripts/e2e_docker_compose.sh plan
packs/microsoft_cloud_m365_eventhub/scripts/e2e_docker_compose.sh write-compose
packs/microsoft_cloud_m365_eventhub/scripts/e2e_docker_compose.sh run
packs/microsoft_cloud_m365_eventhub/scripts/e2e_docker_compose.sh down
```

Passing this harness would be SC4S TEST -> Splunk TEST replay/read-back evidence for the synthetic-equivalent fixture route only. Adding the harness does not prove live Microsoft tenant export, Event Hub delivery, Cribl source-type preservation, API pagination/checkpoints, collector wrapper completeness, HEC delivery in this scheduled run, production readiness, or field validation.

## Reduction stance

No event drops or field deletions are enabled by default. The file `docs/microsoft_cloud_reduction_candidates.csv` lists review-required candidates for Cribl/log-reduction work:

- low-risk: duplicate collector metadata such as redundant raw copies or duplicate ingestion timestamps;
- review-required: bulky nested fields after child fields are extracted;
- high-risk: `Parameters`, `ModifiedProperties`, DLP sensitive-info metadata, and other fields that are noisy but commonly investigation-critical.

In plain English: yes, Microsoft logs are noisy. No, we should not silently throw away the one ugly nested field that explains the incident. That would be very on-brand for Microsoft and very bad for us.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated. No live Cribl/Event Hub replay, SC4S runtime replay, or Splunk read-back evidence has been captured.
- Local preflight evidence: `validation/preflight-2026-06-07.md` shows port 20061 and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Microsoft schema variants are huge and change over time; this pack provides safe intake/routing and common field aliases for the fixture-backed families, not exhaustive normalization of every workload.
- Azure Activity, Entra Identity Protection, Purview label audit, and Intune audit additions are synthetic-equivalent schema-shaped examples only; compare against local Cribl/Event Hub exports and Splunk read-back before treating those as field-validated.
- Exact source-type names and Cribl field names need to be compared against your work pipeline export before promotion.
- Optional reduction must be tested against production-like data before enablement.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real Cribl/Event Hub fixture replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, and normalized fields.
