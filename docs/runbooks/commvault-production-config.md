# Commvault CommCell Production Configuration for SC4S + Splunk

## Scope

This bundle defines a dedicated Commvault CommCell TLS source for SC4S and Splunk Enterprise/Splunk Enterprise Security friendly extraction/export artifacts.

It handles Commvault syslog/SIEM families:

- `AuditTrail`
- `Events`
- `Alerts` / `Alert`

Validated lab target:

- SC4S custom TLS listener: `20029`
- Splunk index: `commvault`
- Splunk sourcetypes by family:
  - `commvault:commcell:audittrail`
  - `commvault:commcell:events`
  - `commvault:commcell:alerts`
- Splunk source: `commvault_commcell`

## 1. SC4S env_file changes

Add these to `/opt/sc4s/env_file`:

```bash
# Commvault CommCell dedicated TLS listener.
# SOURCE_ALL_SET only enables/generates the source/listener and .source.s_COMMVAULT_COMMCELL tag.
# It is not index routing.
SC4S_LISTEN_COMMVAULT_COMMCELL_TLS_PORT=20029
SOURCE_ALL_SET=DEFAULT,COMMVAULT_COMMCELL
```

If `SOURCE_ALL_SET` already exists, append `COMMVAULT_COMMCELL` to the comma-separated list rather than creating a duplicate key.

Example:

```bash
SOURCE_ALL_SET=DEFAULT,COMMVAULT_COMMCELL
```

Production note:

- Ensure SC4S TLS source cert/key are already configured for TLS listeners.
- If adding this listener to a running Docker Compose SC4S deployment, verify the env is actually present inside the container. If not, recreate the container, not just restart it.

```bash
cd /opt/sc4s
sudo docker compose up -d --force-recreate sc4s
sudo docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' SC4S | grep -E 'COMMVAULT|SOURCE_ALL_SET'
sudo ss -ltnp | grep ':20029'
```

## 2. SC4S parser file

Create:

```text
/opt/sc4s/local/config/app_parsers/syslog/app-commvault_commcell.conf
```

Recommended ownership/mode:

```bash
sudo install -m 664 -o root -g sc4s-manager app-commvault_commcell.conf /opt/sc4s/local/config/app_parsers/syslog/app-commvault_commcell.conf
```

Parser content:

