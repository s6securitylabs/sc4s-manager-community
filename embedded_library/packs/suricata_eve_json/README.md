# Suricata EVE JSON

Curated SecHub Resources pack for Suricata EVE JSON records relayed as one JSON object per line. The current scope is intentionally narrow and evidence-backed: `alert`, `dns`, `http`, `tls`, `flow`, `fileinfo`, `anomaly`, `ssh`, `dhcp`, `rdp`, `ftp`, `krb5`, `smb`, `mqtt`, `http2`, `pgsql`, `netflow`, `arp`, `ike`, `modbus`, `quic`, and `pop3` events using the documented EVE common fields (`timestamp`, `flow_id`, `event_type`, network tuple fields, `proto`, `app_proto`) plus the nested event object for each family.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20082` with source tag `SURICATA_EVE_JSON`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `netids` / sourcetype(s) `suricata:eve`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Evidence and provenance

Primary public evidence:

- Official Suricata EVE JSON output documentation: `https://docs.suricata.io/en/latest/output/eve/eve-json-output.html`.
- Official Suricata EVE JSON format documentation: `https://docs.suricata.io/en/latest/output/eve/eve-json-format.html`.
- Official Suricata jq examples for EVE records: `https://docs.suricata.io/en/latest/output/eve/eve-json-examplesjq.html`.
- Public Suricata repository/configuration evidence for `eve-log` output and `eve.json` paths: `https://github.com/OISF/suricata`.
- Parser ecosystem corroboration only: Elastic Suricata EVE integration and Filebeat Suricata module show common EVE parsing expectations, but no Elastic pipeline content is copied into this pack.

Fixtures in this pack are synthetic-equivalent records derived from public field-shape documentation. They use RFC5737 documentation IP ranges, `example.test` hostnames, and synthetic signatures/flow IDs. No customer sensor data, tenant identifiers, tokens, or raw production alerts are included.

## Source shape

- **Delivery model:** one Suricata EVE JSON event per line from `eve.json`, syslog output, file tail, Fluent Bit/Vector/Cribl, or another relay.
- **Wire/envelope:** fixture file is headerless JSONL; helper script wraps each payload in an RFC5424-style line for the dedicated TCP listener.
- **Timestamp:** EVE `timestamp` field with numeric offset, parsed by Splunk props. SC4S/syslog wrapper time is transport metadata and should not replace the source event time.
- **Event boundary:** one JSON object per line; multiline JSON is not covered.
- **Default index/sourcetype:** `netids` / `suricata:eve`.

## Included event families

