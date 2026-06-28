# Commvault CommCell SecHub Resources Pack

Version: `0.1.0`

URL: https://documentation.commvault.com/11.40/software/configuring_syslog_server.html

This pack onboards Commvault CommCell syslog/SIEM data into SC4S and Splunk.

## Event families

- `AuditTrail` -> `commvault:commcell:audittrail`
- `Events` -> `commvault:commcell:events`
- `Alerts` -> `commvault:commcell:alerts`

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
- Test events
- TLS send script


## Test event format and boundaries

The included fixture `test-events/commvault_test_events.txt` is deliberately described in `pack.json` under `test_event_sets` so validation tooling does not guess.

- Format: `custom_application`
- Wire format: headerless syslog payload, no BSD/RFC5424 envelope in the fixture file
- File mode: multiple unique events in one file
- Event boundary: one event per physical line
- Record separator: literal newline, represented as `\n` in pack metadata
- Multiline: false
- Expected count: 3 events, one each for AuditTrail, Events, Alerts
- Field delimiting: braced key-value pairs, e.g. `Key = {Value with spaces}`
- Timestamp policy: prefer `Utctimestamp` as UTC epoch seconds; local display fields are fallbacks and require source timezone metadata if `Utctimestamp` is absent.

Future pack fixtures should declare whether they are BSD, IETF/RFC5424, CEF, CSV, hybrid, raw, or custom application format, and whether a file contains one event or multiple events. Otherwise line/event breaking tests become archaeology with worse lighting.

## Verification SPL

```spl
index=commvault "<MARKER>" earliest=-2h
| table _time index sourcetype source cv_event_type action signature_id signature severity user dest process process_id app message _raw
```