```conf
block parser app-commvault_commcell() {
    channel {
        # Commvault syslog/SIEM families:
        # Alerts: Alertid, Alertname, Alerttime, Alertseverity, Jobid, Alertdescription, Utctimestamp, Companyname
        # AuditTrail: Opid, Audittime, Severitylevel, Username, Operation, Details, Companyname, Utctimestamp
        # Events: Eventid, Occurrencetime, Eventseverity, Computer, Program, Description, Utctimestamp
        if (message("^AuditTrail:" type(pcre))) {
            rewrite {
                set("audit", value(".values.cv_event_type"));
                set("audit", value(".values.action"));
                set("Audit", value(".values.tag"));
            };
        } elif (message("^Alerts?:" type(pcre))) {
            rewrite {
                set("alert", value(".values.cv_event_type"));
                set("alert", value(".values.action"));
                set("Alert", value(".values.tag"));
            };
        } elif (message("^Events?:" type(pcre))) {
            rewrite {
                set("event", value(".values.cv_event_type"));
                set("event", value(".values.action"));
                set("Event", value(".values.tag"));
            };
        };

        # Extract known Commvault Key = {value} fields. regexp-parser preserves multi-word values.
        if (message("Alertid[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Alertid[[:space:]]*=[[:space:]]*[{](?<Alertid>[^}]*)[}].*')); }; };
        if (message("Alertname[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Alertname[[:space:]]*=[[:space:]]*[{](?<Alertname>[^}]*)[}].*')); }; };
        if (message("Alerttime[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Alerttime[[:space:]]*=[[:space:]]*[{](?<Alerttime>[^}]*)[}].*')); }; };
        if (message("Alertseverity[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Alertseverity[[:space:]]*=[[:space:]]*[{](?<Alertseverity>[^}]*)[}].*')); }; };
        if (message("Alertdescription[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Alertdescription[[:space:]]*=[[:space:]]*[{](?<Alertdescription>[^}]*)[}].*')); }; };

        if (message("Opid[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Opid[[:space:]]*=[[:space:]]*[{](?<Opid>[^}]*)[}].*')); }; };
        if (message("Audittime[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Audittime[[:space:]]*=[[:space:]]*[{](?<Audittime>[^}]*)[}].*')); }; };
        if (message("Severitylevel[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Severitylevel[[:space:]]*=[[:space:]]*[{](?<Severitylevel>[^}]*)[}].*')); }; };
        if (message("Username[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Username[[:space:]]*=[[:space:]]*[{](?<Username>[^}]*)[}].*')); }; };
        if (message("Operation[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Operation[[:space:]]*=[[:space:]]*[{](?<Operation>[^}]*)[}].*')); }; };
        if (message("Details[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Details[[:space:]]*=[[:space:]]*[{](?<Details>[^}]*)[}].*')); }; };

        if (message("Eventid[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Eventid[[:space:]]*=[[:space:]]*[{](?<Eventid>[^}]*)[}].*')); }; };
        if (message("Occurrencetime[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Occurrencetime[[:space:]]*=[[:space:]]*[{](?<Occurrencetime>[^}]*)[}].*')); }; };
        if (message("Eventseverity[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Eventseverity[[:space:]]*=[[:space:]]*[{](?<Eventseverity>[^}]*)[}].*')); }; };
        if (message("Computer[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Computer[[:space:]]*=[[:space:]]*[{](?<Computer>[^}]*)[}].*')); }; };
        if (message("Program[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Program[[:space:]]*=[[:space:]]*[{](?<Program>[^}]*)[}].*')); }; };
        if (message("Description[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Description[[:space:]]*=[[:space:]]*[{](?<Description>[^}]*)[}].*')); }; };

        if (message("Utctimestamp[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Utctimestamp[[:space:]]*=[[:space:]]*[{]?(?<Utctimestamp>[0-9]{10})[}]?.*')); }; };
        if (message("Jobid[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Jobid[[:space:]]*=[[:space:]]*[{](?<Jobid>[^}]*)[}].*')); }; };
        if (message("Clientname[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Clientname[[:space:]]*=[[:space:]]*[{](?<Clientname>[^}]*)[}].*')); }; };
        if (message("Companyname[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*Companyname[[:space:]]*=[[:space:]]*[{](?<Companyname>[^}]*)[}].*')); }; };
        if (message("AgentType[[:space:]]*=" type(pcre))) { parser { regexp-parser(prefix(".values.") patterns('.*AgentType[[:space:]]*=[[:space:]]*[{](?<AgentType>[^}]*)[}].*')); }; };

        # CIM-oriented normalized fields for Splunk Enterprise Security search-time use.
        rewrite {
            set("Commvault", value(".values.vendor"));
            set("CommCell", value(".values.product"));
            set("commvault:commcell", value(".values.vendor_product"));
            set("backup", value(".values.app"));
            set("${.values.Username}", value(".values.user") condition('${.values.Username}' ne ''));
            set("${.values.Computer}", value(".values.dest") condition('${.values.Computer}' ne ''));
            set("${.values.Clientname}", value(".values.dest") condition('${.values.Clientname}' ne ''));
            set("${.values.Program}", value(".values.process") condition('${.values.Program}' ne ''));
            set("${.values.AgentType}", value(".values.app") condition('${.values.AgentType}' ne ''));
            set("${.values.Jobid}", value(".values.process_id") condition('${.values.Jobid}' ne ''));
            set("${.values.Alertseverity}", value(".values.severity") condition('${.values.Alertseverity}' ne ''));
            set("${.values.Eventseverity}", value(".values.severity") condition('${.values.Eventseverity}' ne ''));
            set("${.values.Severitylevel}", value(".values.severity") condition('${.values.Severitylevel}' ne ''));
            set("${.values.Alertname}", value(".values.signature") condition('${.values.Alertname}' ne ''));
            set("${.values.Operation}", value(".values.signature") condition('${.values.Operation}' ne ''));
            set("${.values.Description}", value(".values.signature") condition('${.values.Description}' ne ''));
            set("${.values.Alertdescription}", value(".values.message") condition('${.values.Alertdescription}' ne ''));
            set("${.values.Description}", value(".values.message") condition('${.values.Description}' ne ''));
            set("${.values.Details}", value(".values.message") condition('${.values.Details}' ne ''));
            set("${.values.Alertid}", value(".values.signature_id") condition('${.values.Alertid}' ne ''));
            set("${.values.Eventid}", value(".values.signature_id") condition('${.values.Eventid}' ne ''));
            set("${.values.Opid}", value(".values.signature_id") condition('${.values.Opid}' ne ''));
        };

        if (match("^[0-9]{10}$" value(".values.Utctimestamp") type(pcre))) {
            parser { date-parser-nofilter(format("%s") template("${.values.Utctimestamp}")); };
        } elif (match("^." value(".values.Occurrencetime") type(pcre))) {
            parser { date-parser-nofilter(format("%d %b %Y %H:%M:%S") template("${.values.Occurrencetime}")); };
        } elif (match("^." value(".values.Alerttime") type(pcre))) {
            parser { date-parser-nofilter(format("%d %b %Y %H:%M:%S") template("${.values.Alerttime}")); };
        } elif (match("^." value(".values.Audittime") type(pcre))) {
            parser { date-parser-nofilter(format("%d %b %Y %H:%M:%S") template("${.values.Audittime}")); };
        };

        # Default metadata, then refine sourcetype by Commvault family.
        rewrite {
            r_set_splunk_dest_default(
                index("commvault")
                sourcetype("commvault:commcell")
                vendor("commvault")
                product("commcell")
                source("commvault_commcell")
                template("t_json_values")
            );
        };
        rewrite {
            r_set_splunk_dest_update_v2(
                sourcetype("commvault:commcell:audittrail")
                condition('${.values.cv_event_type}' eq 'audit')
            );
        };
        rewrite {
            r_set_splunk_dest_update_v2(
                sourcetype("commvault:commcell:events")
                condition('${.values.cv_event_type}' eq 'event')
            );
        };
        rewrite {
            r_set_splunk_dest_update_v2(
                sourcetype("commvault:commcell:alerts")
                condition('${.values.cv_event_type}' eq 'alert')
            );
        };
    };
};

application app-network-commvault_commcell[sc4s-network-source] {
    filter {
        tags(".source.s_COMMVAULT_COMMCELL")
        and (
            message("^(AuditTrail|Alerts?|Events?):" type(pcre))
            or message("^(Opid|Alertid|Eventid)[[:space:]]*=" type(pcre))
        );
    };
    parser { app-commvault_commcell(); };
};

application app-raw-commvault_commcell[sc4s-raw-syslog] {
    filter {
        message("^(AuditTrail|Alerts?|Events?):" type(pcre))
        or message("^(Opid|Alertid|Eventid)[[:space:]]*=" type(pcre));
    };
    parser { app-commvault_commcell(); };
};

application app-syslog-commvault_commcell[sc4s-syslog] {
    filter {
        message("^(AuditTrail|Alerts?|Events?):" type(pcre))
        or message("^(Opid|Alertid|Eventid)[[:space:]]*=" type(pcre));
    };
    parser { app-commvault_commcell(); };
};
```

