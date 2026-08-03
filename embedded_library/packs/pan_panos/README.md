# Palo Alto Networks PAN-OS SecHub Resources Pack

Version: `0.1.5`

Primary references:

- PAN-OS syslog docs: https://pan.dev/panos/docs/syslog/
- PAN-OS syslog field descriptions: https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-admin/monitoring/use-syslog-for-monitoring/syslog-field-descriptions
- Splunk Add-on for Palo Alto Networks: https://docs.splunk.com/Documentation/AddOns/latest/PaloAltoNetworks/About
- Splunk TA source types: https://docs.splunk.com/Documentation/AddOns/latest/PaloAltoNetworks/SourceTypes

This pack upgrades the upstream `pan_panos` SC4S parser into a first-class SecHub Resources bundle for PAN-OS, Panorama, and compatible PAN-OS syslog emitters.

## Best-practice position

PAN-OS emits positional comma-delimited syslog payloads. The official Splunk Add-on for Palo Alto Networks owns the deep CSV field extractions and CIM normalization. SecHub Resources should therefore detect the PAN-OS log family, assign the correct official `pan:*` sourcetype, preserve the original CSV payload, and avoid lossy rewriting that would hide appliance tokens needed for incident review.

## Event families and sourcetypes

- `traffic` -> `pan:traffic`
- `threat` -> `pan:threat`
- `wildfire` -> `pan:wildfire`
- `system` -> `pan:system`
- `config` -> `pan:config`
- `hipmatch` -> `pan:hipmatch`
- `userid` -> `pan:userid`
- `globalprotect` -> `pan:globalprotect`
- `auth` -> `pan:auth`
- `decryption` -> `pan:decryption`
- `tunnel` -> `pan:tunnel`
- `correlation` -> `pan:correlation`
- `iptag` -> `pan:iptag`
- `gtp` -> `pan:gtp`
- `sctp` -> `pan:sctp`

Fallback sourcetype: `pan:log` for well-formed PAN-OS payloads whose type is not yet mapped.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tls` listener on port `6514` with source tag `PAN_PANOS`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netfw` and sourcetype(s) `pan:traffic`, `pan:threat`, `pan:wildfire`, `pan:system`, and 11 more declared sourcetype(s).

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Source-shape variants

The manifest now exposes the pack's source-shape boundary explicitly:

- `default_panos_syslog_csv` is the only deployable/default variant. It covers default PAN-OS/Panorama positional CSV syslog records sent through TLS/RFC5425, TCP/RFC5424, or legacy BSD-style syslog wrappers, with the 15 fixture-backed `pan:*` families listed above.
- `custom_syslog_format_future` is a non-deployable placeholder for customer-defined PAN-OS syslog formats. Custom formats can change field order, delimiters, or available fields and must be profiled from exact emitted records before parser or fixture statements are added.
- `api_export_future` is a non-deployable placeholder for API/object-store/report exports. Those records are not proven equivalent to appliance syslog CSV and must not inherit this pack's syslog route or validation posture.

All variants remain conservative. The default variant is `curated`/`unverified` until SC4S TEST -> Splunk TEST replay/read-back succeeds; the future variants are `unknown` evidence status and have no artifacts or fixtures.

## Transport and event boundaries

Recommended production transport is TLS syslog/RFC5425 with octet-counting. TCP/RFC5424 is acceptable when TLS terminates upstream. UDP/BSD is legacy/lab only. One PAN-OS log record is one syslog event; fixture files are one event per physical line.

## Timestamp policy

Prefer RFC5424/RFC5425 header timestamps when timezone-qualified. For headerless fixtures and Splunk props, `Receive Time` is the first payload timestamp and is used as the pack's primary payload timestamp; preserve PAN-OS payload `Receive Time` and `Generated Time` because both are usually `YYYY/MM/DD HH:MM:SS` without an explicit timezone. Field-only parsing requires source/firewall timezone knowledge, especially with Panorama forwarding across regions. The SC4S parser intentionally does not reinterpret those timezone-less payload fields, leaving payload timestamp parsing to Splunk props/TA knowledge where the deployment's source timezone can be configured explicitly.

## Dashboard scope

This pack includes `splunk/default/data/ui/views/pan_panos_overview.xml`, a conservative onboarding and first-triage dashboard for the fixture-backed PAN-OS CSV families. It uses local, clean-room Splunk props that expose only dashboard/read-back fields already present in the synthetic-equivalent fixtures: `pan_type`, `pan_subtype`, `serial`, source/destination tuple fields, `action`/`result`, `severity`, `app`, `rule`, `user`, `signature`/`signature_id`, and family-specific system/config/auth/GlobalProtect context.

Dashboard panels cover data-arrival health, sourcetype/family distribution, blocked/high-severity counters, traffic and threat triage, configuration/system changes, identity/auth/GlobalProtect/HIP/IP-tag context, onboarding coverage, and raw CSV drilldown. The dashboard does not prove complete Palo Alto Networks TA parity, custom syslog-format coverage, exact appliance timezone validation, collector health, or replay/read-back validation.

## Disposable E2E harness

`packs/pan_panos/scripts/e2e_docker_compose.sh` now provides a one-shot disposable SC4S TEST -> Splunk TEST path:

```bash
packs/pan_panos/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/pan_panos/compose.yaml`, starts disposable Splunk and SC4S containers, creates `index=netfw`, replays all 15 PAN-OS CSV fixtures through the TLS/RFC5425 listener mapped to host port `20039` by default, and fails closed unless Splunk read-back returns all 15 `SC4S-PAN-` fixture markers. This is a runnable lab requirement and evidence capture path only; it is not replay/read-back evidence until run in the dedicated validation lab and the SC4S/syslog-ng movement, HEC delivery, and indexed Splunk read-back output are retained.

## Validation SPL

```spl
index=netfw "SC4S-PAN-" earliest=-2h
| table _time index sourcetype source host vendor product vendor_product pan_type pan_subtype serial action result severity src src_ip src_port dest dest_ip dest_port user app rule signature signature_id eventtype tag marker _raw
```

## Known limitations

- This is curated and fixture-validated from official docs and synthetic-equivalent records, not promoted to 5-star field validation. Real PAN-OS/Panorama source/version read-back evidence is still required for `field_validated`.
- PAN-OS custom syslog formats can invalidate positional parsing. Use the default/standard PAN-OS syslog field order when targeting the Splunk TA.
- PAN-OS and the Splunk TA add fields over time. The parser is intentionally tolerant of trailing fields and avoids full SC4S-side CSV extraction.

## Splunk Edge Processor template candidates

This pack now includes file-backed Splunk Edge Processor candidate artifacts under `edge-processor/`:

- `edge-processor/modules/pan_panos_low_risk_traffic_reduce.spl2` — conservative SPL2 module candidate that annotates and routes events unchanged by default.
- `edge-processor/templates/pan_panos_low_risk_traffic_reduce.json` — metadata for source-type definitions, transforms, destination placeholders, lossy behavior, required validation, rollback, and review status.
- `edge-processor/samples/pan_panos_low_risk_traffic_reduce.raw.txt` and `.parsed.jsonl` — synthetic-equivalent snippets for preview/review only.
- `edge-processor/validation/pan_panos_low_risk_traffic_reduce-preflight.md` — explicit preflight and rollback checklist.

No Edge Processor validation/read-back is published. Any reduction remains opt-in and must pass non-production preview, replay/read-back, detection impact review, and rollback approval before use.
