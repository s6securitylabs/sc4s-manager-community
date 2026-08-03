# Zeek JSON logs

Curated SecHub Resources pack for Zeek logs written as one JSON object per line. The scope is deliberately conservative and fixture-backed for fifteen high-value Zeek log families: `conn`, `dns`, `http`, `ssl`, `notice`, `files`, `x509`, `ssh`, `dhcp`, `rdp`, `weird`, `software`, `known_hosts`, `intel`, and `smtp`.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20083` with source tag `ZEEK_JSON_LOGS`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `netids` / sourcetype(s) `zeek:json`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Evidence and provenance

Primary public evidence:

- Zeek logging framework documentation in the public docs repository states that ASCII logs can be written as JSON with `redef LogAscii::use_json = T`: `https://raw.githubusercontent.com/zeek/zeek-docs/master/frameworks/logging.rst`.
- Zeek `conn.log` documentation and source record fields: `https://raw.githubusercontent.com/zeek/zeek-docs/master/logs/conn.rst` and `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/protocols/conn/main.zeek`.
- Zeek source record definitions for DNS, HTTP, SSL/TLS, Notice, Files, X.509, SSH, DHCP, RDP, Weird, Software, Known Hosts, Intel framework matches, and SMTP transactions: `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/protocols/dns/main.zeek`, `.../http/main.zeek`, `.../ssl/main.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/frameworks/notice/main.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/frameworks/files/main.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/files/x509/main.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/protocols/ssh/main.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/protocols/dhcp/main.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/protocols/rdp/main.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/frameworks/notice/weird.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/frameworks/software/main.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/policy/protocols/conn/known-hosts.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/frameworks/intel/main.zeek`, `https://raw.githubusercontent.com/zeek/zeek/master/scripts/base/protocols/smtp/main.zeek`, and `https://raw.githubusercontent.com/zeek/zeek-docs/master/logs/smtp.rst`.
- Parser ecosystem corroboration only: Elastic/Filebeat Zeek module documentation confirms common Zeek module handling. No Elastic ingest pipeline or third-party parser code is copied into this pack.

Fixtures are synthetic-equivalent records shaped from public Zeek record-field definitions. They use RFC5737 documentation IP addresses, `example.test` names, synthetic UIDs, and explicit marker fields. No production PCAP-derived logs, tenant identifiers, or customer data are included.

## Source shape

- **Delivery model:** one Zeek JSON log record per line from Zeek ASCII JSON output, file tail, syslog wrapper, Fluent Bit/Vector/Cribl, or another relay.
- **Wire/envelope:** fixture file is headerless JSONL; helper script wraps each payload in an RFC5424-style line for the dedicated TCP listener.
- **Timestamp:** source `ts` is ISO-8601 UTC in fixtures. Zeek deployments can also emit epoch timestamps depending on writer configuration; those variants need local confirmation before promotion.
- **Event boundary:** one JSON object per line. Zeek TSV logs are explicitly out of scope for this first pack.
- **Default index/sourcetype:** `netids` / `zeek:json`.

## Included event families