## 3. Splunk index

Create or deploy an index named `commvault`.

Example app-local `indexes.conf`:

```ini
[commvault]
homePath = $SPLUNK_DB/commvault/db
coldPath = $SPLUNK_DB/commvault/colddb
thawedPath = $SPLUNK_DB/commvault/thaweddb
repFactor = auto
```

Adjust retention and volume paths for the production Splunk cluster/indexer tier.

## 4. Splunk props.conf

For an initial search-head/indexer app, create:

```text
default/props.conf
```

Content:

```ini
[commvault:commcell]
SHOULD_LINEMERGE = false
KV_MODE = json
AUTO_KV_JSON = true
TRUNCATE = 20000
TIME_PREFIX = "Utctimestamp":"
TIME_FORMAT = %s
MAX_TIMESTAMP_LOOKAHEAD = 10
category = Custom
pulldown_type = true
EVAL-vendor = coalesce(vendor, "Commvault")
EVAL-product = coalesce(product, "CommCell")
EVAL-vendor_product = coalesce(vendor_product, "commvault:commcell")
EVAL-action = coalesce(action, cv_event_type)
EVAL-signature = coalesce(signature, Operation, Description, Alertname)
EVAL-signature_id = coalesce(signature_id, Opid, Eventid, Alertid)
EVAL-severity = coalesce(severity, Severitylevel, Eventseverity, Alertseverity)
EVAL-user = coalesce(user, Username)
EVAL-dest = coalesce(dest, Computer, Clientname)
EVAL-process = coalesce(process, Program)
EVAL-process_id = coalesce(process_id, Jobid)
EVAL-app = coalesce(app, AgentType, "backup")
EVAL-message = coalesce(message, Details, Description, Alertdescription)
FIELDALIAS-commvault_audit_time = Audittime AS audit_time
FIELDALIAS-commvault_alert_time = Alerttime AS alert_time
FIELDALIAS-commvault_occurrence_time = Occurrencetime AS occurrence_time

[commvault:commcell:audittrail]
SHOULD_LINEMERGE = false
KV_MODE = json
AUTO_KV_JSON = true
TIME_PREFIX = "Utctimestamp":"
TIME_FORMAT = %s
EVAL-cv_event_type = coalesce(cv_event_type, "audit")
EVAL-action = coalesce(action, "audit")

[commvault:commcell:events]
SHOULD_LINEMERGE = false
KV_MODE = json
AUTO_KV_JSON = true
TIME_PREFIX = "Utctimestamp":"
TIME_FORMAT = %s
EVAL-cv_event_type = coalesce(cv_event_type, "event")
EVAL-action = coalesce(action, "event")

[commvault:commcell:alerts]
SHOULD_LINEMERGE = false
KV_MODE = json
AUTO_KV_JSON = true
TIME_PREFIX = "Utctimestamp":"
TIME_FORMAT = %s
EVAL-cv_event_type = coalesce(cv_event_type, "alert")
EVAL-action = coalesce(action, "alert")
```

