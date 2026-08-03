# CrowdStrike Falcon dashboard Splunk fixture validation — 2026-06-16

## Scope

Validated the CrowdStrike Falcon Platform JSON Relay SOC dashboard XML and all panel SPL against the non-production Splunk TEST instance.

This evidence proves:

- dashboard XML is accepted by Splunk as a saved view;
- 23 synthetic-equivalent CrowdStrike Falcon fixture rows can be indexed into `epintel` across all declared sourcetypes;
- all dashboard panel searches return fixture-backed rows/counts when run with the pack Splunk knowledge available;
- Spotlight vulnerability, Devices API inventory, detection, Identity Protection incident, RTR, audit, firewall policy, FDR process/network/DNS/file/asset, and intelligence panels match the current fixture shapes.

This is **not** full SC4S listener / HEC / live CrowdStrike source validation. It does not promote `quality_status`, `trust_level`, `validated`, `s6_verified`, `field_validated`, or `field_verified`.

## Testbed

- Splunk TEST: `10.10.100.251:8089`
- Splunk version: `10.2.3`
- Validation run marker prefix: `SECHUB_SELECTED_DASH_VALIDATE_V3_20260616T234126Z`
- Result artifact: `/tmp/selected_dashboard_validation_v3_SECHUB_SELECTED_DASH_VALIDATE_V3_20260616T234126Z.json`
- Credentials: Splunk admin password read from the existing root-owned Proxmox file; value not printed or committed.

## Fixture indexing/read-back

Read-back summary:

```text
count=23
index=epintel
source=crowdstrike_falcon_dashboard_fixture
host=crowdstrike_falcon-fixture-host
sourcetypes=crowdstrike:falcon:api:devices, crowdstrike:falcon:api:intel, crowdstrike:falcon:api:spotlight, crowdstrike:falcon:eventstream:audit, crowdstrike:falcon:eventstream:detection, crowdstrike:falcon:eventstream:identity, crowdstrike:falcon:eventstream:policy, crowdstrike:falcon:eventstream:rtr, crowdstrike:falcon:fdr:asset, crowdstrike:falcon:fdr:dns, crowdstrike:falcon:fdr:file, crowdstrike:falcon:fdr:network, crowdstrike:falcon:fdr:process
```

## Dashboard SPL panel results

All 21 dashboard searches executed without Splunk errors and returned expected fixture-backed results, including:

- Total Falcon events: `23`
- Active detections: `1`
- Spotlight open vulnerabilities: `1`
- RTR sessions: `1`
- Events by sourcetype over time: all 13 declared sourcetypes represented by fixture rows
- Detection summary table: returns device, user, detect ID/name/description, tactic, technique, and severity
- Identity Protection incident table: returns `identity_incident_id`, device, endpoint IP, user, incident/detect name, and severity
- Spotlight vulnerability table/CVE/product panels: return device, OS, CVE, severity, affected product, status, and remediation
- Devices API inventory table: returns device name, local/external IP, OS version, agent version, device status, and last seen time

## Fixes made

The dashboard now keeps base searches to index/sourcetype/time constraints, then runs `| extract reload=true` and, where needed, explicit `| spath` before filtering on search-time or nested JSON fields.

Specific corrections:

- Spotlight panels no longer filter on `vulnerability_status`, `device_name`, `cve_id`, `severity`, `affected_product`, or remediation fields before extraction/materialisation.
- Devices API inventory no longer filters on `device_name` before it is materialised from `hostname`/aliases.
- Detection and Identity Protection incident panels explicitly materialise nested `event.*` fields, so incident and detection rows show useful triage context rather than sparse raw-only rows.
- Dashboard host/device filtering is applied after search-time fields exist.

## Incidents note

This pack currently has fixture-backed **Identity Protection incident/detection** coverage via `crowdstrike:falcon:eventstream:identity`. It does not state coverage for the deprecated Falcon **Incidents API** entity export. FalconPy public endpoint evidence confirms the legacy Incidents API is marked deprecated and scheduled for removal in March 2026; exact emitted incident entity samples were not added to this pack. If local tenants still export Incidents API entities, add sanitized samples or an official schema-backed fixture before adding a separate `crowdstrike:falcon:api:incidents` sourcetype/dashboard panel.

## Caveat

This validation used direct Splunk fixture indexing for dashboard/SPL quality. It does not prove the dedicated CrowdStrike SC4S listener, syslog-ng counters, HEC destination path, API collector completeness, FDR/Event Streams delivery, or live CrowdStrike tenant behavior.
