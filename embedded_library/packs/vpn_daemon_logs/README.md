# VPN daemon logs pack

Curated SecHub Resources SC4S pack for narrow OpenVPN and strongSwan daemon log relay paths. It is intended for dedicated source-tagged TCP syslog/file-agent/collector relay traffic, not as a generic `/var/log` parser.

## Scope and trust posture

- **Pack ID:** `vpn_daemon_logs`
- **Default index:** `netauth`
- **Default listener:** TCP 20078 (`VPN_DAEMON_LOGS` source tag)
- **Current quality:** `curated`
- **Current trust:** `unverified`

This pack uses public evidence captured in `docs/evidence/vpn-daemon-logs-evidence-scan-20260608.md`:

- OpenVPN upstream source templates for peer connection, certificate verification, initialization, virtual-IP assignment, pool-return assignment, and `AUTH_FAILED` rows.
- strongSwan documentation/upstream `_updown` examples for `vpn:` tunnel create/delete rows.

No live OpenVPN, strongSwan, or WireGuard relay was replayed through SC4S and read back from Splunk. CI/schema/fixture checks and the blocked local preflight do not promote trust.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tcp` listener on port `20078` with source tag `VPN_DAEMON_LOGS`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netauth` and sourcetype(s) `vpn:openvpn:peer`, `vpn:openvpn:verify`, `vpn:openvpn:session`, `vpn:openvpn:auth`, and 1 more declared sourcetype(s).

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Event families and sourcetypes

| Family | Sourcetype | Evidence basis | Notes |
| --- | --- | --- | --- |
| OpenVPN peer connection initiated | `vpn:openvpn:peer` | OpenVPN `socket.c` log template | Extracts peer endpoint IP/port when present. |
| OpenVPN certificate verification OK | `vpn:openvpn:verify` | OpenVPN `ssl_verify.c` log template | Preserves certificate depth and subject. |
| OpenVPN session initialized / virtual IP and pool assignment | `vpn:openvpn:session` | OpenVPN `init.c` and `multi.c` templates | Captures initialization, tunnel IP assignment, and `MULTI_sva` pool-return context. |
| OpenVPN authentication/cipher failure | `vpn:openvpn:auth` | OpenVPN docs/source `AUTH_FAILED` examples | Preserves raw failure reason. |
| strongSwan `_updown` tunnel create/delete | `vpn:strongswan:updown` | strongSwan `_updown` documented syslog rows | Preserves `+`/`-` raw action, peer ID/IP, local IP, and tunnel network. |

WireGuard is deliberately **not** parser-backed in this initial pack. Public evidence found during the scan supports only kernel-debug/dynamic-debug style messages; normal deployments may not emit routine WireGuard audit rows. Add a WireGuard variant only after lab journald/syslog evidence proves the exact relay shape.

## Fixture semantics

Fixture file: `test-events/vpn_daemon_logs_test_events.txt`

- Format: plain text daemon syslog payloads with RFC3164-style timestamp/host/program prefixes.
- Envelope: no outer transport envelope in the fixture file; the send helper sends one line per TCP record to the dedicated listener.
- Event count: 8.
- Event boundary: one event per line, newline-separated.
- Multiline: false.
- Timestamp policy: payload timestamps have month/day/time but no timezone/year; production relays should prefer timezone-qualified RFC5424/RFC5425 envelope timestamps or an explicit receiver-time policy.
- Values: synthetic-equivalent hostnames, identities, documentation IP ranges, tunnel networks, and markers. No customer logs, secrets, tenant identifiers, or proprietary TA content are included.

Unique markers:

```text
SC4S_VPN_DAEMON_LOGS_TEST_OPENVPN_PEER_001
SC4S_VPN_DAEMON_LOGS_TEST_OPENVPN_VERIFY_002
SC4S_VPN_DAEMON_LOGS_TEST_OPENVPN_INIT_003
SC4S_VPN_DAEMON_LOGS_TEST_OPENVPN_VIP_004
SC4S_VPN_DAEMON_LOGS_TEST_OPENVPN_POOL_005
SC4S_VPN_DAEMON_LOGS_TEST_OPENVPN_AUTH_FAILED_006
SC4S_VPN_DAEMON_LOGS_TEST_STRONGSWAN_UP_007
SC4S_VPN_DAEMON_LOGS_TEST_STRONGSWAN_DOWN_008
```

