# Oracle WebLogic fixture IVV — 2026-07-01

Scope: local source-shape/fixture validation for `oracle_weblogic` server/access log relay fixtures only.

Verdict: **Alpha / unverified**. The pack now has synthetic-equivalent WebLogic server/access event logs and search-time extraction artifacts for `oracle:weblogic:server` and `oracle:weblogic:access`. No live WebLogic server, SC4S listener, HEC delivery, Splunk indexed read-back, or field validation was performed.

Evidence used:

- Oracle WebLogic documentation for the `####<...>` server-log first-line shape.
- Elastic `oracle_weblogic` integration pipeline test shapes reviewed under Elastic License 2.0; raw samples were not copied.
- Synthetic-equivalent local fixture: `test-events/oracle_weblogic_server_access.txt`.
- SC4S route artifact: `sc4s/app_parsers/syslog/app-oracle_weblogic.conf`.
- Splunk search-time extraction: `splunk/default/props.conf`.
- Onboarding dashboard (2026-07-03): `splunk/default/data/ui/views/oracle_weblogic_server_access_overview.xml`, parse-checked with ElementTree. Panels reference only fields the shipped extractions produce; the dashboard is an onboarding/triage aid, not validation evidence.

Checks expected before promotion:

1. Replay all 6 fixture records through TCP/20102 using `scripts/send_tcp_20102.sh` in the standard SC4S/Splunk test lab.
2. Confirm 4 server events in `sourcetype="oracle:weblogic:server"` and 2 access events in `sourcetype="oracle:weblogic:access"` in `index=infraops`.
3. Verify marker, timestamp, severity/status, subsystem/message_id for server logs, and src/status/method/path for access logs.
4. After read-back, load the overview dashboard and confirm each panel renders against the indexed fixtures (severity/attention counts, security subsystem events, managed-server activity, HTTP status, top URIs/clients, marker coverage, raw drilldown).
5. Keep trust `unverified` until replay/read-back evidence exists.
