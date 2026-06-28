# Palo Alto Networks PAN-OS SecHub Resources Pack

Version: `0.1.0`

Primary references:

- PAN-OS syslog docs: https://pan.dev/panos/docs/syslog/
- PAN-OS syslog field descriptions: https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-admin/monitoring/use-syslog-for-monitoring/syslog-field-descriptions
- Splunk Add-on for Palo Alto Networks: https://docs.splunk.com/Documentation/AddOns/latest/PaloAltoNetworks/About
- Splunk TA source types: https://docs.splunk.com/Documentation/AddOns/latest/PaloAltoNetworks/SourceTypes

This pack upgrades the upstream `pan_panos` SC4S parser into a first-class SecHub Resources bundle for PAN-OS, Panorama, and compatible PAN-OS syslog emitters.

## Best-practice position

PAN-OS emits positional comma-delimited syslog payloads. The official Splunk Add-on for Palo Alto Networks owns the deep CSV field extractions and CIM normalization. SC4S Manager should therefore detect the PAN-OS log family, assign the correct official `pan:*` sourcetype, preserve the original CSV payload, and avoid clever lossy rewriting. Heroics are for dashboards and people avoiding therapy.

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

## Transport and event boundaries

Recommended production transport is TLS syslog/RFC5425 with octet-counting. TCP/RFC5424 is acceptable when TLS terminates upstream. UDP/BSD is legacy/lab only. One PAN-OS log record is one syslog event; fixture files are one event per physical line.

## Timestamp policy

Prefer RFC5424/RFC5425 header timestamps when timezone-qualified. Preserve PAN-OS payload `Receive Time` and `Generated Time`; they are usually `YYYY/MM/DD HH:MM:SS` without an explicit timezone, so field-only parsing requires source/firewall timezone knowledge, especially with Panorama forwarding across regions.

## Validation SPL

```spl
index=netfw ("SC4S-PAN-TRAFFIC-MARKER" OR "SC4S-PAN-THREAT-MARKER" OR "SC4S-PAN-GLOBALPROTECT-MARKER") earliest=-2h
| table _time index sourcetype source vendor product action severity src dest src_ip dest_ip user app signature signature_id category _raw
```

## Known limitations

- This is curated and fixture-validated from official docs and synthetic-equivalent records, not promoted to 5-star field validation. Real PAN-OS/Panorama source/version read-back evidence is still required for `field_validated`.
- PAN-OS custom syslog formats can invalidate positional parsing. Use the default/standard PAN-OS syslog field order when targeting the Splunk TA.
- PAN-OS and the Splunk TA add fields over time. The parser is intentionally tolerant of trailing fields and avoids full SC4S-side CSV extraction.
