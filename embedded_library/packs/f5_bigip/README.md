# F5 BIG-IP

Curated SecHub Resources SC4S pack for F5 BIG-IP syslog and common iRule/ASM/JSON HSL variants. This pack promotes the upstream SC4S F5 BIG-IP inventory into a conservative SecHub Resources pack with explicit provenance, fixture semantics, Splunk knowledge, and validation gaps.

## Scope

- Vendor: F5
- Product: BIG-IP
- Covered families:
  - base BIG-IP syslog (`f5:bigip:syslog`)
  - TMM SSL connection errors, TCL errors, and traffic limiting events routed to F5 LTM sourcetypes
  - ASM/iRule security messages (`f5:bigip:asm:syslog`)
  - Splunk-style iRule DNS/HTTP/LB messages (`f5:bigip:*:irule`)
  - RFC5424 iRule JSON access messages (`f5:bigip:ltm:access_json`)
- Recommended transport: TLS/RFC5425 to a dedicated listener.

## Ingestion and collection notes

Typical ingestion is **push syslog/stream relay** from the appliance, controller, or an intermediate syslog/collector tier into the dedicated `tls` listener on port `20050` with source tag `F5_BIGIP`. Prefer a dedicated source tag/listener per product or source mode so SC4S routing does not depend on weak hostname or generic program-name matching. Route to index `netops` and sourcetype(s) `f5:bigip:syslog`, `f5:bigip:ltm:ssl:error`, `f5:bigip:ltm:tcl:error`, `f5:bigip:ltm:traffic`, and 6 more declared sourcetype(s).

Where logs arrive through a collector, use ingestion-time tooling only for safe envelope work: TLS termination, RFC3164/RFC5424 normalization, line splitting, source tagging, archive decompression, and routing metadata. Preserve raw message text and vendor tokens because firewall/network/security events often need exact rule/action/signature fields during incident review. Optional noise reduction must remain disabled by default and backed by replay/read-back plus rollback guidance.

If the product also offers API, CSV, ZIP/TGZ, or object-store exports, treat those as separate source-shape variants unless the emitted records match the fixture/schema assumptions in this pack.

## Provenance and evidence

Public evidence used:

- Upstream SC4S generated catalogue entries for `f5_bigip`, `f5_bigip_irule_asm`, `f5_bigip_irule_json`, `f5_bigip_irule_splunk`, and `f5_bigip_structured` from SC4S `v3.43.0` (`5206370a6e9e5a2f3389b82291f68f86fc91c337`).
- Upstream SC4S source documentation `docs/sources/vendor/F5/bigip.md`, including sourcetype/index guidance and the `access_json` RFC5424 example shape.
- Upstream SC4S parser source paths under `package/etc/conf.d/conflib/syslog/` and `package/etc/conf.d/conflib/netsource/` for F5 BIG-IP routing semantics.

The fixtures are synthetic-equivalent and sanitized. They preserve parser-relevant structure from the upstream parser/documentation but are **not** captured from a real BIG-IP device. Keep `quality_status=curated` and `trust_level=unverified` until real BIG-IP replay and Splunk read-back evidence exists.

## Fixture semantics

`test-events/f5_bigip_test_events.txt` contains nine one-line syslog fixtures. The manifest-level `bigip_syslog` family is an umbrella/base parser route: all nine fixtures exercise the base BIG-IP parser match first, then the SC4S parser updates final sourcetypes to the narrower TMM, ASM, iRule, or access-json families where their stronger signatures match. There is not yet a standalone fallback-only `f5:bigip:syslog` fixture; add one only after exact BIG-IP emitted-message evidence is available.

The fixture rows are:

1. BSD-style TMM SSL connection error with slot/host header (`SC4S_F5_BIGIP_TEST_TMM_SSL_001`).
2. BSD-style TMM TCL error routed to `f5:bigip:ltm:tcl:error` (`SC4S_F5_BIGIP_TEST_TMM_TCL_008`).
3. BSD-style TMM traffic limiting event routed to `f5:bigip:ltm:traffic` (`SC4S_F5_BIGIP_TEST_TMM_TRAFFIC_009`).
4. BSD-style ASM iRule message with Splunk-F5-ASM prefix (`SC4S_F5_BIGIP_TEST_ASM_002`).
5. BSD-style Splunk iRule DNS request message (`SC4S_F5_BIGIP_TEST_IRULE_DNS_003`).
6. BSD-style Splunk iRule DNS response message (`SC4S_F5_BIGIP_TEST_IRULE_DNS_RESPONSE_007`).
7. BSD-style Splunk iRule HTTP request message (`SC4S_F5_BIGIP_TEST_IRULE_HTTP_004`).
8. BSD-style Splunk iRule load-balancing failure message (`SC4S_F5_BIGIP_TEST_IRULE_LB_FAILED_005`).
9. RFC5424 JSON access iRule message using APP-NAME `F5` and MSGID `access_json` (`SC4S_F5_BIGIP_TEST_ACCESS_JSON_006`).