| Family | Evidence-backed fields | Notes |
| --- | --- | --- |
| `alert` | `alert.action`, `alert.signature_id`, `alert.signature`, `alert.category`, `alert.severity`, network tuple | IDS alert triage; not a statement of ruleset validation. |
| `dns` | `dns.rrname`, `dns.rrtype`, `dns.type`, `dns.id`, network tuple | Conservative DNS query fixture only. |
| `http` | `http.hostname`, `http.url`, `http.http_method`, `http.status`, `http.http_user_agent` | Common HTTP metadata; custom headers are deployment-specific. |
| `tls` | `tls.sni`, `tls.version`, `tls.subject`, `tls.issuer`, `tls.fingerprint` | TLS metadata only; certificate-chain completeness depends on local Suricata config. |
| `flow` | `flow.pkts_*`, `flow.bytes_*`, `flow.state`, `flow.reason`, `flow.action` | Flow accounting context; not NetFlow/IPFIX validation. |
| `fileinfo` | `fileinfo.filename`, `fileinfo.state`, `fileinfo.size`, `fileinfo.tx_id`, HTTP context when present | File transaction metadata; file storage/extraction policy is deployment-specific. |
| `anomaly` | `anomaly.type`, `anomaly.event`, packet/network tuple | Decode/stream/application anomaly triage; packet payload capture is not fixture-backed. |
| `ssh` | `ssh.client.software_version`, `ssh.server.software_version`, optional HASSH hashes | SSH protocol/software metadata; HASSH requires local Suricata configuration. |
| `dhcp` | `dhcp.type`, `dhcp.dhcp_type`, `dhcp.id`, `dhcp.client_mac`, `dhcp.assigned_ip`, `dhcp.requested_ip`, `dhcp.hostname`, lease timers | DHCP address-mapping/lease context; extended fields depend on local Suricata DHCP logging mode. |
| `rdp` | `rdp.tx_id`, `rdp.event_type`, `rdp.protocol`, `rdp.cookie`, `rdp.client.client_name`, flags | RDP negotiation/client context only; this is not complete RDP session or credential validation. |
| `ftp` | `ftp.command`, `ftp.command_data`, `ftp.reply`, `ftp.completion_code`, `ftp.mode`, `ftp.reply_received` | FTP command/reply context only; payload/file extraction policy and data-channel coverage are deployment-specific. |
| `krb5` | `krb5.msg_type`, `krb5.cname`, `krb5.realm`, `krb5.sname`, `krb5.encryption`, weak-encryption flags, optional `krb5.error_code` | Kerberos protocol metadata; this is not Active Directory/domain-controller validation or complete authentication semantics. |
| `smb` | `smb.command`, `smb.status`, `smb.status_code`, `smb.filename`, `smb.share`, `smb.share_type`, transaction/session/tree IDs | SMB file/share/pipe transaction context only; not Windows file-server audit validation or complete authentication semantics. |
| `mqtt` | `mqtt.publish.topic`, QoS/retain/dup/message ID, acknowledgement context | MQTT transaction context; payload semantics and broker/client identity vary by deployment and must be locally reviewed before reduction. |
| `http2` | HTTP/2 request/response header arrays, pseudo-headers such as `:authority`, `:method`, `:path`, and `:status` when extracted | HTTP/2 metadata only; header capture and privacy posture depend on local Suricata configuration. |
| `pgsql` | `pgsql.tx_id`, `pgsql.request.simple_query`, `pgsql.response.command_completed`, `pgsql.response.data_rows`, `pgsql.response.data_size` | PostgreSQL transaction metadata only; query text can be sensitive and local `passwords`/payload options must be reviewed before reduction. |
| `netflow` | `netflow.pkts`, `netflow.bytes`, `netflow.start`, `netflow.end`, `netflow.age`, TTL range, optional transaction count | Suricata EVE Netflow accounting context; not IPFIX/NetFlow exporter validation. |
| `arp` | `arp.hw_type`, `arp.proto_type`, `arp.opcode`, `arp.src_mac`, `arp.dest_mac`, ARP source/destination IPs | ARP request/reply visibility; not endpoint inventory validation or ARP-spoofing detection validation. |
| `ike` | `ike.init_spi`, `ike.resp_spi`, `ike.version_major`, `ike.exchange_type`, `ike.exchange_type_verbose`, algorithm fields | IKE VPN negotiation metadata only; not VPN authentication outcome, tunnel state, or IPsec policy validation. |
| `modbus` | `modbus.id`, request/response `transaction_id`, `unit_id`, `function_code`, `access_type`, `category`, `error_flags` | Modbus industrial protocol transaction metadata only; not control-system process validation, device inventory validation, or safety/availability assessment. |
| `quic` | `quic.version`, `quic.sni`, `quic.ja3.hash`, `quic.ja3s.hash`, `quic.ja4`, CYU hash/string | QUIC handshake/fingerprint metadata only; not encrypted-traffic attribution, application identity validation, or complete QUIC session semantics. |
| `pop3` | `pop3.request.command`, `pop3.request.args`, `pop3.response.success`, `pop3.response.status`, `pop3.response.header` | POP3 command/response metadata only; not mailbox access validation, credential outcome proof, or mail-content capture. |

Suricata supports more EVE event types (`stats` and others). The current hardening passes add `smb`, `mqtt`, `http2`, `pgsql`, `netflow`, `arp`, `ike`, `modbus`, `quic`, and `pop3` fixture coverage from the public Suricata EVE format documentation and extend the SC4S parser route for those families. Other EVE families remain future work until exact source-shape coverage and local replay/read-back are added; `stats` remains deferred because it requires separate high-volume routing/read-back review beyond the current event-family expansion.

## Splunk fields and validation SPL

Expected non-lossy fields after Splunk search-time extraction include:

```spl
index=netids "SC4S_SURICATA_EVE_TEST_" earliest=-2h
| table _time index sourcetype source vendor product suricata_eve_family event_type src_ip src src_port dest_ip dest dest_port transport app action signature signature_id severity dns_query dns_query_type http_method http_status url tls_sni tls_version bytes_in bytes_out file_name file_state file_size anomaly_type anomaly_event ssh_client_software ssh_server_software ssh_client_hassh ssh_server_hassh dhcp_type dhcp_client_mac dhcp_assigned_ip dhcp_requested_ip dhcp_hostname dhcp_lease_time rdp_tx_id rdp_type rdp_protocol rdp_cookie rdp_client_name ftp_command ftp_command_data ftp_completion_code ftp_reply krb5_msg_type krb5_client krb5_service krb5_realm krb5_encryption krb5_error_code smb_command smb_status smb_status_code smb_filename smb_share smb_share_type mqtt_topic mqtt_message_id mqtt_qos mqtt_retain mqtt_client_id http2_authority http2_method http2_path http2_status http2_user_agent pgsql_tx_id pgsql_query pgsql_command_completed pgsql_data_rows pgsql_data_size netflow_pkts netflow_bytes netflow_age netflow_min_ttl netflow_max_ttl arp_hw_type arp_proto_type arp_opcode arp_src_mac arp_dest_mac ike_init_spi ike_resp_spi ike_version_major ike_exchange_type ike_exchange_type_verbose ike_alg_enc ike_alg_hash ike_alg_auth ike_alg_dh modbus_id modbus_transaction_id modbus_unit_id modbus_request_function modbus_response_function modbus_access_type modbus_category modbus_error_flags quic_version quic_sni quic_ja3_hash quic_ja3s_hash quic_ja4 quic_cyu_hash pop3_command pop3_args pop3_success pop3_status pop3_header marker _raw
```

