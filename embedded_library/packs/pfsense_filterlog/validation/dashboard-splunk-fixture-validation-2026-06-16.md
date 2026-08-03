# pfSense filterlog dashboard Splunk fixture validation — 2026-06-16

## Scope

Validated the pfSense filterlog dashboard XML, CSV field extraction, and panel SPL against the non-production Splunk TEST instance.

This evidence proves:

- dashboard XML is accepted by Splunk as a saved view;
- three synthetic-equivalent pfSense filterlog fixture rows can be indexed into `netfw` with the TCP/UDP/ICMP sourcetypes;
- CSV filterlog fields required by the dashboard are extracted at search time;
- all dashboard panel searches return fixture-backed rows/counts when run with the pack Splunk knowledge available.

This is **not** full SC4S listener / HEC / pfSense source validation. It does not promote `quality_status`, `trust_level`, `validated`, `s6_verified`, `field_validated`, or `field_verified`.

## Testbed

- Splunk TEST: `10.10.100.251:8089`
- Splunk version: `10.2.3`
- Validation run marker prefix: `SECHUB_SELECTED_DASH_VALIDATE_V3_20260616T213852Z`
- Result artifact: `/tmp/selected_dashboard_validation_v3_SECHUB_SELECTED_DASH_VALIDATE_V3_20260616T213852Z.json`
- Credentials: Splunk admin password read from the existing root-owned Proxmox file; value not printed or committed.

## Fixture indexing/read-back

Read-back summary:

```text
count=3
index=netfw
sourcetypes=pfsense:filterlog:tcp, pfsense:filterlog:udp, pfsense:filterlog:icmp
source=pfsense_filterlog_dashboard_fixture
host=pfsense_filterlog-fixture-host
```

## Dashboard SPL panel results

All 14 dashboard searches executed without Splunk errors and returned expected fixture-backed results, including:

- Total pfSense filterlog events: `3`
- Passed traffic: `1`
- Blocked traffic: `2`
- Tracked rules: `3`
- Sourcetype, action/direction, protocol, interface, source/destination, blocked review, rule/tracker, transport context, onboarding, and raw event panels all returned rows.

## Fixes made

- Added search-time CSV extraction for the fixture-backed pfSense filterlog field layout across `pfsense:filterlog`, `pfsense:filterlog:tcp`, `pfsense:filterlog:udp`, and `pfsense:filterlog:icmp`.
- Hardened dashboard SPL to run `| extract reload=true` before using search-time fields.
- Moved `vendor`, `product`, and `action` predicates out of the base search and after extraction.
- Coalesced sparse `src`/`dest` dimensions before `stats by`.

## Caveat

This validation used direct Splunk fixture indexing for dashboard/SPL quality. It does not prove the pfSense SC4S listener, syslog-ng counters, HEC destination path, or live firewall behavior.
