# Hermes Agent audit blocked preflight — 2026-07-07

Initial pack creation could not perform replay/read-back validation because no dedicated Hermes Agent audit relay, SC4S listener on TCP 20131, Splunk `netauth` search path, or OpenSearch test data view was available in this repository run.

This file is blocker evidence only. It does not validate the pack, sourcetype, dashboards, SC4S route, Splunk props, or OpenSearch saved-object import.

Required promotion evidence:

1. Emit one normalized JSON object per Hermes Agent audit event.
2. Replay fixtures and a representative sanitized live export through SC4S TCP 20131.
3. Read back from Splunk `index=netauth sourcetype="hermes:agent:audit"` with event count, source, sourcetype, timestamp, actor, source IP, channel, tool/provider, policy fields, and raw JSON.
4. Import `opensearch/dashboards/hermes_agent_audit_security.ndjson` into a disposable OpenSearch Dashboards space and confirm the data view resolves against real indexed events.

## S6 Hermes / legacy OpenClaw refinement

The pack was refined from the public-safe shape of our Hermes Agent migration evidence: active Hermes gateway/runtime concepts, legacy OpenClaw gateway control state, Telegram channel policy, owner allowlist state, command-logger/session-memory hooks, and dry-run/cutover hazards. Real tokens, chat IDs, owner IDs, message bodies, prompts, and workspace paths remain outside the pack and must stay collector-local or redacted.
