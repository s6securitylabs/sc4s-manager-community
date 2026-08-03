# pfSense Filterlog SecHub Resources SC4S pack

This pack curates the community `community_pfsense_filterlog_issue` catalogue candidate into a conservative pfSense firewall filterlog onboarding bundle.

## Scope and evidence

- **Vendor/product:** pfSense / filterlog firewall log records.
- **Primary public reference:** Netgate pfSense documentation for raw filter log format: <https://docs.netgate.com/pfsense/en/latest/monitoring/logs/raw-filter-format.html>.
- **Candidate source:** `catalogue/generated/community/community-extra.json` entry `community_pfsense_filterlog_issue`.
- **Current quality:** `curated`, `unverified`. The parser and fixtures are documentation-grounded, but no live pfSense appliance replay and Splunk read-back evidence is stored yet.

Netgate documents the remote syslog shape as:

```text
<Timestamp> <Hostname> filterlog: <CSV data>
```

The CSV data starts with common fields: rule number, sub-rule number, anchor, tracker, interface, reason, action, direction, IP version, followed by protocol/IP-family-specific fields. This pack parses the common fields plus the documented IPv4/IPv6 transport fields that are useful for routing and CIM-oriented normalization.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tls` listener on port `20030` with source tag `PFSENSE_FILTERLOG`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netfw` and sourcetype(s) `pfsense:filterlog:tcp`, `pfsense:filterlog:udp`, `pfsense:filterlog:icmp`.

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Transport and listener

Recommended production transport is TLS syslog on the dedicated pack listener:

```bash
SC4S_LISTEN_PFSENSE_FILTERLOG_TLS_PORT=20030
SOURCE_ALL_SET=DEFAULT,PFSENSE_FILTERLOG
```

TCP or UDP syslog may be used for lab/legacy sources, but UDP can lose events and should not be considered production validation.

## Event families and sourcetypes

| Family | Sourcetype | Match basis |
| --- | --- | --- |
| `filterlog_tcp` | `pfsense:filterlog:tcp` | protocol ID `6` or protocol text `tcp` |
| `filterlog_udp` | `pfsense:filterlog:udp` | protocol ID `17` or protocol text `udp` |
| `filterlog_icmp` | `pfsense:filterlog:icmp` | protocol ID `1`/`58` or protocol text beginning `icmp` |
| fallback | `pfsense:filterlog` | recognised filterlog record without protocol split |

## Fixture semantics

`test-events/pfsense_filterlog_test_events.txt` contains three synthetic-equivalent, headerless CSV payloads using RFC5737 documentation IP ranges:

1. IPv4 TCP `pass` event.
2. IPv4 UDP `block` event.
3. IPv4 ICMP `block` event.

Each physical line is one event. The fixture file has no syslog envelope; `scripts/send_tls_20030.sh` wraps each payload in an RFC5424 message and RFC5425 octet-count frame for the dedicated TLS listener. Timestamp validation should use the RFC5424/RFC5425 header timestamp unless a deployment intentionally parses local firewall log timestamps from a full BSD/RFC5424 pfSense emission.

## Splunk knowledge

The pack ships props, eventtypes, and tags for JSON events emitted by SC4S:

- `vendor`, `product`, and `vendor_product` defaults.
- Network Traffic CIM-oriented fields: `src`, `dest`, `dest_port`, `transport`, `action`, `signature`, `signature_id`.
- Eventtypes for all filterlog events, allowed/pass traffic, and blocked traffic.

The mapping is intentionally partial. It does not state full CIM coverage for every ICMP/CARP/protocol-specific tail field.

## Dashboard

`pfsense_filterlog_overview.xml` provides a fixture-backed Splunk onboarding and first-triage view for the three documented source shapes in this pack: TCP, UDP, and ICMP filterlog CSV rows. The dashboard covers event arrival, sourcetype/protocol distribution, pass/block counters, direction and interface coverage, source/destination pair review, blocked-traffic triage, rule/tracker context, onboarding coverage, and raw CSV/JSON context.

Dashboard panels intentionally use only fields present in the synthetic-equivalent fixtures and exposed by the SC4S parser plus Splunk JSON/search-time knowledge, including `action`, `direction`, `interface`, `src`/`src_ip`, `dest`/`dest_ip`, `src_port`, `dest_port`, `protocol`/`transport`, `tracker`, `rule_number`, `reason`, `signature`, and `signature_id`. The dashboard does not state live appliance validation, complete pfSense version coverage, CARP/ESP/additional protocol tail-field support, collector health, or replay/read-back evidence.

## Disposable E2E harness

`packs/pfsense_filterlog/scripts/e2e_docker_compose.sh` defines an idempotent disposable SC4S TEST -> Splunk TEST harness for this pack. Use `plan` to review the exact stages without Docker, or `run` in the dedicated validation lab to write a Compose file, start Splunk/SC4S containers, create `index=netfw`, replay all three fixtures through TLS/RFC5425 port `20030`, and fail closed unless Splunk read-back returns all three tracker-backed fixture events.

The 2026-06-27 lab attempt is retained at `validation/e2e-lab-2026-06-27.md`: Splunk TEST and the SC4S container reached healthy-looking states, but `syslog-ng` aborted before replay and the OpenSSL send helper saw `write:errno=104`. The harness now fails closed unless a real `syslog-ng` process and usable stats socket are present; this blocked attempt is not replay/read-back validation.

Passing that harness would be replay/read-back evidence only for the shipped synthetic-equivalent pfSense filterlog CSV fixtures. It would not prove a real pfSense/Netgate appliance version, complete protocol tail-field coverage, collector wrapper behavior, production forwarding configuration, or source-local timezone behavior.

## Validation SPL

After installing/exporting the pack and sending marked fixtures:

```spl
index=netfw ("SC4S_PFSENSE_FILTERLOG_TEST" OR tracker IN (1770001001,1770001002,1770001003) OR signature_id IN (1770001001,1770001002,1770001003)) earliest=-2h
| table _time index sourcetype source host vendor product vendor_product eventtype action direction src src_ip src_interface dest dest_ip dest_port transport protocol signature signature_id tracker interface rule reason marker _raw
```

Expected read-back for the shipped fixtures:

- 3 events in `index=netfw`.
- Sourcetypes include `pfsense:filterlog:tcp`, `pfsense:filterlog:udp`, and `pfsense:filterlog:icmp`.
- `vendor="pfSense"`, `product="filterlog"`.
- Action/direction, source/destination/port, protocol, tracker/signature, interface/rule, and raw CSV context remain available for review.
- No event drops in basic/standard presets.

## Known limitations

- This pack has not yet been validated against a live pfSense/Netgate appliance and Splunk read-back, so it remains `curated`/`unverified`.
- CSV tail fields vary by IP version and protocol. The parser captures common transport fields and preserves the original event, but protocol-specific ICMP/CARP tail fields need additional fixtures before deeper extraction.
- Timezone handling depends on the syslog envelope. The synthetic headerless fixtures intentionally rely on the RFC5424 wrapper timestamp produced by the send helper.
- No default reduction/drop rules are included.
