# Commvault CommCell SecHub Resources Pack

Version: `0.5.2`

URL: https://documentation.commvault.com/11.40/software/configuring_syslog_server.html

This pack onboards Commvault CommCell syslog/SIEM data into SC4S and Splunk.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tls` listener on port `20029` with source tag `COMMVAULT_COMMCELL`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `commvault` and sourcetype(s) `commvault:commcell:audittrail`, `commvault:commcell:event`, `commvault:commcell:alert`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Current validation status

- `quality_status`: `validated`
- `trust_level`: `s6_verified`
- Evidence: `docs/evidence/sc4s-library-replay-20260605T230445Z/` records the dedicated Commvault TLS/RFC5425 replay path, Splunk indexed read-back, and exact marker count (`3 / 3`) for the AuditTrail, Events, and Alerts fixtures. The retained summaries prove dedicated-listener delivery and marker count; re-run pack-aware replay/read-back before stating the renamed family sourcetypes or `index=commvault` in fresh evidence.
- Scope: this is pack-specific lab validation for the Commvault dedicated listener. It does not validate other SecHub Resources packs and does not make the whole SecHub Resources catalogue production-ready.

## Event families

- `AuditTrail` -> `commvault:commcell:audittrail`
- `Events` -> `commvault:commcell:event` (renamed from `commvault:commcell:events`; a props `rename` stanza keeps data indexed under the old name searchable as the new sourcetype)
- `Alerts` -> `commvault:commcell:alert` (renamed from `commvault:commcell:alerts`; a props `rename` stanza keeps data indexed under the old name searchable as the new sourcetype)

## Default listener

- Transport: TLS
- Port: `20029`
- SC4S source id: `COMMVAULT_COMMCELL`

## Included artifacts

- SC4S parser
- SC4S env example
- Splunk `props.conf`
- Splunk `transforms.conf`
- Splunk `eventtypes.conf`
- Splunk `tags.conf`
- Splunk SOC dashboard `default/data/ui/views/commvault_commcell_soc.xml`
- Splunk lookup `lookups/commvault_eventcodes.csv` plus builder script
- Test events
- TLS send script
- Disposable SC4S TEST -> Splunk TEST E2E harness script

## Deployable Splunk app: commvault_custom

The Library build packages this pack's Splunk knowledge as a ready-to-deploy
app, `commvault_custom-<version>.tgz` (published next to the pack zip in the
Library downloads). Contents: `default/props.conf`, `default/transforms.conf`,
`default/eventtypes.conf`, `default/tags.conf`,
`default/data/ui/views/commvault_commcell_soc.xml`,
`lookups/commvault_eventcodes.csv`, plus generated `default/app.conf` and
`metadata/default.meta` (`export = system` so the knowledge applies globally).
Deploy to the search head tier (SHC deployer `shcluster/apps/`); indexers only
need the `commvault` index.

To build a customer-prefixed copy for app precedence control:

```bash
python3 scripts/package_splunk_app.py commvault_commcell --prefix ZZ_
# -> dist/ZZ_commvault_custom-<version>.tgz
```

Precedence rules (Splunk global config context):

1. `system/local` beats everything; any app `local/` beats any app `default/`.
2. Within the same layer, app directory names are compared in ASCII order and
   the name that sorts FIRST wins.
3. ASCII sorts uppercase before lowercase, so `ZZ_commvault_custom` (uppercase
   prefix) overrides `commvault_custom` and other lowercase-named apps. A
   lowercase `zz_` prefix would sort after them and LOSE - keep override
   prefixes uppercase.
4. Install either the base app or a prefixed copy, not both: they carry the
   same stanzas, and running both means the ASCII-first app silently wins on
   every conflicting key.

## SOC dashboard

`splunk/default/data/ui/views/commvault_commcell_soc.xml` is a classic Simple XML
form scoped to `index=commvault`. Panels are grouped the way a SOC engineer or
incident responder triages a backup platform (backup infrastructure is a primary
ransomware target, so anomaly and tamper signals come first):

- Posture single-values: total events, Commvault anomaly alerts
  (`Alertcriteria="Anomaly*"`: file-activity, event-rate, and failed-job
  anomalies), critical severity, failed logins, failed-job alerts, distinct
  logged-in users.
- Volume/severity overview by sourcetype, CommCell, and forwarding host.
- Detection panels: anomaly alert trend and detail; failed logins with
  threshold colouring; first-time login source per user (24h novelty against a
  fixed 30d baseline); after-hours audit activity; privileged/destructive audit
  operations (delete, retention/aging, security, password, policy/plan,
  schedule, credential, workflow, job kill, media erase).
- Authentication: login trend by user and a login-source table built from the
  extracted `cv_login_src` / `cv_login_from` fields showing who logs in from
  which host/IP and console.
- Backup health: top `Eventcode` values enriched from the
  `commvault_eventcodes` lookup, events severity trend, per-job duration
  buckets (first event to last event per `Jobid`), and failed-job alerts by
  company; tape media import/export movements parsed from base-sourcetype
  events (`<barcode> - IEPort<n>`), plus a residual table for any other
  unclassified base-sourcetype records.

The dashboard only assumes the fields shipped by this pack (SC4S JSON payload
fields plus the `props.conf` extractions below). Deploy `props.conf`,
`transforms.conf`, and the lookup CSV together with the view.

## Login-detail field extractions

CommCell packs login context inside the AuditTrail `Details` string rather than
discrete fields. `props.conf` adds search-time extractions:

- `cv_login_src` — `host/ device:[10.222.111.95]` from successful logins (the
  source host/IP requested for "where are users logging in from").
- `cv_login_from` — `logged in from: [AdminConsole]` console/interface.
- `cv_login_machine` — `Machine: JUMPBOX018` from logout/failed-login details.
- `cv_login_reason` — `Reason: ...` from failed logins.
- `src` — coalesced from `cv_login_src` then `cv_login_machine` for CIM use.

## Eventcode lookup

Events-family records carry `Eventcode` (for example `30:359`) with no readable
meaning. `splunk/lookups/commvault_eventcodes.csv` maps
`event_code,subsystem_id,message_id,event_string`, and `props.conf` applies it
automatically as `eventcode_description` on `commvault:commcell:event`.

Provenance: the authoritative table is the Commvault documentation page
"System Messages, Event Strings and Error Codes"
(https://documentation.commvault.com/2024e/commcell-console/system_messages_event_strings_and_error_codes.html).
The shipped CSV (37,681 codes) was generated with
`scripts/build_commvault_eventcode_lookup.py --text-file` from an
operator-supplied tab-separated export of that page (page banner: "Updated
Sun, Jan 18, 2026"). The docs site is not reachable from this library's build
network and bot-gates scripted fetches, so the text/HTML export path is the
expected refresh route. To refresh after a documentation update:

```bash
# from a host that can reach documentation.commvault.com
python3 scripts/build_commvault_eventcode_lookup.py
# or from a browser-saved copy of the page
python3 scripts/build_commvault_eventcode_lookup.py --html-file saved_page.html
python3 scripts/build_commvault_eventcode_lookup.py --text-file saved_page.txt
```

The script merges with existing rows by default (newest parse wins per code),
sorts numerically, and fails loudly if it parses zero codes.

The TLS send script reads the headerless fixture payloads, substitutes a fresh marker and UTC epoch value, then wraps each event in an RFC5424 syslog envelope with an RFC5425 octet-count prefix before sending to the default TLS listener. This keeps the fixture file self-contained while exercising the declared TLS/RFC5425 transport instead of sending bare application lines over the TLS socket.

## Disposable E2E harness

`packs/commvault_commcell/scripts/e2e_docker_compose.sh run` is the one-shot disposable SC4S TEST -> Splunk TEST harness for refreshing pack-aware replay/read-back evidence. It creates `index=commvault`, starts Splunk TEST and SC4S TEST with the pack parser/Splunk knowledge mounted, sends all nine fixtures through TLS/RFC5425 port `20029`, then fails closed unless Splunk indexed read-back returns all nine `COMMVAULT_PROFILE_TEST_` fixture markers across the audit, event, alert, and base sourcetypes.

This harness is evidence tooling only. A passing run would refresh fixture replay/read-back for the current pack routes; it would not field-validate a real CommCell source version, every SIEM/syslog event shape, collector wrapper behavior, optional alert-drop reduction behavior, or source-local timezone fallback. The 2026-06-26 dedicated lab attempt is retained in `validation/e2e-lab-2026-06-26.md`; it failed closed at host-port preflight because an existing `cisco_duo_audit` disposable Splunk TEST stack owned the standard lab ports, so no Commvault replay/read-back occurred.

## Test event format and boundaries

The included fixture `test-events/commvault_test_events.txt` is deliberately described in `pack.json` under `test_event_sets` so validation tooling does not guess.

- Format: `custom_application`
- Wire format: headerless syslog payload, no BSD/RFC5424 envelope in the fixture file
- File mode: multiple unique events in one file
- Event boundary: one event per physical line
- Record separator: literal newline, represented as `\n` in pack metadata
- Multiline: false
- Expected count: 9 events covering AuditTrail, Events, Alerts, media movement, and base/unclassified rows
- Field delimiting: braced key-value pairs, e.g. `Key = {Value with spaces}`
- Timestamp policy: prefer `Utctimestamp` as UTC epoch seconds; local display fields are fallbacks and require source timezone metadata if `Utctimestamp` is absent.

Future pack fixtures should declare whether they are BSD, IETF/RFC5424, CEF, CSV, hybrid, raw, or custom application format, and whether a file contains one event or multiple events. Otherwise line/event breaking tests become archaeology with worse lighting.

## Verification SPL

```spl
index=commvault "<MARKER>" earliest=-2h
| table _time index sourcetype source cv_event_type action signature_id signature severity user dest process process_id app message _raw
```