| Family | Evidence-backed fields | Notes |
| --- | --- | --- |
| `conn` | `uid`, `id.orig_h`, `id.orig_p`, `id.resp_h`, `id.resp_p`, `proto`, `service`, `duration`, `orig_bytes`, `resp_bytes`, `conn_state`, packet counters | Flow summary; not NetFlow/IPFIX validation. |
| `dns` | `uid`, tuple fields, `trans_id`, `query`, `qtype_name`, `rcode_name`, `answers`, `TTLs` | DNS query/response metadata only. |
| `http` | `uid`, tuple fields, `method`, `host`, `uri`, `user_agent`, body lengths, `status_code`, `status_msg` | HTTP request/response summary; body capture is not included. |
| `ssl` | `uid`, tuple fields, `version`, `cipher`, `server_name`, `established`, `subject`, `issuer`, `validation_status` | TLS handshake metadata; certificate-chain detail depends on local Zeek configuration. |
| `notice` | `uid`, tuple fields or `src`/`dst`/`p`, `note`, `msg`, `sub`, `actions`, `suppress_for` | Zeek notice framework events; local notice policy changes field presence. |
| `files` | `fuid`, `tx_hosts`, `rx_hosts`, `conn_uids`, `source`, `mime_type`, `filename`, byte counters, optional hashes | File analysis metadata; not proof of full file extraction or hash availability in every deployment. |
| `x509` | `id`, `certificate.subject`, `certificate.issuer`, `certificate.serial`, certificate validity fields, key/signature context | Certificate metadata emitted by Zeek x509 scripts; local certificate logging and nested-field shape must be verified. |
| `ssh` | `uid`, tuple fields, `auth_success`, `auth_attempts`, client/server strings, cipher/MAC/KEX/host-key algorithms | SSH handshake/auth metadata; no packet payload or credential capture. |
| `dhcp` | `uids`, `client_addr`, `server_addr`, `client_port`, `server_port`, `mac`, `host_name`, `requested_addr`, `assigned_addr`, `lease_time`, `msg_types`, `duration` | DHCP transaction/lease conversation metadata; not a full DHCP option inventory or lease-state validator. |
| `rdp` | `uid`, tuple fields, `cookie`, `result`, `security_protocol`, `client_channels`, `keyboard_layout`, `client_build`, `client_name`, desktop/certificate/encryption context | RDP negotiation/client context; cookie may be a truncated username and requires local privacy review before broad analyst exposure. |
| `weird` | `uid`, tuple fields, `name`, `addl`, `notice`, `peer`, `source` | Unusual/exceptional activity metadata; not a substitute for local notice policy review. |
| `software` | `host`, `host_p`, `software_type`, `name`, `version.*`, `unparsed_version` | Software/version detection metadata; local protocol analyzers determine coverage and logging frequency. |
| `known_hosts` | `host` | Daily/default host-discovery inventory from the Zeek known-hosts policy script; not endpoint asset validation. |
| `intel` | `uid`, tuple fields, `seen.indicator`, `seen.indicator_type`, `seen.where`, `matched`, `sources` | Intelligence-framework match context; not proof of feed quality, IOC lifecycle, or local intel matching policy. |
| `smtp` | `uid`, tuple fields, `helo`, `mailfrom`, `rcptto`, `date`, `from`, `to`, `subject`, `msg_id`, `last_reply`, `path`, and `user_agent` | SMTP transaction/message metadata from Zeek SMTP::Info; encrypted submission paths, local analyzer policy, and message-content privacy handling must be reviewed locally. |

Other Zeek logs such as package-specific logs and local package extensions remain future coverage until fixture-backed variants and read-back requirements are added.

## Splunk dashboard

This pack includes `splunk/default/data/ui/views/zeek_json_logs_overview.xml`, a fixture-backed Splunk SimpleXML overview for onboarding and first triage. It follows the network-security/NSM dashboard pattern from the local dashboard target-shape guidance and F5/VMware-style operational exemplars: arrival health, Zeek family coverage, notice/HTTP/DNS risk counters, source/destination tuple context, DNS/HTTP/TLS/notice/file/certificate/SSH triage tables, onboarding coverage, and recent raw-event drilldown.

Dashboard panels are constrained to the fifteen fixture-backed families (`conn`, `dns`, `http`, `ssl`, `notice`, `files`, `x509`, `ssh`, `dhcp`, `rdp`, `weird`, `software`, `known_hosts`, `intel`, and `smtp`) and fields present in `test-events/zeek_json_logs_test_events.txt` plus Splunk JSON/search-time knowledge: `zeek_log_type`, `uid`, `src_ip`/`src_port`, `dest_ip`/`dest_port`, `transport`, `service`, `conn_state`, `dns_query`, `dns_query_type`, `rcode_name`, `answers`, `http_method`, `http_status`, `url`, `user_agent`, `tls_sni`, `tls_version`, `cipher`, `validation_status`, `note`, `msg`, `file_id`, `file_name`, `file_mime_type`, `file_seen_bytes`, `file_total_bytes`, `file_md5`, `x509_subject`, `x509_issuer`, `x509_serial`, `ssh_auth_success`, `ssh_client`, `ssh_server`, `ssh_cipher_alg`, `dhcp_client_addr`, `dhcp_server_addr`, `dhcp_mac`, `dhcp_host_name`, `dhcp_assigned_addr`, `dhcp_msg_types`, `rdp_cookie`, `rdp_result`, `rdp_security_protocol`, `rdp_client_name`, `weird_name`, `weird_addl`, `weird_notice`, `weird_source`, `software_host`, `software_port`, `software_type`, `software_name`, `software_version`, `known_host`, `intel_indicator`, `intel_indicator_type`, `intel_seen_where`, `intel_matched_types`, `intel_sources`, `smtp_helo`, `smtp_mailfrom`, `smtp_rcptto`, `smtp_subject`, `smtp_last_reply`, `action`, `signature`, `signature_id`, `bytes_in`, `bytes_out`, and `marker`. It does not state coverage for Zeek TSV logs, local package-specific logs beyond the fixture-backed Intel/SMTP rows, exact local Zeek timestamp variants, collector-envelope behavior, IOC feed quality, message-content privacy decisions, or live SC4S/Splunk replay/read-back.

