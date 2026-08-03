# Hermes Agent Audit Logs

Conservative SecHub Resources pack for Hermes Agent gateway/runtime audit events relayed as one normalized JSON object per event. The point is analyst visibility: who logged in, from where, what channel or handoff changed, what tool was run, what provider/credential changed, and which approval or safety/policy guard blocked something.

## Scope

- Product/application: `hermes_agent`.
- Sourcetype: `hermes:agent:audit`.
- Default index: `netauth`.
- SC4S listener example: TCP `20131`.
- Source mode: local collector, journald export, gateway audit stream, or webhook relay emits one JSON audit event per line.

This is a separate product pack. Hermes Agent and legacy OpenClaw should be ingested as distinct applications/products. Correlate them in Splunk/OpenSearch only with an explicit cross-product investigation view.

## Analyst questions this pack is designed to answer

- Did anyone log in from an unexpected IP, country, user-agent, VPN exit, or automation client?
- Did a channel, topic, handoff, webhook, delivery destination, or owner/allowlist policy change?
- Were provider/model credentials, plugin/profile/hook settings, or admin controls modified?
- Which high-side-effect tool, gateway, hook, approval, or blocked-policy event fired?
- Can the team reconstruct a timeline without storing secrets, raw prompts, message bodies, or private identifiers in public fixtures?

## Splunk dashboards

- `hermes_agent_audit_overview` — family/action counts and recent audit trail.
- `hermes_agent_audit_security_review` — critical-review panels for unexpected/foreign source IPs, route/control changes, credential/provider activity, risky operations, and blocked/policy events.

Foreign-IP review uses Splunk `iplocation` enrichment on `src_ip`. Treat country results as triage context, not source truth.

## OpenSearch

`opensearch/dashboards/hermes_agent_audit_security.ndjson` is a starter saved-object bundle for a `hermes-agent-audit-*` data view and a placeholder security-review dashboard. Import it into a disposable OpenSearch Dashboards space and wire panels to real indexed fields before operational use.

## Fixture semantics

`test-events/hermes_agent_audit_test_events.txt` contains six compact synthetic JSON lines. All values use documentation IP ranges or example identifiers. No real bot tokens, chat IDs, owner IDs, prompts, message bodies, workspace paths, or credentials are present.

## Validation status

Current status: **blocked / unverified**. Creation-time schema and fixture checks are expected to run in CI, but no live Hermes Agent Audit Logs relay, SC4S listener, Splunk indexed read-back, or OpenSearch dashboard import has been captured. Do not promote quality/trust until replay/read-back evidence exists.
