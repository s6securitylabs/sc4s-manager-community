# VMware vSphere dashboard Splunk fixture validation — 2026-06-16

## Scope

Validated the VMware vSphere / ESXi / vCenter SOC dashboard XML and SPL query behavior against the non-production Splunk TEST instance.

This evidence proves:

- dashboard XML is accepted by Splunk as a saved view;
- synthetic-equivalent VMware fixture events can be indexed into the intended `infraops` and `netfw` indexes with the pack sourcetypes;
- the dashboard panel SPL returns expected rows/counts when run against those fixtures with the pack search-time knowledge available.

This is **not** full SC4S listener / HEC / VMware source validation. It does not promote `quality_status`, `trust_level`, `validated`, `s6_verified`, `field_validated`, or `field_verified`.

## Testbed

- Splunk TEST: `10.10.100.251:8089`
- Splunk version: `10.2.3`
- Validation saved view: `search/vmware_vsphere_soc_validation_20260616`
- Validation run marker: `SECHUB_VMWARE_DASH_VALIDATE_20260616T1151Z`
- Credentials: admin password read from the existing root-owned Proxmox file; value not printed or committed.

## Dashboard XML read-back

Splunk REST accepted and returned the saved view:

```json
{
  "name": "vmware_vsphere_soc_validation_20260616",
  "app": "search",
  "owner": "admin",
  "sharing": "app",
  "label": "VMware vSphere / ESXi / vCenter - SOC Overview"
}
```

## Fixture indexing/read-back

Six fixture events were submitted through Splunk REST receiver with explicit sourcetype/index metadata:

- `infraops` / `vmware:esxlog:hostd`
- `infraops` / `vmware:vclog:vpxd`
- `infraops` / `vmware:esxlog:vmkernel`
- `netfw` / `vmware:nsxlog:dfwpktlogs` × 2
- `infraops` / `vmware:esxlog:sdata`

Read-back summary:

```text
validation_run=SECHUB_VMWARE_DASH_VALIDATE_20260616T1151Z
count=6
indexes=infraops, netfw
sourcetypes=vmware:esxlog:hostd, vmware:esxlog:sdata, vmware:esxlog:vmkernel, vmware:nsxlog:dfwpktlogs, vmware:vclog:vpxd
source=search_fixture
host=vmware-fixture-host
vendor_nonempty=6
product_nonempty=6
action_nonempty=6
src_ip_nonempty=2
dest_ip_nonempty=2
src_user_nonempty=2
severity_nonempty=2
rule_nonempty=2
```

## Dashboard SPL panel results

All dashboard searches executed without Splunk errors and returned expected fixture-backed results:

- Total VMware events: `6`
- NSX DFW blocked: `1`
- vmkernel warnings/errors: `1`
- Authentication events: `1`
- Events by sourcetype over time: row with all five expected sourcetypes
- Authentication detail: `EXAMPLE\\alice`, target `esxi-1.example.test`, result `success`
- vCenter task completions: `EXAMPLE\\bob`, target `vm-example-01`, signature `completed`
- vmkernel storage warnings: `Storage path APD timeout`
- NSX DFW allowed traffic: `192.0.2.10 -> 198.51.100.20:443`, rule `domain-c7/1001`
- NSX DFW blocked traffic: `192.0.2.30 -> 198.51.100.40:22`, rule `domain-c7/1002`, raw action `DROP`
- Structured-data events: signature ID `SC4S_VMWARE_VSPHERE_TEST_SDATA_004`, severity `warning`

## Fixes made during validation

The original dashboard was too optimistic for real Splunk execution. The validation found and fixed these issues:

- Replaced broad `index IN (infraops, netfw)` clauses with `(index=infraops OR index=netfw)` for reliable SPL behavior across the test target.
- Moved calculated-field predicates such as `vendor=vmware`, `product=vsphere`, `action=blocked`, and `severity=warning` after `| extract reload=true`, so panels work against fixture-backed search-time extractions instead of depending on implicit field availability before extraction.
- Re-ran all panel searches after edits and confirmed non-zero fixture-backed results where expected.

## Caveats / evidence boundaries

- This was Splunk REST fixture indexing, not full SC4S listener replay over the VMware TLS/RFC5425 listener on port `20051`.
- Fixtures are synthetic-equivalent and documentation/upstream-grounded; they are not real VMware/NSX production logs.
- Full validation still requires the `vmware_vsphere` validation harness path: fixture/source → SC4S listener → syslog-ng route/parser → HEC → Splunk indexed read-back.