Because SC4S emits `t_json_values`, Splunk gets JSON raw events. `KV_MODE=json` and the `EVAL-*` fallbacks make the fields visible/searchable even if the parser evolves.

## 5. Splunk transforms.conf

For this SC4S JSON-output design, no index-time transforms are required for basic CIM-oriented search use. Still ship a file so the export bundle is explicit:

```text
default/transforms.conf
```

Content:

```ini
# Commvault CommCell SC4S JSON events do not require index-time transforms.
# Field extraction is handled by KV_MODE=json in props.conf and SC4S emits normalized fields.
# Keep this file as a placeholder for customer-specific routing/masking transforms.
```

If a production customer insists on raw non-JSON events instead of SC4S `t_json_values`, transforms can be added later. For this design, JSON is cleaner and easier to support.

## 6. Splunk eventtypes.conf

```ini
[commvault_commcell]
search = index=commvault (sourcetype=commvault:commcell OR sourcetype=commvault:commcell:*) vendor_product="commvault:commcell"

[commvault_commcell_audit]
search = index=commvault sourcetype=commvault:commcell:audittrail

[commvault_commcell_event]
search = index=commvault sourcetype=commvault:commcell:events

[commvault_commcell_alert]
search = index=commvault sourcetype=commvault:commcell:alerts
```

## 7. Splunk tags.conf

These are conservative initial tags. Final CIM mapping should be reviewed with the ES content/correlation use cases.

```ini
[eventtype=commvault_commcell]
backup = enabled
inventory = enabled

[eventtype=commvault_commcell_audit]
audit = enabled
change = enabled

[eventtype=commvault_commcell_alert]
alert = enabled

[eventtype=commvault_commcell_event]
event = enabled
```

## 8. Test events

Use a fresh marker per test run.

```bash
MARKER="COMMVAULT_PROD_TEST_$(date -u +%Y%m%dT%H%M%SZ)"
EPOCH="$(date -u +%s)"
cat > /tmp/commvault_test_events.txt <<EOF
AuditTrail: Opid = {119263} Audittime = {26 May 2026 11:55:00} Severitylevel = {Medium} Username = {S6LAB\\nigel.test} Operation = {Login Failed} Details = {Login Name: S6LAB\\nigel.test Machine: cv-console01 Reason: invalid password Marker: ${MARKER}_AUDIT} Companyname = {S6 Security Labs} Utctimestamp = {$EPOCH}
Events: Eventid = {64235109} Occurrencetime = {26 May 2026 11:55:01} Eventseverity = {Information} Computer = {cv-mediaagent01} Program = {CommServe} Description = {Backup job completed successfully Marker: ${MARKER}_EVENT} Jobid = {881231} AgentType = {File System} Utctimestamp = {$EPOCH}
Alerts: Alertid = {70042} Alertname = {Job Failed} Alerttime = {26 May 2026 11:55:02} Alertseverity = {Critical} Jobid = {881232} Alertdescription = {Backup job failed for client cv-client01 Marker: ${MARKER}_ALERT} Companyname = {S6 Security Labs} Clientname = {cv-client01} Utctimestamp = {$EPOCH}
EOF
while IFS= read -r event; do
  printf '%s\n' "$event" | timeout 5 openssl s_client -connect <SC4S_HOST>:20029 -quiet >/tmp/commvault_send.out 2>&1 || rc=$?
  rc=${rc:-0}
  if [ "$rc" != "0" ] && [ "$rc" != "124" ]; then
    echo "send failed rc=$rc"
    cat /tmp/commvault_send.out
    exit "$rc"
  fi
  unset rc
  sleep 1
done < /tmp/commvault_test_events.txt
echo "$MARKER"
```

## 9. Verification SPL

