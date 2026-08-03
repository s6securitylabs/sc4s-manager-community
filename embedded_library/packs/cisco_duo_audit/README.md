# Cisco Duo Audit

Conservative SecHub Resources pack for Cisco Duo Admin API authentication, activity, telephony, Trust Monitor, selected user/phone inventory, and selected integration/application inventory JSON records relayed as one JSON object per line.

This is an API/export/collector relay pack, not a Duo API collector and not proof of live Duo ingestion. It preserves raw JSON, routes fixture-backed Duo audit and inventory families to `cisco:duo:audit:json`, and exposes durable analyst fields while keeping trust `curated`/`unverified` until real Duo relay replay/read-back evidence exists.

## Scope

Fixture-backed source-shape variants:

- Duo authentication success records.
- Duo authentication denial/failure records.
- Duo authentication fraud/low-trust records.
- Duo v1-style activity/admin change records.
- Duo v1-style activity/policy change records.
- Duo Activity Logs v2 WebAuthn/passwordless credential activity records with nested `action`, `actor`, `target`, `outcome`, and `ts` fields.
- Duo Telephony Logs v2 SMS/phone usage records with `telephony_id`, `txid`, `context`, `type`, `credits`, masked `phone`, and `ts` fields.
- Duo Trust Monitor authentication security events with `sekey`, `surfaced_timestamp`, `type=auth`, `state`, `priority_event`, explanation/priority reason arrays, and nested `surfaced_auth` context.
- Duo Trust Monitor bypass-status events with `sekey`, `type=bypass_status`, `enabled_by`, `enabled_for`, `bypass_status_enabled`, state, and priority fields.
- Duo Trust Monitor device-registration events with `sekey`, `type=device_registration`, `surfaced_timestamp`, state, and explanation context.
- Duo Admin API user/phone inventory snapshots with `user_id`, `username`, `status`, nested `phones[].phone_id`, `platform`, `model`, `type`, `last_seen`, and posture fields such as `encrypted`, `screenlock`, and `tampered`.
- Duo Admin API integration/application inventory snapshots with `integration_key`, `name`, `type`, Admin API permission flags such as `adminapi_read_log` / `adminapi_read_resource`, `user_access`, `groups_allowed`, `policy_key`, Universal Prompt flags, and optional API network allowlist context.

Out of current scope: direct Duo API polling or credential custody, SIEM connector wrapper metadata, broader telephony variants beyond the one v2 SMS/phone usage fixture, trust-monitor event types beyond `auth`, `bypass_status`, and `device_registration`, broader endpoint/integration inventory variants, complete optional fields, and local pagination behavior. Add those as separate variants only after exact source-shape evidence or local capture exists.

## Ingestion and collection notes

Typical ingestion is **pull/export/relay**, not direct credential custody inside this pack. Operators usually collect records through the vendor API, cloud export service, SIEM connector, object-store feed, webhook/Event Hub/EventBridge/Pub/Sub route, or a collector such as Cribl, Fluent Bit, Logstash, Vector, or a small scheduled job. Bulk exports may arrive as JSON/CSV files or compressed ZIP/TGZ archives; unpack them outside SC4S, preserve one source record per line where possible, and relay the normalized payload to the dedicated `tcp` listener on port `20088` with source tag `CISCO_DUO_AUDIT`.

Use ingestion-time tooling to unwrap envelopes, decompress archives, split multi-record files, stamp source metadata, and route to index `main` / sourcetype(s) `cisco:duo:audit:json`. Keep the raw vendor payload available for audit challenge. Any redaction, dropping, field suppression, or lossy normalization should be implemented only as an explicit optional preset/postfilter with replay/read-back evidence and rollback notes; do not make lossy reduction the default.

This pack does not itself poll APIs, hold SaaS credentials, manage API pagination/checkpoints, or certify vendor export completeness. Validate local collectors against the source-shape assumptions in this README and the fixture set before promoting trust.

## Evidence and provenance

Public evidence used for this pack is summarized in `docs/evidence/cisco-duo-audit-evidence-scan-20260613.md`.

Representative source URLs:

- Cisco Duo Admin API documentation: <https://duo.com/docs/adminapi>
- Duo authentication logs section: <https://duo.com/docs/adminapi#authentication-logs>
- Duo Admin API users/phones documentation: <https://duo.com/docs/adminapi#users>
- Duo Admin API integrations documentation: <https://duo.com/docs/adminapi#integrations>
- Duo Splunk App documentation: <https://duo.com/docs/splunkapp>