Each physical line is one event. BSD fixtures depend on syslog header time plus receiver/source timezone. The RFC5424 JSON fixture includes an explicit UTC timestamp. The send helper wraps lines over TLS/RFC5425 with octet-counting when used against an SC4S TLS listener.

## Expected sourcetypes

| Family | Expected sourcetype | Notes |
| --- | --- | --- |
| `bigip_syslog` | `f5:bigip:syslog` | Base/fallback BIG-IP syslog. |
| `bigip_tmm_ssl` | `f5:bigip:ltm:ssl:error` | Upstream parser routes matching TMM SSL connection errors; Splunk props extract fixture-backed `message_code` plus the numeric message-code severity token and use the message code as a non-lossy signature when available. |
| `bigip_tmm_tcl` | `f5:bigip:ltm:tcl:error` | Upstream parser routes matching TMM TCL errors; Splunk props extract fixture-backed `message_code` plus the numeric message-code severity token and eventtype `f5_bigip_ltm_tcl_error` is tagged as network/communicate/error. |
| `bigip_tmm_traffic` | `f5:bigip:ltm:traffic` | Upstream parser routes matching TMM traffic limiting messages; Splunk props extract fixture-backed `message_code`, `signature_id`, numeric message-code `severity`, `src_ip`, `src`, uppercase `transport`, and `packet_rate`; eventtypes include broad `f5_bigip_ltm_traffic` plus narrow `f5_bigip_ltm_traffic_limited` for events with `action=traffic_limit`, `packet_rate`, `src_ip`, and `transport`, both tagged as network/communicate. |
| `bigip_asm` | `f5:bigip:asm:syslog` | ASM/iRule security messages; default index `netwaf`; props preserve the fixture-backed ASM `support_id` as `signature_id` for correlation, keep `policy_name` for WAF policy triage, and surface the already-present `unit_hostname` in the manifest required-field coverage for appliance/member context. Narrow eventtype `f5_bigip_asm_attack` requires both `violations=*` and `support_id=*` for WAF/ASM analyst discovery without stating complete ASM CIM coverage. |
| `bigip_irule_dns_request` | `f5:bigip:gtm:dns:request:irule` | Splunk-style iRule DNS request category; fixture-backed eventtypes include broad `f5_bigip_irule_dns` plus narrow `f5_bigip_irule_dns_request` constrained to `qname=*`, both tagged as network/communicate. |
| `bigip_irule_dns_response` | `f5:bigip:gtm:dns:response:irule` | Splunk-style iRule DNS response category; fixture-backed eventtypes include broad `f5_bigip_irule_dns` plus narrow `f5_bigip_irule_dns_response` constrained to `qname=* rcode=*`, both tagged as network/communicate, and preserve the observed DNS `rcode` (for example `NOERROR`) for response-result searches. |
| `bigip_irule_http` | `f5:bigip:ltm:http:irule` | Splunk-style iRule HTTP request category; fixture-backed eventtype `f5_bigip_irule_http` is tagged as web/network/communicate. |
| `bigip_irule_lb_failed` | `f5:bigip:ltm:failed:irule` | Splunk-style iRule load-balancing failure category; fixture-backed eventtype `f5_bigip_irule_lb_failed` is tagged as network/communicate/error. Props preserve the virtual destination in `dest`/`dest_ip` and separately derive `pool_member_ip` plus `pool_member_port` from `member=<ip>:<port>` for pool-member triage. |
| `bigip_access_json` | `f5:bigip:ltm:access_json` | User-defined iRule JSON access messages; fixture-backed eventtype `f5_bigip_access_json` requires the observed `event_type`, `method`, and `uri` fields and is tagged as web/network/communicate. |

All F5 BIG-IP eventtypes also carry non-lossy `f5` and `bigip` tags so analysts can pivot by product family without relying only on sourcetype naming. These discovery tags do not imply complete CIM coverage or validation promotion.

## Validation harness and SPL

`pack.json` carries a blocked `validation_harness` requirements for the F5 BIG-IP pack. It is a runbook/status requirements, not validation evidence: replay is expected to use `scripts/send_tls_20050.sh` against the dedicated TLS/RFC5425 listener on port `20050`, produce nine `SC4S_F5_BIGIP_TEST_*` events in `index=netops`/`index=netwaf`, and verify Splunk read-back for count, index, sourcetype, source, host/fromhost, timestamp, raw preservation, normalized fields, and eventtypes/tags. The latest local preflight (`validation/preflight-2026-06-07.md`) found no TLS/RFC5425 listener on `127.0.0.1:20050`; `ss` returned only the header row, `openssl s_client` returned `connect:errno=111`, and local Splunk management/web ports `8089`/`8000` refused TCP connections. No fixture replay, SC4S/syslog-ng counter check, HEC delivery, or Splunk indexed read-back was performed.