The validation harness in `pack.json` uses the same read-back field set. It is a requirements only; it has not passed because no local SC4S/Splunk testbed was available in this run.

## Disposable SC4S TEST -> Splunk TEST harness

`packs/suricata_eve_json/scripts/e2e_docker_compose.sh` now provides an idempotent Docker/Compose lab requirements for operators who have permission to run disposable containers:

```bash
packs/suricata_eve_json/scripts/e2e_docker_compose.sh plan
packs/suricata_eve_json/scripts/e2e_docker_compose.sh run
```

The harness writes `.tmp/e2e/suricata_eve_json/compose.yaml`, starts disposable Splunk and SC4S containers, creates `index=netids`, mounts this pack's Splunk knowledge and SC4S parser artifacts read-only, sends all 22 synthetic-equivalent EVE JSON fixtures through TCP `20082`, and runs summary/detail read-back SPL over `SC4S_SURICATA_EVE_TEST_*` markers.

A passing harness run would be lab replay/read-back evidence for the fixture-backed Suricata EVE JSON relay shape only. It would still not prove live Suricata sensor/source-version emission, ruleset behavior, local `eve-log` configuration, collector wrapper/file-tail/archive handling, non-EVE/TSV outputs, high-volume `stats` routing, real PCAP-derived traffic coverage, production readiness, or field validation. Retain command output and Splunk read-back evidence before using it for any future trust promotion.

## Dashboard scope

This pack includes a fixture-backed Splunk SimpleXML overview dashboard at `splunk/default/data/ui/views/suricata_eve_json_overview.xml`. The dashboard follows the network-security/NSM operator pattern used by the local F5 BIG-IP and Zeek exemplars: arrival health, EVE family distribution, alert and HTTP/severity risk counters, source/destination tuple context, alert/DNS/HTTP/TLS/flow/fileinfo/anomaly/SSH/DHCP/RDP/FTP/KRB5/SMB/MQTT/HTTP2/PGSQL/Netflow/ARP/IKE/Modbus/QUIC/POP3 triage tables, onboarding coverage, and raw-event drilldown.

Dashboard panels are intentionally limited to fields proven by `test-events/suricata_eve_json_test_events.txt` and `splunk/default/props.conf`, including `suricata_eve_family`, `event_type`, `flow_id`, network tuple fields, `transport`, `app`, `action`, `signature`, `signature_id`, `severity`, DNS/HTTP/TLS/flow/fileinfo/anomaly/SSH/DHCP/RDP/FTP/KRB5 fields, plus `smb_command`, `smb_status`, `smb_filename`, `smb_share`, `mqtt_topic`, `mqtt_qos`, `http2_authority`, `http2_method`, `http2_path`, `http2_status`, `marker`, and preserved nested JSON fields such as `smb.session_id`, `mqtt.puback.message_id`, and HTTP/2 header arrays, PGSQL transaction summaries, Netflow accounting fields, ARP request/reply fields, IKE negotiation fields, and Modbus request/response function/access fields, QUIC fingerprint fields, and POP3 command/response fields.

The dashboard does not state coverage for Suricata TSV logs, non-EVE outputs, additional EVE families such as `stats`, collector-envelope behavior, ruleset quality, industrial-control process validation, or live replay/read-back validation.

## Reduction posture

No default drops, null queues, lossy redaction, or field trimming are shipped. `docs/suricata_eve_json_reduction_candidates.csv` is advisory only and covers review-required candidates such as payload/packet retention, stats-event volume, and HTTP query-string handling. Any reduction must be enabled outside the basic/standard presets only after local replay/read-back proves event counts, alert/dns/http/tls/flow triage fields, and rollback behavior.

## Current validation status

- Quality: `curated`.
- Trust: `unverified`.
- Local schema/fixture/pack validation: handled by repository CI.
- Live SC4S replay and Splunk indexed read-back: **not performed**.
- Blocked preflight evidence: `validation/preflight-2026-06-13.md` shows no local TCP listener on `127.0.0.1:20082` and unavailable local Splunk TEST ports at the time of curation.

This pack must not be described as validated, S6 verified, field validated, or deployment-approved until replay/read-back evidence proves the intended route with real or production-equivalent Suricata EVE data.

## Splunk Edge Processor template candidates

This pack now includes file-backed Splunk Edge Processor candidate artifacts under `edge-processor/`:

- `edge-processor/modules/suricata_eve_flow_reduce.spl2` — conservative SPL2 module candidate that annotates and routes events unchanged by default.
- `edge-processor/templates/suricata_eve_flow_reduce.json` — metadata for source-type definitions, transforms, destination placeholders, lossy behavior, required validation, rollback, and review status.
- `edge-processor/samples/suricata_eve_flow_reduce.raw.txt` and `.parsed.jsonl` — synthetic-equivalent snippets for preview/review only.
- `edge-processor/validation/suricata_eve_flow_reduce-preflight.md` — explicit preflight and rollback checklist.

No Edge Processor validation/read-back is published. Any reduction remains opt-in and must pass non-production preview, replay/read-back, detection impact review, and rollback approval before use.
