# Cisco ASA dashboard Splunk fixture validation — 2026-06-16

## Scope

Validated the Cisco ASA/FTD dashboard XML and panel SPL against the non-production Splunk TEST instance.

This evidence proves:

- dashboard XML is accepted by Splunk as a saved view;
- six synthetic-equivalent Cisco ASA/FTD fixture rows can be indexed into `netfw` with sourcetype `cisco:asa`;
- all dashboard panel searches return fixture-backed rows/counts when run with the pack Splunk knowledge available.

This is **not** full SC4S listener / HEC / Cisco ASA source validation. It does not promote `quality_status`, `trust_level`, `validated`, `s6_verified`, `field_validated`, or `field_verified`.

## Testbed

- Splunk TEST: `10.10.100.251:8089`
- Splunk version: `10.2.3`
- Validation run marker prefix: `SECHUB_SELECTED_DASH_VALIDATE_V3_20260616T213852Z`
- Result artifact: `/tmp/selected_dashboard_validation_v3_SECHUB_SELECTED_DASH_VALIDATE_V3_20260616T213852Z.json`
- Credentials: Splunk admin password read from the existing root-owned Proxmox file; value not printed or committed.

## Fixture indexing/read-back

Read-back summary:

```text
count=6
index=netfw
sourcetype=cisco:asa
source=cisco_asa_dashboard_fixture
host=cisco_asa-fixture-host
```

## Dashboard SPL panel results

All 13 dashboard searches executed without Splunk errors and returned expected fixture-backed results, including:

- Total ASA/FTD events: `6`
- Access-group denies: `2`
- Connection builds: `2`
- NAT translations: `1`
- Message-family timechart: access-group deny, connection build, connection teardown, dynamic translation
- Source/destination pair, deny review, connection context, NAT context, facility/message coverage, onboarding coverage, and raw context panels all returned rows.

## Fixes made

The dashboard now keeps base searches to index/sourcetype/host constraints, then runs `| extract reload=true` before filtering on search-time fields such as `cisco_msg_id`, `action`, and NAT fields. Sparse `src`/`dest` dimensions are coalesced before `stats by` so fixture rows are not silently dropped.

## Caveat

This validation used direct Splunk fixture indexing for dashboard/SPL quality. It does not prove the dedicated Cisco ASA SC4S listener, syslog-ng counters, HEC destination path, or live ASA/FTD appliance behavior.
