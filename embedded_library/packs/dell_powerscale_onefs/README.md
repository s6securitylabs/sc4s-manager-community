# Dell PowerScale / OneFS audit logging pack

Conservative SecHub Resources SC4S pack for Dell PowerScale OneFS audit forwarding.

## Research summary

Evidence found:

- **Dell KB 000020901:** OneFS can audit system configuration events and SMB/NFS/HDFS protocol access events. Protocol auditing records SMB/NFS/HDFS file access in the `protocol` audit topic; configuration auditing records API-handled config events in the `config` audit topic. Audit logs live under `/ifs/.ifsvar/audit/logs` and are viewed with `isi_audit_viewer`.
- **Dell whitepaper H12428.3:** OneFS 7.1.1 added forwarding of config and protocol audit events to syslog. By default, syslog forwarding writes to `/var/log/audit_protocol.log` and `/var/log/audit_config`. OneFS 8.2 introduced granular protocol events and a `detailType` field in the event payload. The paper also documents audit progress fields for CEE/syslog forwarding.
- **PowerScale syslog integration guide (Peer Software, secondary):** OneFS 9.5+ supports a syslog-based connection for audit events and requires TLS certificates for that integration.
- **Public OneFS protocol-auditing example (secondary):** example payload fields include `protocol`, `zoneID`, `zoneName`, `eventType`, `detailType`, `isDirectory`, `clientIPAddr`, `fileName`, `newFileName`, `userSID`, and `userID`.

## Confidence / limitation

This pack is **curated, not validated**. Dell confirms the audit topics, forwarding path, and many payload concepts, but the public sources I could access do not provide a complete raw emitted syslog line for the current OneFS syslog forwarding path. Fixtures are synthetic-equivalent JSON payloads based on public payload examples and Dell field descriptions. They must be replaced or confirmed with real OneFS syslog captures before validation.

## Event shape

- Topics/families: protocol audit and configuration audit.
- Protocol payload fields observed publicly: `protocol`, `zoneID`, `zoneName`, `eventType`, `detailType`, `isDirectory`, `clientIPAddr`, `fileName`, `newFileName`, `userSID`, `userID`.
- Boundary assumption for fixtures: one JSON payload per syslog message line.
- Timestamp policy: RFC5424 header timestamp in fixtures; real appliance timestamp handling requires capture confirmation.

## Ingestion and collection notes

Typical ingestion is **agent/syslog/file/collector relay** from the host, platform component, appliance, or management service into the dedicated `tls` listener on port `20092` with source tag `DELL_POWERSCALE_ONEFS`. Depending on the product, records may originate from syslog, journald/eventlog forwarding, application log files, API exports, backup/report exports, or ZIP/TGZ bundles collected by an intermediate forwarder. Normalize wrappers and split records before SC4S where practical, then route to index `infraops` and sourcetype(s) `dell:powerscale:onefs:protocol`, `dell:powerscale:onefs:config`.

Use ingestion-time controls for safe framing and routing: source tags, host/source correction, timestamp preservation, multiline handling, archive extraction, and file-to-line conversion. Keep raw operational and audit context by default; fields that look noisy can still be required for outage, backup, privilege-change, or incident reconstruction. Any filtering or transformation should be opt-in, documented, and validated with replay/read-back evidence.

This pack does not prove every collector/export mode. Compare local emitted records against the fixture semantics and validation SPL before treating a new ingestion route as covered.

## Dashboard scope

`dell_powerscale_onefs_overview.xml` is a fixture-backed onboarding and first-triage dashboard for the currently covered OneFS protocol/config audit smoke source shape. It covers arrival health, sourcetype/family distribution, protocol rename/file context, configuration change context, client/user summaries, fixture smoke markers, host/source onboarding, and raw syslog context. Panels use only fields preserved by the synthetic-equivalent fixtures and Splunk JSON props: `protocol`, `topic`, `eventType`, `detailType`, `clientIPAddr`, `src`, `userID`, `userSID`, `user`, `actor`, `object`, `fileName`, `newFileName`, `zoneName`, `action`, `signature`, and `marker`.

The dashboard does **not** statement complete OneFS audit coverage, exact production syslog envelope validation, SMB/NFS/HDFS operation completeness, CEE integration parity, cluster health/storage telemetry, collector health, or SC4S/Splunk replay/read-back validation.

## Validation SPL

```spl
index=infraops sourcetype IN ("dell:powerscale:onefs:protocol", "dell:powerscale:onefs:config") "SC4S_DELL_POWERSCALE_TEST_" earliest=-2h
| table _time index sourcetype source vendor product protocol topic eventType detailType action signature clientIPAddr src userID userSID user actor object fileName newFileName zoneName marker _raw
```

The read-back table intentionally includes both raw OneFS JSON fields (`eventType`, `detailType`, `clientIPAddr`, `userID`, `userSID`, `fileName`, `newFileName`, `zoneName`) and Splunk analyst aliases (`action`, `signature`, `src`, `user`). That lets a reviewer prove parser/search-time normalization did not hide the vendor payload tokens. This is a requirements for future replay/read-back, not validation evidence by itself.

## Disposable SC4S TEST -> Splunk TEST harness

`packs/dell_powerscale_onefs/scripts/e2e_docker_compose.sh` provides an idempotent Docker/Compose harness for a permitted lab run. Use `plan` to inspect the commands without Docker, `write-compose` to write the disposable Compose file with an ephemeral HEC token, or `run` to start Splunk/SC4S TEST containers, create `index=infraops`, replay both OneFS protocol/config JSON fixtures through TLS/RFC5425 TCP `20092`, and execute summary/detail read-back SPL.

The harness is a replay/read-back requirements for the synthetic-equivalent fixture shape only. A passing run would still not prove a real PowerScale appliance, OneFS version, SMB/NFS/HDFS audit completeness, exact forwarded JSON/envelope behavior, UDP/BSD variants, collector wrapper behavior, source-local timezone handling, or field validation. Keep `curated`/`unverified` until sanctioned OneFS output or vendor-certified examples are captured and read back.

## Next step to promote

Capture real OneFS syslog output from a PowerScale node for both protocol and config audit topics. Specifically verify whether the forwarded body is JSON, key-value, or another serialized format, and whether the syslog envelope is RFC3164, RFC5424, or TLS/RFC5425.