Fixtures are synthetic-equivalent records shaped from public Duo documentation using `example.test`, documentation IP ranges, synthetic Duo object keys, and synthetic transaction IDs. They contain no tenant identifiers, integration keys, API secrets, phone numbers, administrator panel hostnames, or production audit/security-event records.

## Transport, envelope, and event boundaries

- Recommended listener: dedicated TCP line-delimited JSON on port `20088`.
- Fixture file: `test-events/cisco_duo_audit_test_events.txt`.
- Event boundary: one JSON object per line.
- Timestamp policy: authentication and v1-style activity fixtures use Duo `isotimestamp` with UTC offset; Activity Logs v2 and Telephony Logs v2 fixtures use `ts` with UTC offset; Trust Monitor fixtures preserve documented millisecond `surfaced_timestamp` and nested `surfaced_auth.isotimestamp` where present, with receiver-time fallback until local collector timestamp handling is validated.
- Default index: `main` until a deployment-specific identity/SaaS index is chosen.
- Default sourcetype: `cisco:duo:audit:json`.

## Splunk required-field coverage notes

`props.conf` keeps `KV_MODE=json` / `AUTO_KV_JSON=true` and derives the following analyst fields where present:

- `duo_family`
- `user` / `src_user`
- `src_ip` / `src`
- `app`
- `action` / `vendor_raw_action`
- `action_name` for nested Activity Logs v2 `action.name`
- `signature` / `signature_id`
- `status`
- `outcome_result` for nested Activity Logs v2 `outcome.result`
- `factor`
- `reason`
- `object` / `object_type`
- `marker`
- Telephony v2 context fields: `telephony_id`, `txid`, `context`, `type`, `credits`, and masked `phone` where present.
- Trust Monitor fields: `sekey`, `surfaced_timestamp`, `state`, `priority_event`, `triaged_as_interesting`, explanation/priority-reason helper fields, nested `surfaced_auth` user/application/source context, and bypass `enabled_by` / `enabled_for` identities where present.
- User/phone inventory fields: `user_id`, `user_status`, `phone_id`, `phone_platform`, `phone_model`, `phone_type`, `phone_last_seen`, `phone_encrypted`, `phone_screenlock`, `phone_tampered`, and `phone_capabilities` where present.
- Integration inventory fields: `integration_key`, `integration_name`, `integration_type`, Admin API permission flags (`adminapi_read_log`, `adminapi_read_resource`, `adminapi_integrations`, `adminapi_settings`, `adminapi_write_resource`), `user_access`, `groups_allowed`, `policy_key`, Universal Prompt flags, and `networks_for_api_access` where present.

The mappings are intentionally partial. Nested endpoint posture, adaptive trust, application, actor, target, outcome, Trust Monitor explanation arrays, user/phone and integration inventory arrays/permission flags, and security-event workflow state are preserved but not exhaustively normalized.

## Dashboard coverage

`Splunk > Dashboards > Cisco Duo Audit - Overview` is shipped as `splunk/default/data/ui/views/cisco_duo_audit_overview.xml`.

The dashboard is intentionally scoped to the twelve fixture-backed Duo Admin API JSON relay families in this pack: authentication success, authentication denial/failure, authentication fraud, v1-style administrative activity, v1-style policy activity, one Activity Logs v2 WebAuthn credential activity shape, one Telephony Logs v2 SMS/phone usage shape, three Trust Monitor security-event shapes (`auth`, `bypass_status`, and `device_registration`), one user/phone inventory shape, and one integration/application inventory permission shape. Panels use only the shared sourcetype `cisco:duo:audit:json` plus fields proven by the fixtures and `props.conf`/JSON search-time knowledge: `event_type`, `duo_family`, `result`, `action`, `action_name`, `vendor_raw_action`, `outcome_result`, `user`/`src_user`, `src_ip`, `app`, `factor`, `reason`, `object`, `object_type`, `signature_id`, `context`, `type`, `credits`, `phone`, `telephony_id`, `txid`, `sekey`, `state`, `surfaced_timestamp`, `priority_event`, `triaged_as_interesting`, Trust Monitor explanation helpers, user/phone inventory helper fields (`user_id`, `user_status`, `phone_id`, `phone_platform`, `phone_model`, `phone_type`, and phone posture fields), integration inventory helper fields (`integration_key`, `integration_name`, `integration_type`, Admin API permission flags, `user_access`, `groups_allowed`, `policy_key`, and prompt/network-access fields), and `marker`.