For an idempotent disposable lab path, `scripts/e2e_docker_compose.sh` can write a local Compose stack, start Splunk TEST plus SC4S TEST, create `netops` and `netwaf`, replay all nine fixtures through the TLS/RFC5425 listener, and run summary/detail read-back SPL. The read-back stage now fails closed unless Splunk returns exactly nine indexed `SC4S_F5_BIGIP_TEST_` fixture events, so an empty or partial search cannot be mistaken for successful replay. Use `packs/f5_bigip/scripts/e2e_docker_compose.sh plan` to review the command sequence and evidence boundaries before running Docker. The harness is ready for lab execution only; it does not prove live BIG-IP appliance emission, BIG-IP version/module behavior, custom iRule payload completeness, ASM policy semantics, HEC delivery, Splunk indexed read-back, production readiness, or trust/quality promotion until it is actually run and retained evidence passes.

After importing through SC4S Manager or local SC4S validation, replay fixtures and query:

```spl
index IN (netops, netwaf) "SC4S_F5_BIGIP_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product action signature signature_id support_id policy_name unit_hostname violations f5_asm message_code severity src dest src_ip dest_ip pool dest_port pool_member_ip pool_member_port transport packet_rate f5_irule event_type method uri qname rcode reason member _raw
```

Expected count: 9 events with one marker per line and no drops. Standard eventtypes include broad F5/iRule groupings plus narrow fixture-backed TMM traffic-limiting, ASM attack, DNS request, DNS response, HTTP, load-balancing failure, and access JSON eventtypes for analyst searches; all carry product-family `f5`/`bigip` tags for discovery, but these tags do not imply complete CIM coverage. The readback requirements tables both the raw load-balancing pool context (`pool`, `member`) and derived pool-member fields (`pool_member_ip`, `pool_member_port`, `dest_port`) so reviewers can prove the virtual destination and pool-member endpoint were not conflated.
Standard props derive non-lossy `signature` values for fixture-backed TMM SSL/TCL errors, traffic limiting, HTTP iRule, load-balancing failure, and access JSON events from already-present fields such as `message_code`, `uri`, `reason`, `pool`, or the family label; this improves analyst search consistency without changing trust or quality statements. The validation SPL tables raw fixture-backed source-mode tokens such as `f5_irule` and `event_type` alongside derived `action` so reviewers can prove normalization did not hide the original iRule/access-json signal. ASM fixtures preserve the already-present `support_id` and surface it as `signature_id` for correlation; `policy_name` is retained for fixture-backed WAF policy triage, `unit_hostname` is documented in the manifest required-field coverage as sanitized appliance/member context, and the raw `f5_asm` helper identifier is tabled next to WAF fields so reviewers can prove the ASM source-mode token was preserved before analyst derivation. The `f5_bigip_asm_attack` eventtype is intentionally constrained to events that carry both `violations` and `support_id` so it supports WAF/ASM analyst discovery without stating validated ASM event identity semantics. DNS iRule fixtures also preserve the already-present `qname` and DNS response `rcode` fields through Splunk automatic key/value extraction; DNS requests now have their own narrow `f5_bigip_irule_dns_request` eventtype for request-only searches without relying on the broader request/response DNS grouping. For traffic limiting events, props extract the already-present TMM message code plus source IP, normalize the protocol token to uppercase `transport` (for example `ICMP`), preserve the packets-per-second rate from the fixture-backed `Limiting <proto> response from <ip> to <rate> packets/sec` message text, and add a narrow `f5_bigip_ltm_traffic_limited` eventtype constrained to `action=traffic_limit`, `packet_rate`, `src_ip`, and `transport` for rate-limit triage. TMM SSL/TCL/traffic stanzas also surface fixture-backed `message_code` as `signature_id` and extract the numeric message-code severity token (`4`, `3`, or similar) for analyst correlation; this is not a complete BIG-IP severity taxonomy. For load-balancing failure events, props also derive `dest_port`, `pool_member_ip`, and `pool_member_port` from the fixture-backed `member=<ip>:<port>` value when Splunk has not already supplied those pool-member fields, while preserving the virtual server destination in `dest`/`dest_ip`.

## Known limitations

- No real BIG-IP appliance replay or Splunk read-back evidence is included yet.
- BIG-IP module/program coverage is intentionally conservative; the upstream parser contains additional sourcetype refinements that should be validated with real event captures before further promotion.
- BSD syslog fixture timestamps do not include timezone offsets. Production deployments should prefer RFC5424/RFC5425 or explicitly configure source timezone handling.
- The JSON access iRule format is user-defined; the fixture follows the upstream SC4S documentation example shape but deployments may add custom keys.

## Next validation step

Capture real BIG-IP LTM/APM/ASM and iRule events from a lab or approved field source, replay through the dedicated listener, verify Splunk read-back fields/sourcetypes, and store sanitized evidence before promoting beyond curated/unverified quality.

## Splunk dashboard

`splunk/default/data/ui/views/f5_bigip_soc.xml` — SOC overview dashboard covering ingestion health, ASM WAF violations, SSL/TCL errors, LTM traffic limiting, load-balancer pool failures, HTTP and DNS iRule events, access JSON APM sessions, and drilldown SPL. Not field-validated; panels use synthetic-equivalent fixture evidence only.
