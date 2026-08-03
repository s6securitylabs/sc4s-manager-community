# Sophos Firewall

Curated SecHub Resources pack for **Sophos Firewall / SFOS syslog** records relayed to SC4S. The pack is intentionally narrow: it covers native Sophos Firewall key=value syslog records and does **not** cover Sophos Central SIEM API `/events` or `/alerts` JSON. Central API collection requires a separate collector/API relay pack or variant with cursor/checkpoint ownership.

## Scope and source shape

- Vendor/product: Sophos Firewall / SFOS.
- Delivery mode: native syslog from Sophos Firewall to a dedicated SC4S listener/source tag.
- Fixture wire shape: headerless Sophos key=value payloads, one event per line. The send helper wraps each payload in RFC5424/RFC5425 for TEST replay.
- Default routing: firewall and IPS families to `netfw`, VPN family to `netauth`, system-health family to `netops`.
- Public evidence: Sophos Firewall 21.0 syslog documentation describes external syslog forwarding, `log_id` composition, severity/status values, and field tables for firewall, IPS/network protection, VPN, WAF/web, wireless, and system areas. This pack uses only concise derived field coverage, not a mirror of the vendor guide.

## Event families

| Family | Sourcetype | Fixture marker | Notes |
| --- | --- | --- | --- |
| Firewall traffic allow | `sophos:firewall:traffic` | `SC4S_SOPHOS_FIREWALL_TEST_TRAFFIC_ALLOW_001` | Preserves `log_id`, `fw_rule_id`, source/destination tuple, status/action, user, byte counters, and appliance identity. |
| Firewall traffic deny | `sophos:firewall:traffic` | `SC4S_SOPHOS_FIREWALL_TEST_TRAFFIC_DENY_002` | Same tuple fields with deny status; useful for blocked-traffic triage. |
| IPS/network protection | `sophos:firewall:ips` | `SC4S_SOPHOS_FIREWALL_TEST_IPS_DETECTED_003` | Preserves documented security-event context such as `threat`, category, tuple, and device identity. |
| VPN login | `sophos:firewall:vpn` | `SC4S_SOPHOS_FIREWALL_TEST_VPN_LOGIN_004` | Preserves user/source/result/status context for SSL VPN-style relay rows. |
| System health | `sophos:firewall:system` | `SC4S_SOPHOS_FIREWALL_TEST_SYSTEM_HEALTH_005` | Preserves status/severity and appliance identity for system events. |

## Operator notes

- Use a dedicated listener/source tag (`SOPHOS_FIREWALL`) rather than broad key=value matching whenever possible.
- No lossy filtering, masking, or null-queue reduction is enabled by default.
- Retain source/destination tuple, user, rule, message, `log_id`, severity/status, and appliance serial/hostname by default; these fields are needed for SOC triage and audit challenge.
- `vendor_raw_action` preserves the raw Sophos `status`/`log_subtype` action token before any analyst-facing interpretation.
- Synthetic fixtures use RFC5737 documentation IP ranges and example appliance/user values. They are not customer or field telemetry.

## Validation status

Current posture: `curated` / `unverified`; public Review status should remain **Unreviewed** until maintainer review. The pack has schema/fixture/local artifact coverage only. It has not been replayed through a live Sophos Firewall SC4S route or read back from Splunk.

Blocked preflight evidence is recorded in `validation/preflight-2026-06-20.md`: no local listener was present on TCP 20097 and Splunk management/search API on TCP 8089 refused connections. TCP 8000 accepted a web connection, but no authenticated read-back was attempted.

A disposable Docker/Compose harness is now registered for a permitted lab run:

```bash
packs/sophos_firewall/scripts/e2e_docker_compose.sh plan
packs/sophos_firewall/scripts/e2e_docker_compose.sh run
```

The harness writes an isolated Splunk TEST + SC4S TEST stack under `.tmp/e2e/sophos_firewall/`, creates `netfw`, `netauth`, and `netops`, replays all five synthetic-equivalent SFOS key=value fixtures through the TLS/RFC5425 listener on TCP 20097, and queries Splunk for marker read-back. A passing harness run would be fixture-route SC4S TEST -> Splunk TEST evidence only. It would not prove live Sophos Firewall appliance emission, SFOS version-specific fields, Sophos Central SIEM API collection, WAF/web-filter/wireless categories, production readiness, or field validation.

Required replay/read-back SPL after a TEST route is available:

```spl
(index=netfw OR index=netauth OR index=netops) "SC4S_SOPHOS_FIREWALL_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product vendor_product eventtype sophos_firewall_family log_id log_type log_component log_subtype severity status action vendor_raw_action signature signature_id src dest src_port dst_port transport user src_user fw_rule_id threat bytes_sent bytes_received device_name device_serial_id marker message _raw
```

Must verify: event count 5, expected indexes/sourcetypes, source `sophos_firewall`, host/device identity, `log_id`, severity/status, source/destination tuple, user for VPN/traffic rows, eventtype discovery metadata, and timestamp handling.

## Known limitations

- No real Sophos Firewall appliance or SFOS source-version replay/read-back evidence is captured.
- WAF/web-filter/wireless families are not included in the first pack despite public field references; add them only with exact event/source-shape evidence and tests.
- Sophos Central SIEM API JSON is explicitly out of scope for this pack and requires separate collector/API-relay handling.
- Vendor syslog field presence and quoting can vary by SFOS version/configuration; current fixtures are synthetic-equivalent required-field examples only.