The dashboard supports onboarding and first triage (volume, family distribution, denied/fraud authentication counts, top users/source IPs/applications, MFA factor/reason distribution, administrative and policy changes, telephony SMS/phone usage, Trust Monitor auth/bypass/device-registration security events, user/phone inventory posture context, integration/application permission posture, sourcetype/source/host coverage, and recent raw-event context). It is not replay/read-back validation, does not promote trust/quality labels, and does not expand scope to broader Duo telephony variants, unsupported Trust Monitor event types, broader endpoint/integration inventory variants, API polling, SIEM connector envelopes, or complete optional-field coverage.

A registered screenshot example is available at `dashboards/screenshots/cisco_duo_audit_overview-splunk-test.png`. It was captured from a disposable Splunk TEST dashboard populated with safe pack fixture events after fixture read-back and panel export gates passed; it is a sanitized documentation example only, not Cisco Duo source validation or production/customer evidence.

## Validation status

Local validation is structural plus blocked lab evidence only. A 2026-06-27 disposable SC4S/Splunk TEST retry sent all 12 fixture rows to TCP/20088 and showed syslog-ng listener/source movement, but Splunk indexed read-back returned zero Duo fixture markers. See `validation/e2e-lab-2026-06-27.md`. This is not validation evidence and does not change `curated`/`unverified` trust.

Intended read-back SPL:

```spl
index=main "SC4S_CISCO_DUO_AUDIT_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product duo_family event_type user src_user src_ip app action vendor_raw_action signature signature_id status factor reason object object_type action_name outcome_result context type credits phone telephony_id txid sekey state surfaced_timestamp priority_event triaged_as_interesting trust_explanation_type priority_reason_type user_id user_status phone_id phone_platform phone_model phone_type phone_last_seen phone_encrypted phone_screenlock phone_tampered integration_key integration_name integration_type adminapi_read_log adminapi_read_resource adminapi_integrations adminapi_settings adminapi_write_resource user_access groups_allowed policy_key prompt_v4_enabled frameless_auth_prompt_enabled networks_for_api_access marker _raw
```

Expected fixture count: `12` events with one unique marker each.

Current blocker: the 2026-06-27 dedicated lab retry reached the listener and moved 12 events through SC4S/syslog-ng counters, but Splunk marker read-back returned zero indexed events. Earlier local-only preflight also found no local listener/Splunk TEST ports. See `validation/e2e-lab-2026-06-27.md` and `validation/preflight-2026-06-13.md`.

### Disposable E2E harness requirements

`pack.json` now references `scripts/e2e_docker_compose.sh` as an idempotent Docker/Compose harness for a disposable SC4S TEST -> Splunk TEST run. Use `packs/cisco_duo_audit/scripts/e2e_docker_compose.sh plan` for the exact command plan or `... run` when Docker/Compose and image access are available. The harness writes a compose file under `.tmp/e2e/cisco_duo_audit/`, generates an ephemeral HEC token unless `SPLUNK_HEC_TOKEN` is supplied, installs this pack's Splunk knowledge into the test Splunk container, mounts the SC4S parser, replays the 12 JSON fixtures through TCP/20088, and runs summary/detail read-back SPL over `index=main "SC4S_CISCO_DUO_AUDIT_TEST_"`.

A successful harness run would be fixture replay/read-back evidence only for the declared Duo JSON relay source shape. It must still capture retained evidence for count, index, sourcetype, source, host/timestamp, SC4S movement, and required Duo fields before any validation label changes. It does not prove direct Duo API polling, pagination/checkpoint behavior, SIEM connector envelope metadata, production source completeness, or field validation.

## Reduction posture

No drops or field deletion are enabled by default. `docs/cisco_duo_audit_reduction_candidates.csv` lists advisory candidates only. User identity, application, result/reason/factor, endpoint posture, IP address, activity object, timestamps, transaction IDs, and raw JSON are retained by default because they are central to authentication investigation and audit challenge.
