# Nginx / Apache HTTP access-log pack

Conservative SecHub Resources SC4S pack for common Nginx and Apache httpd HTTP access-log relay lines plus selected documentation-shaped error-log rows. Scope remains intentionally narrow: Nginx combined access logs, Apache Common Log Format, Apache Combined Log Format, Nginx core error-log rows, and Apache httpd ErrorLog-style rows as documented by the upstream web-server projects.

This is curated intake guidance, not live web-server validation. Trust remains `unverified` and quality remains `curated` until real Nginx/Apache relay replay and Splunk indexed read-back evidence exists.

## Evidence searched

- `docs/evidence/nginx-apache-http-evidence-scan-20260608.md` records reachable Nginx and Apache official documentation for access-log directives, Common Log Format, Combined Log Format, token semantics, Nginx `error_log` examples, and Apache httpd `ErrorLogFormat` / error-log examples.
- Fixtures use synthetic-equivalent values derived from documented structure only.
- JSON/custom access formats, reverse-proxy timing extensions, WAF/security module logs, application access logs, debug/custom error formats, and collector-enriched wrappers are deferred until exact emitted-record evidence or a testbed is available.

## Scope

- Listener: dedicated TCP syslog example on port `20075` with source tag `NGINX_APACHE_HTTP`.
- Payloads: one access-log record per line.
- Routed sourcetypes: `nginx:access:combined`, `apache:httpd:access:common`, `apache:httpd:access:combined`, `nginx:error`, and `apache:httpd:error`.
- Default index: `netops`.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tcp` listener on port `20075` with source tag `NGINX_APACHE_HTTP`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `netops` and sourcetype(s) `nginx:access:combined`, `apache:httpd:access:common`, `apache:httpd:access:combined`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Fixture semantics

- File: `test-events/nginx_apache_http_test_events.txt`.
- Format: raw access-log and error-log payload lines with synthetic documentation-shaped values.
- Wire/envelope: headerless fixture payloads; `scripts/send_tcp_20075.sh` wraps each line in an RFC5424-style syslog header for TCP replay.
- Event splitting: one event per physical line; multiline errors, debug logs, arbitrary custom formats, and collector JSON wrappers are out of scope.
- Timestamp: access fixtures use bracketed access-log timestamps with explicit numeric timezone offsets (`%d/%b/%Y:%H:%M:%S %z`); Nginx error fixtures use leading `YYYY/MM/DD HH:MM:SS`; Apache error fixtures use bracketed weekday/month/day/time/microsecond/year values.
- Delimiting: space-delimited CLF/combined fields with quoted request, referrer, and user-agent fields where the documented format includes them; error-log rows use product-specific bracket/prefix context plus comma-delimited client/request/host/referrer attributes where documented.
- Markers: `SC4S_NGINX_APACHE_HTTP_TEST_*` values each occur exactly once.
- Sanitisation: fixtures use RFC5737 addresses, example paths/hostnames, neutral users, synthetic process/thread/connection IDs, and synthetic user-agent/referrer strings only.

Validation SPL smoke pattern:

```spl
index=netops "SC4S_NGINX_APACHE_HTTP_TEST_" earliest=-2h
| table _time index sourcetype source vendor product eventtype src_ip src client_ip client_port user ident http_method uri_path url http_version status bytes bytes_out http_referrer http_user_agent error_level module error_code process_id tid connection_id server host_header request error_message action signature signature_id marker _raw
```

## Disposable E2E harness

`pack.json` now registers `scripts/e2e_docker_compose.sh` as an idempotent Docker/Compose harness for a permitted SC4S TEST -> Splunk TEST run. Use `packs/nginx_apache_http/scripts/e2e_docker_compose.sh plan` to print the evidence stages without requiring Docker, or `... run` in an approved disposable lab to stand up Splunk + SC4S, replay all five fixture records through TCP `20075`, and query `index=netops` for the expected Nginx/Apache sourcetypes and fields.

The harness is a runnable validation requirements, not validation evidence by itself. Passing it would prove only the fixture-backed Nginx combined, Apache common/combined, Nginx error, and Apache error source shapes in that disposable test path. It does not prove real web-server source-version emission, local `log_format` / `ErrorLogFormat` customisations, reverse-proxy timing fields, WAF/security modules, collector wrappers, source-local timezone behaviour, or field validation.

## Splunk dashboard

This pack includes `splunk/default/data/ui/views/nginx_apache_http_overview.xml`, a fixture-backed onboarding and first-triage dashboard for the five declared access/error sourcetypes. The dashboard follows the repository dashboard target shape for infrastructure/web observability: arrival volume, sourcetype coverage over time, 4xx/5xx and POST counters, top clients and requested paths, method/status distribution, HTTP access error triage, error-log level/module triage, referrer/user-agent context for combined-format logs, onboarding coverage by host/source/sourcetype, and recent raw log context.

Dashboard panels intentionally use only fields proven by the synthetic-equivalent fixtures and `props.conf`: `src_ip`/`client_ip`, `user`, `ident`, `http_method`, `uri_path`, `status`, `bytes`/`bytes_out`, `http_referrer`, `http_user_agent`, `error_level`, `module`, `error_code`, `process_id`, `tid`, `connection_id`, `server`, `host_header`, `request`, `error_message`, `vendor_product`, `signature_id`, `marker`, and raw event context. The read-back requirements also tables `eventtype` so reviewers can prove the standard analyst groupings are present: Nginx combined, Apache common/combined, 4xx client-error, 5xx server-error, Nginx error-log, and Apache error-log. It does not cover unrepresented JSON/custom access formats, reverse-proxy timing extensions, WAF/security module fields, debug/custom error formats, collector health, or replay/read-back validation.

## Reduction stance

No event drops or field deletion are enabled by default. `docs/nginx_apache_http_reduction_candidates.csv` lists advisory-only candidates for static asset successes, health probes, verbose referrer/user-agent trimming, and high-volume successful 2xx traffic. Source IP, user, method, URI/query, status, bytes, referrer, user-agent, host/source, request/correlation markers, 4xx/5xx failures, auth/admin/API paths, suspicious methods, unusual user agents, and proxy/security/WAF paths are risky to drop and must be retained by default.

## Known limitations

- Quality remains `curated` and trust remains `unverified`: this is not validated, not S6-verified, and not field-validated.
- Local preflight evidence: `validation/preflight-2026-06-08.md` shows port `20075` and local Splunk TEST ports were unavailable, so replay/read-back remains blocked.
- Fixtures are synthetic-equivalent examples shaped from official documentation, not real customer or server exports.
- Selected Nginx/Apache error-log rows are now fixture-backed, but debug/custom error formats, JSON/custom access formats, reverse-proxy timing extensions, module-specific WAF/security logs, and collector wrapper variants remain deferred.
- Reduction candidates are advisory only and require local replay/read-back plus rollback review before enablement.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, or `field_validated` from CI/schema success alone. Promotion requires real Nginx/Apache relay replay through the intended listener plus Splunk indexed read-back evidence proving count, index, sourcetype, source, timestamps, HTTP field extraction, eventtypes/tags, and normalized fields.
