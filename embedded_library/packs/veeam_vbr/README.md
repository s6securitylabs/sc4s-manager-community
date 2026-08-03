# Veeam Backup & Replication SecHub Resources SC4S pack

This pack curates the upstream SC4S `veeam_vbr` parser inventory into a conservative Veeam Backup & Replication syslog onboarding bundle.

## Scope and evidence

- **Vendor/product:** Veeam / Backup & Replication.
- **Upstream SC4S references:** `docs/sources/vendor/Veeam/veeam.md` and `package/etc/conf.d/conflib/syslog/app-syslog-veeam_vbr.conf` route `program('Veeam_MP')` to `veeam:vbr:syslog`.
- **Official event evidence:** Veeam Help Center, "How integration with Syslog Server Works" for Veeam Backup & Replication 12, documents RFC5424/RFC3339 syslog and gives an example event with `APP-NAME` `Veeam_MP` and structured metadata such as `categoryId`, `instanceId`, `JobSessionID`, `JobID`, `JobType`, `Platform`, `Flags`, `Version`, and `Description`.
- **Public parser schema evidence:** ExabeamLabs Content-Library-CIM2 parser `veeam-v-kv-app-activity-success-veeam_mp` confirms public field expectations for `Veeam_MP` events including `categoryId`, `instanceId`, `TaskSessionID`, `Status`, `JobDescription`, `SourceHostName`, `Description`, `ActivityType`, `UserName`, and `ObjectName`.
- **Current quality:** `curated`, `unverified`. Fixtures are synthetic-equivalent from public documentation/schema examples only; no live Veeam server replay and Splunk read-back evidence is stored yet.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tls` listener on port `20040` with source tag `VEEAM_VBR`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `infraops` and sourcetype(s) `veeam:vbr:syslog`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Transport and listener

Recommended production transport is TLS syslog with RFC5425 octet-counted framing:

```bash
SC4S_LISTEN_VEEAM_VBR_TLS_PORT=20040
SOURCE_ALL_SET=DEFAULT,VEEAM_VBR
```

Veeam also documents TCP/UDP and default ports 514/6514. Use UDP only for lab/legacy sources because it can lose events.

## Event families and sourcetype

| Family | Sourcetype | Match basis |
| --- | --- | --- |
| `vbr_job_activity` | `veeam:vbr:syslog` | `APP-NAME`/program `Veeam_MP` plus job/session metadata |

The SC4S parser intentionally keeps the family conservative. It sets destination metadata, parses the RFC5424 structured-data style key/value message body into `.values.*`, preserves the original message, and does not drop or reduce events.

## Fixture semantics

`test-events/veeam_vbr_test_events.txt` contains two synthetic-equivalent RFC5424-like lines derived from Veeam's official example shape and public parser field expectations:

1. Job started event with `JobSessionID`/`JobID` and marker `SC4S_VEEAM_VBR_TEST_JOB_START_001`.
2. Job completed event with `TaskSessionID`, `Status`, `UserName`, and marker `SC4S_VEEAM_VBR_TEST_JOB_SUCCESS_002`.

Each physical line is one event. Timestamps are RFC3339/RFC5424-style and include offsets. The TLS send helper wraps each line with an RFC5425 octet-count prefix for the dedicated listener.

## Splunk knowledge

The pack ships props/eventtypes/tags for SC4S JSON output and Veeam structured-data fields:

- `vendor`, `product`, and `vendor_product` defaults.
- `action`, `signature`, `signature_id`, `session_id`, `job_id`, `job_type`, `job_description`, `platform`, `veeam_flags`, `veeam_event_version`, `user`, `src_host`, and job/object fields where present.
- Eventtypes for all VBR syslog events, job activity, and successful activity.

Mappings are intentionally partial and do not state full CIM coverage for all Veeam event IDs.

## Dashboard scope

`splunk/default/data/ui/views/veeam_vbr_overview.xml` provides a fixture-backed onboarding and first-triage dashboard for the covered Veeam Backup & Replication syslog shape. It focuses on arrival health, successful job/activity counts, session and object coverage, action/result distribution, Veeam structured-data identifiers, users/source hosts/objects, onboarding host/source coverage, and raw event context.

Dashboard panels use only fields proven by the current fixtures and Splunk props: `sourcetype`, `vendor`, `product`, `action`, `result`, `session_id`, `signature`, `signature_id`, `object`, `src_host`, `user`, `marker`, and preserved `values.*` structured-data keys such as `values.categoryId`, `values.instanceId`, `values.JobSessionID`, `values.TaskSessionID`, `values.Status`, `values.ActivityType`, `values.SourceHostName`, and `values.ObjectName`.

The dashboard does not state coverage for the complete Veeam Event Reference, ransomware/malware detections, repository capacity/health telemetry, Enterprise Manager APIs, collector health, or every VBR job/task status variant. Dashboard availability does not change the pack's `curated`/`unverified` status; live Veeam relay replay and Splunk indexed read-back are still required before validation promotion.

## Validation SPL

After installing/exporting the pack and sending marked fixtures:

```spl
index=infraops "SC4S_VEEAM_VBR_TEST" earliest=-2h
| table _time index sourcetype source vendor product action signature signature_id session_id job_id job_type job_description platform veeam_flags veeam_event_version user src_host object result _raw
```

Expected read-back for the shipped fixtures:

- 2 events in `index=infraops`.
- Sourcetype `veeam:vbr:syslog`.
- `vendor="Veeam"`, `product="Backup & Replication"`.
- No event drops in basic/standard presets.

## Disposable SC4S TEST -> Splunk TEST harness

`packs/veeam_vbr/scripts/e2e_docker_compose.sh` provides an idempotent Docker/Compose harness requirements for a permitted disposable lab. Use `plan` to review the exact stages without Docker side effects:

```bash
packs/veeam_vbr/scripts/e2e_docker_compose.sh plan
```

When Docker and the required images are available, `run` writes `.tmp/e2e/veeam_vbr/compose.yaml`, starts Splunk TEST plus SC4S TEST, creates `index=infraops`, replays both RFC5424/RFC5425 Veeam fixtures through TCP `20040`, then runs summary/detail read-back SPL for `veeam:vbr:syslog` and the Veeam structured-data fields listed above.

Passing this harness would be fixture-backed SC4S TEST -> Splunk TEST replay/read-back evidence for the packaged Veeam syslog route only. It is not live Veeam Backup & Replication server/source-version validation, product-build coverage, collector wrapper proof, source-local timezone proof, HEC delivery evidence until actually run, production readiness, or trust/quality promotion.

## Known limitations

- This pack has not yet been validated against a live Veeam Backup & Replication server and Splunk read-back, so it remains `curated`/`unverified`.
- The parser is grounded in official/public examples but does not enumerate every Veeam Event Reference event ID.
- Structured-data escaping edge cases need real-event fixtures before deeper extraction or validated status.
- No default reduction/drop rules are included.
