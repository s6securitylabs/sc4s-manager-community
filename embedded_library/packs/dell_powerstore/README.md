# Dell PowerStore remote logging pack

Conservative SecHub Resources SC4S pack for Dell PowerStore remote logging.

## Research summary

Evidence found:

- **Upstream SC4S parser:** `package/etc/conf.d/conflib/syslog/app-syslog-dell_powerstore.conf` routes events whose message contains `[PowerStore_<name>@1139` to `dell:emc:powerstore`, vendor `dellemc`, product `powerstore`.
- **Upstream SC4S docs:** `docs/sources/vendor/Dell/emc_powerstore.md` states the source is message-format based, legacy BSD format, default port 514, sourcetype `dell:emc:powerstore`, default index `infraops` since SC4S 3.38.0.
- **Dell PowerStore Monitoring Your System:** remote logging can send audit log messages and system alert-related events to up to two hosts; TLS can use one-way server CA or mutual authentication.
- **Dell PowerStore Events and Alerts Reference Guide:** documents event/alert fields including event code, severity, alert raised, call home, message, repair flow, system impact, and KB article ID. It includes remote syslog server events such as `0x02400101` (unable to establish a connection with the remote syslog server) and `0x02400102` (connection established).

## Confidence / limitation

This pack is **curated, not validated**. Public evidence proves routing shape and event catalogue fields, but I did **not** find a Dell-published full raw syslog example showing the exact emitted PowerStore message body and structured-data keys. Test events are therefore conservative synthetic-equivalent fixtures for SC4S/Library smoke testing, not a statement that every field name exactly matches appliance output.

## Event shape

- Transport: PowerStore supports remote logging; SC4S upstream documents legacy BSD/default 514. PowerStore docs also document TLS certificate options for remote logging.
- Routing signature: `[PowerStore_<category>@1139` in the message body.
- Expected content: audit log messages and system alert-related events.
- Event catalogue fields: event code, severity, alert raised, call home, message, repair flow, system impact, KB article ID.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tls` listener on port `20091` with source tag `DELL_POWERSTORE`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `infraops` and sourcetype(s) `dell:emc:powerstore`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Dashboard scope

The included `dell_powerstore_overview` Splunk dashboard is a conservative onboarding and first-triage view for the fixture-backed PowerStore structured-data smoke shape. It covers event arrival, severity distribution, alert-raised and remote-syslog connection counters, event code/type coverage, host/source onboarding, and recent raw context.

Dashboard panels intentionally use only fields present in the synthetic-equivalent fixtures and exposed by the Splunk props/transforms: `event_code`, `severity`, `event_type`, `alert_raised`, `call_home`, `kb_article`, `message`, `action`, `signature`, `signature_id`, `marker`, plus Splunk `host`, `source`, `sourcetype`, and `_raw`. The dashboard does **not** statement complete PowerStore event catalogue coverage, real appliance field validation, exact vendor escaping semantics, collector health, or SC4S/Splunk replay/read-back validation.

## Disposable E2E harness

`packs/dell_powerstore/scripts/e2e_docker_compose.sh` defines an idempotent Docker/Compose SC4S TEST -> Splunk TEST harness for this pack. Use `plan` to review the exact commands without requiring Docker:

```bash
packs/dell_powerstore/scripts/e2e_docker_compose.sh plan
```

The harness creates disposable Splunk and SC4S containers, pre-creates `index=infraops`, sends both synthetic-equivalent PowerStore structured-data fixtures through the dedicated TLS/RFC5425 listener on TCP `20091`, then searches for the `SC4S_DELL_POWERSTORE_TEST_` markers and tables the expected PowerStore fields. A successful harness run would be lab replay/read-back evidence for the fixture-backed smoke shape only. It would still not prove a real PowerStore appliance, PowerStoreOS build, exact vendor escaping semantics, UDP/BSD variants, collector wrapper behavior, source-local timezone handling, or field validation.

## Validation SPL

```spl
index=infraops sourcetype="dell:emc:powerstore" "SC4S_DELL_POWERSTORE_TEST_" earliest=-2h
| table _time index sourcetype source host vendor product vendor_product event_code severity event_type action alert_raised call_home kb_article message signature signature_id marker _raw
```

The read-back requirements intentionally tables both source-shaped fields (`event_code`, `severity`, `event_type`, `message`) and Splunk props-derived analyst fields (`vendor_product`, `action`, `signature`, `signature_id`) so reviewers can prove normalization did not hide the original PowerStore structured-data context.

## Next step to promote

Capture real PowerStore remote syslog output from a lab appliance, including one audit event and one alert/event notification, then update fixtures and Splunk extractions from the observed raw records. Until then, keep `trust_level=unverified`.
