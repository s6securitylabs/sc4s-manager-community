# Netskope SASE / Security Cloud JSON Relay

Curated SecHub Resources pack for narrow Netskope Security Cloud / SASE Data Export and log-streaming JSON relay records. It is intended for operators who already collect Netskope events with Netskope Data Export Iterator, Log Streaming, Event Streaming Client, Cloud Exchange, Cribl, or another controlled collector and relay one JSON event per line to SC4S.

## Review and trust status

- Review status: Reviewed pack metadata and artifacts, but not source validated.
- Internal quality: `curated`.
- Internal trust: `unverified`.
- No `validated`, `s6_verified`, `field_validated`, or `field_verified` statement is made.
- Current blocker: no live Netskope relay, SC4S TEST listener, HEC delivery, or Splunk indexed read-back has been captured.

## Evidence basis

The initial fixture and required-field coverage are derived from the Netskope-owned public `netskopeoss/Data-Schema` repository (`BSD-3-Clause`) and the prior source-shape evidence notes:

- `docs/evidence/netskope-sase-evidence-scan-20260620.md`
- `docs/evidence/netskope-source-shape-unblock-20260621.md`
- `https://github.com/netskopeoss/Data-Schema`
- `schema/event_schema.json` and `schema/event_transaction.json`

Fixtures are synthetic-equivalent JSON records assembled from documented field names, types, examples, and event applicability. They are not captured tenant exports and do not prove Netskope production defaults.

## Source delivery and boundaries

- SC4S does not poll Netskope APIs, manage OAuth/API tokens, own Cloud Exchange plugins, or manage object-store checkpoints.
- A collector must unwrap/export records and relay exactly one JSON event per line.
- Recommended relay for this pack: dedicated TCP syslog listener on port `20101` with headerless or BSD/RFC3164-wrapped JSON payloads.
- Production TLS/RFC5425 can be used if SC4S provisions an equivalent source-tagged route; this pack does not include TLS certificates.
- Default routing: `netproxy` for page/application/alert/network/transaction families and `netauth` for audit family rows.
- No default lossy filtering, masking, redaction, or field deletion is enabled.

## Fixture-backed families

| Family | Sourcetype | Index | Evidence scope |
| --- | --- | --- | --- |
| Page / web transaction event | `netskope:events:page` | `netproxy` | Data-Schema `type=page`, user/app/site/url/action/policy/network fields |
| Application event | `netskope:events:application` | `netproxy` | Data-Schema `type=application`, activity/object/app/user fields |
| Alert | `netskope:alerts` | `netproxy` | Data-Schema alert/policy/severity/object fields |
| Audit | `netskope:audit` | `netauth` | Data-Schema `type=audit` activity/action/object/user fields |
| Network event | `netskope:events:network` | `netproxy` | Data-Schema `type=network`, src/dst/site/action/policy fields |
| Transaction log-streaming event | `netskope:transaction` | `netproxy` | Data-Schema `event_transaction.json` `x-transaction-id`, `x-cs-timestamp`, HTTP/policy/byte fields |

## Validation harness

The blocked replay/read-back requirements is:

```spl
(index=netproxy OR index=netauth) "SC4S_NETSKOPE_SASE_TEST_" earliest=-2h
| table _time index sourcetype source vendor product netskope_event_family type action policy signature signature_id event_id user src_user src_ip dest_ip dest app site url bytes severity alert_type marker _raw
```

Expected count is 6 events. A successful promotion attempt must prove event count, index, sourcetype, source, timestamp, vendor/product, family, policy/action/severity, user/source/destination context, transaction IDs, marker uniqueness, and raw JSON preservation.

Latest preflight evidence is `validation/preflight-2026-06-21.md`; it is blocked at listener plus Splunk management/HEC layers and is not validation.

### Disposable Docker E2E harness

`packs/netskope_sase/scripts/e2e_docker_compose.sh` provides an idempotent disposable Splunk TEST + SC4S TEST harness with `plan`, `write-compose`, `up`, `replay`, `readback`, `run`, and `down` modes. It writes `.tmp/e2e/netskope_sase/compose.yaml`, generates an ephemeral HEC token unless `SPLUNK_HEC_TOKEN` is supplied, creates `netproxy` and `netauth` test indexes, replays all six fixture records through TCP `20101`, and runs summary/detail read-back SPL over the `SC4S_NETSKOPE_SASE_TEST_` markers.

Run `packs/netskope_sase/scripts/e2e_docker_compose.sh plan` for the exact one-shot and step-by-step commands. A successful `run` would create SC4S TEST -> Splunk TEST fixture replay/read-back evidence for this pack's JSON relay shape only. It would still not prove live Netskope tenant delivery, Cloud Exchange/Event Streaming Client behaviour, API token custody, pagination, object-store/checkpoint handling, CEF/ELFF modes, field validation, or production readiness.

## Known limitations

- No live Netskope tenant/API/log-streaming replay or Splunk indexed read-back has been captured.
- Cloud Firewall, endpoint, API Data Protection, CEF/ELFF, object-store native envelopes, and Cloud Exchange plugin-specific serialization are out of scope until separately evidenced.
- Fixture fields are a narrow schema-derived subset; they do not state default production field lists or complete Netskope coverage.
- Splunk eventtypes/tags are analyst discovery helpers only and do not state full CIM certification.

## Reduction posture

All fields are retained by default. Advisory reduction candidates are recorded in `docs/netskope_sase_reduction_candidates.csv`; none are enabled. Because Netskope rows can contain sensitive URLs, object names, users, policy names, and IP addresses, any local masking/reduction must be opt-in and preceded by replay/read-back proving incident reconstruction is not damaged.