```spl
index=commvault "<MARKER>" earliest=-2h
| table _time index sourcetype source cv_event_type action signature_id signature severity user dest process process_id app message _raw
```

Expected:

- 3 events
- `index=commvault`
- sourcetype is family-specific: `commvault:commcell:audittrail`, `commvault:commcell:events`, or `commvault:commcell:alerts`
- `source=commvault_commcell`
- `cv_event_type` values: `audit`, `event`, `alert`
- normalized fields populated as appropriate

## 10. SC4S runtime checks

```bash
sudo docker inspect -f 'status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' SC4S
sudo ss -ltnp | grep ':20029'
sudo docker exec SC4S syslog-ng-ctl stats | grep -E 'COMMVAULT|commvault|d_hec_fmt.*(written|dropped|queued|processed)'
sudo docker logs --since '30 minutes ago' SC4S 2>&1 | grep -Ei 'commvault|syntax|parse|parser|error|invalid' || true
```

Expected:

- SC4S healthy
- live listener on `:20029`
- source processed count increases
- destination dropped/queued remain zero
- no Commvault parser syntax errors

## 11. Production cautions

- Do not use source tag alone for index routing. Require Commvault-shaped payloads.
- Do not put HEC tokens in exported UI bundles.
- Do not claim ES CIM compatibility solely from field names. Validate against the specific ES correlation searches/use cases that will consume the data.
- If Commvault is configured for RFC5424, keep the same parser available for `sc4s-syslog`; the payload body still needs to match the Commvault patterns.
- If multiple CommCells should map to different indexes, use separate source/listener IDs or add a deliberate lookup/selector. Do not overload one parser silently.

## 12. SecHub Resources SC4S pack/template packaging model

Commvault should be shipped as a reusable pack, not as a one-off parser. The pack bundle should contain:

```text
packs/commvault_commcell/pack.json
packs/commvault_commcell/sc4s/app_parsers/syslog/app-commvault_commcell.conf
packs/commvault_commcell/sc4s/env.example
packs/commvault_commcell/splunk/default/props.conf
packs/commvault_commcell/splunk/default/transforms.conf
packs/commvault_commcell/splunk/default/eventtypes.conf
packs/commvault_commcell/splunk/default/tags.conf
packs/commvault_commcell/test-events/commvault_test_events.txt
packs/commvault_commcell/scripts/send_tls_20029.sh
packs/commvault_commcell/README.md
```

The `pack.json` manifest defines the pack. Required trust and admin-help fields are `version`, `url`, and `description`. Optional enrichment fields include `supported_transports`, `recommended_transport`, `source_log_version`, and `validation`:

```yaml
id: commvault_commcell
version: 0.1.0
url: https://documentation.commvault.com/11.40/software/configuring_syslog_server.html
description: Commvault CommCell syslog/SIEM pack for AuditTrail, Events, and Alerts. Includes install instructions, parser config, Splunk exports, and test events.
display_name: Commvault CommCell
vendor: commvault
product: commcell
default_index: commvault
default_source: commvault_commcell
listener:
  source_id: COMMVAULT_COMMCELL
  transport: tls
  port: 20029
supported_transports:
  - id: tls_rfc5425
    label: TLS syslog RFC5425
    transport: tls
    format: rfc5424
    recommended: true
    default_port: 20029
  - id: tcp_rfc5424
    label: TCP syslog RFC5424
    transport: tcp
    format: rfc5424
    recommended: false
  - id: udp_bsd
    label: UDP syslog BSD/headerless
    transport: udp
    format: bsd
    recommended: false
recommended_transport: tls_rfc5425
source_log_version:
  name: Commvault Platform Release
  min: null
  max: null
  notes: Set min/max when the customer source version is confirmed.
validation:
  date_validated: 2026-05-26
  source_log_version: Commvault documentation current as of 2026-05-26; lab samples for AuditTrail, Events, Alerts
  sc4s_version: 3.43.0
  splunk_version: 10.2.3
sourcetypes:
  audit: commvault:commcell:audittrail
  event: commvault:commcell:events
  alert: commvault:commcell:alerts
event_families:
  - id: audit
    label: AuditTrail
    match: '^(AuditTrail:|Opid[[:space:]]*=)'
  - id: event
    label: Events
    match: '^(Events?:|Eventid[[:space:]]*=)'
  - id: alert
    label: Alerts
    match: '^(Alerts?:|Alertid[[:space:]]*=)'
exports:
  sc4s: true
  splunk: true
  test_events: true
```

The UI should treat this as the template contract so admins can add many packs later: Palo Alto, Fortinet, Microsoft, Commvault, custom apps, etc.