## Splunk fields and validation SPL

Expected non-lossy fields after Splunk search-time extraction include:

```spl
index=netids "SC4S_ZEEK_JSON_TEST_" earliest=-2h
| table _time index sourcetype source vendor product zeek_log_type uid src_ip src src_port dest_ip dest dest_port transport action signature signature_id dns_query dns_query_type http_method http_status url tls_sni tls_version bytes_in bytes_out file_id file_name file_mime_type file_seen_bytes file_total_bytes file_md5 x509_id x509_subject x509_issuer x509_serial x509_not_valid_before x509_not_valid_after ssh_auth_success ssh_client ssh_server ssh_cipher_alg ssh_host_key_alg dhcp_client_addr dhcp_server_addr dhcp_mac dhcp_host_name dhcp_assigned_addr dhcp_msg_types rdp_cookie rdp_result rdp_security_protocol rdp_client_name weird_name weird_addl weird_notice weird_source software_host software_port software_type software_name software_version known_host intel_indicator intel_indicator_type intel_seen_where intel_matched_types intel_sources smtp_helo smtp_mailfrom smtp_rcptto smtp_subject smtp_last_reply marker _raw
```

The validation harness in `pack.json` uses the same read-back field set. It is a requirements only; it has not passed because no local SC4S/Splunk testbed was available in this run.

## Disposable E2E harness requirements

`packs/zeek_json_logs/scripts/e2e_docker_compose.sh` provides a runnable Docker/Compose harness requirements for a permitted disposable lab. The harness can write a local Compose file, start Splunk TEST plus SC4S TEST, create `index=netids`, replay all 15 Zeek JSON fixtures through TCP `20083`, sample SC4S/syslog-ng counters, and run summary/detail Splunk read-back SPL over the `SC4S_ZEEK_JSON_TEST_` markers.

Useful modes:

```bash
packs/zeek_json_logs/scripts/e2e_docker_compose.sh plan
packs/zeek_json_logs/scripts/e2e_docker_compose.sh run
packs/zeek_json_logs/scripts/e2e_docker_compose.sh down
```

The harness is execution tooling only until it is actually run and retained as evidence. It does not prove live Zeek sensor/source-version emission, LogAscii timestamp variants, collector wrappers, file-tail buffering, syslog envelope rewrites, HEC delivery, Splunk indexed read-back, production readiness, or trust promotion by itself.

## Reduction posture

No default drops, null queues, lossy redaction, or field trimming are shipped. `docs/zeek_json_logs_reduction_candidates.csv` is advisory only and covers review-required candidates such as high-volume successful `conn` summaries, URI query-string handling, certificate-chain verbosity, and repeated notice suppression. Any reduction must be enabled outside the basic/standard presets only after local replay/read-back proves event counts, UIDs, source/destination tuples, family fields, and rollback behavior.

## Current validation status

- Quality: `curated`.
- Trust: `unverified`.
- Local schema/fixture/pack validation: handled by repository CI.
- Live SC4S replay and Splunk indexed read-back: **not performed**.
- Blocked preflight evidence: `validation/preflight-2026-06-13.md` records that no local listener/Splunk TEST route was available in this repository run.

This pack must not be described as validated, S6 verified, field validated, or deployment-approved until replay/read-back evidence proves the intended route with real or production-equivalent Zeek JSON data.

## Splunk Edge Processor template candidates

This pack now includes file-backed Splunk Edge Processor candidate artifacts under `edge-processor/`:

- `edge-processor/modules/zeek_json_routine_conn_reduce.spl2` — conservative SPL2 module candidate that annotates and routes events unchanged by default.
- `edge-processor/templates/zeek_json_routine_conn_reduce.json` — metadata for source-type definitions, transforms, destination placeholders, lossy behavior, required validation, rollback, and review status.
- `edge-processor/samples/zeek_json_routine_conn_reduce.raw.txt` and `.parsed.jsonl` — synthetic-equivalent snippets for preview/review only.
- `edge-processor/validation/zeek_json_routine_conn_reduce-preflight.md` — explicit preflight and rollback checklist.

No Edge Processor validation/read-back is published. Any reduction remains opt-in and must pass non-production preview, replay/read-back, detection impact review, and rollback approval before use.