## Validation harness

Current harness status: **blocked**.

Last local preflight evidence: `validation/preflight-2026-06-08.md`.

The 2026-06-08 preflight found no local TCP listener on `127.0.0.1:20078`; local Splunk TEST ports `8089` and `8000` also refused TCP connections. Fixture replay, SC4S parser counters, HEC delivery, and indexed Splunk read-back were not attempted.

A disposable Docker/Compose E2E harness requirements is now available at `scripts/e2e_docker_compose.sh` for permitted lab use. `plan` and `write-compose` are safe planning modes; `run` starts Splunk TEST and SC4S TEST containers, creates `index=netauth`, replays all eight VPN daemon fixtures through TCP `20078`, and runs summary/detail read-back SPL for OpenVPN peer, certificate, session, auth-failure, and strongSwan `_updown` rows. A passing harness run would be fixture-route SC4S TEST -> Splunk TEST evidence only; it would not prove live OpenVPN/strongSwan source-version emission, distro syslog/journald wrappers, production TLS/RFC5425 transport, broader strongSwan `charon`/IKE coverage, WireGuard routine audit/debug rows, collector-specific envelopes, production readiness, or field validation.

Expected read-back SPL when a non-production testbed is available:

```spl
index=netauth "SC4S_VPN_DAEMON_LOGS_TEST_" earliest=-2h
| table _time index sourcetype source vendor product action result signature signature_id host process_id client_context peer_id peer_ip local_ip tunnel_network src src_ip src_port tunnel_ip pool_ipv4 pool_ipv6 user certificate_subject reason marker _raw
```

To promote above `curated`/`unverified`, capture evidence that proves event count, index, sourcetype, source, timestamps, vendor/product, raw vendor tokens, normalized fields, no unintended drops, and Splunk indexed read-back.

## Splunk dashboard

Dashboard artifact: `splunk/default/data/ui/views/vpn_daemon_logs_overview.xml`.

The dashboard is a fixture-backed onboarding and first-triage view for the currently declared OpenVPN and strongSwan sourcetypes. It covers arrival volume, sourcetype/family distribution, OpenVPN authentication failures, OpenVPN peer/session/virtual-IP and pool-return context, certificate verification context, strongSwan tunnel up/down rows, peer/source endpoint summaries, onboarding coverage by source/host, and recent raw relay rows.

Dashboard panels intentionally use only fields proven by `test-events/vpn_daemon_logs_test_events.txt` and `splunk/default/props.conf`: `action`, `result`, `signature`, `signature_id`, `client_context`, `peer_id`, `src_ip`, `src_port`, `tunnel_ip`, `pool_ipv4`, `pool_ipv6`, `peer_ip`, `local_ip`, `tunnel_network`, `vendor_raw_action`, `reason`, `cert_depth`, `certificate_subject`, and `marker`. The dashboard does not state WireGuard coverage, broader strongSwan `charon`/IKE log coverage, generic Linux VPN logs, collector health/checkpointing, or replay/read-back validation.

## Reduction review

No default drops or lossy field removal are shipped.

Security-relevant fields/events retained by default:

- OpenVPN peer/source endpoint, certificate subject/depth, session initialized state, tunnel IP and pool assignment, `AUTH_FAILED` reason, and fixture marker context.
- strongSwan tunnel up/down raw action, peer identity, peer IP, local IP, and tunnel network.
- Raw vendor action/status strings before analyst normalization.

Potential future reduction candidates are advisory only and documented in `docs/vpn_daemon_logs_reduction_candidates.csv`. High-volume OpenVPN success/verification/session chatter might be review candidates in some environments, but only after local replay/read-back proves the retained evidence is sufficient and rollback is documented.

## Known limitations

- No live daemon relay, SC4S runtime replay, HEC delivery, Splunk read-back, Manager apply, or production evidence captured.
- OpenVPN fixtures are source-template-derived, not live server captures.
- strongSwan structured coverage is limited to documented `_updown` `vpn:` rows; broader `charon` IKE/CHILD_SA logs need exact samples or lab capture.
- WireGuard routine audit coverage remains blocked/deferred until a kernel-debug/journald testbed capture exists.
- Distro syslog/journald wrappers vary; use the dedicated listener/source tag and validate the actual local relay envelope before production use.
