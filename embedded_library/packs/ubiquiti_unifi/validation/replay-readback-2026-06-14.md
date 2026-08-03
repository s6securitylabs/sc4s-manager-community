# SC4S TEST replay/read-back validation — 2026-06-14

## Scope

- Testbed: `sc4s-test` at `10.10.1.183` running SC4S container `ghcr.io/splunk/splunk-connect-for-syslog/container3:3.43.0`.
- Destination: non-production Splunk TEST LXC `splunk-test` at `10.10.1.251` running Splunk `10.2.3 build 4d61cf8a5c0c`.
- SC4S destination: HEC `https://10.10.100.251:8088/services/collector/event`; token value not recorded.
- Validation marker: `SC4S_REAL_VALIDATE_20260614T005539Z`.
- Source route: pack-specific dedicated TCP syslog listeners, line-delimited fixtures.

## Live listener and env proof

SC4S was recreated after applying pack env settings so the running container, not only the env file, carried the listener configuration:

```text
SC4S_LISTEN_CISCO_ASA_TCP_PORT=20042
SC4S_LISTEN_PROXMOX_TCP_PORT=20074
SC4S_LISTEN_TRUENAS_TCP_PORT=20087
SC4S_LISTEN_UBIQUITI_UNIFI_TCP_PORT=20086
SOURCE_ALL_SET=DEFAULT,CISCO_ASA,PROXMOX,UBIQUITI_UNIFI,TRUENAS
```

Socket read-back after recreation:

```text
tcp LISTEN 0 255 0.0.0.0:20074 0.0.0.0:*  # PROXMOX
tcp LISTEN 0 255 0.0.0.0:20086 0.0.0.0:*  # UBIQUITI_UNIFI
tcp LISTEN 0 255 0.0.0.0:20087 0.0.0.0:*  # TRUENAS
```

SC4S health endpoint returned:

```json
{"status":"healthy"}
```

## SC4S/syslog-ng counter proof

Fixture replay sent 18 events total:

```text
proxmox sent=6 port=20074
ubiquiti_unifi sent=6 port=20086
truenas sent=6 port=20087
```

Relevant syslog-ng counters after replay:

```text
source;s_PROXMOX;;a;processed;6
src.network;s_PROXMOX#0;tcp,127.0.0.1;o;processed;6
source;s_UBIQUITI_UNIFI;;a;processed;6
src.network;s_UBIQUITI_UNIFI#0;tcp,127.0.0.1;o;processed;6
source;s_TRUENAS;;a;processed;6
src.network;s_TRUENAS#0;tcp,127.0.0.1;o;processed;6
dst.http;d_hec_fmt#0;...;written;529
dst.http;d_hec_fmt#0;...;dropped;0
dst.http;d_hec_fmt#0;...;queued;0
```

The HEC `written` counter is cumulative for the running SC4S container. The per-source counters above are the pack-level proof for this replay batch.

## Splunk indexed read-back

Search method: Splunk CLI inside CT1051 using admin credentials read from the Proxmox root-only secret file; credential values are not recorded here.

SPL summary:

```spl
index=infraops OR index=netops SC4S_REAL_VALIDATE_20260614T005539Z earliest=-45m
| stats count min(_time) as first max(_time) as last values(index) as indexes values(sourcetype) as sourcetypes values(source) as sources values(host) as hosts by validation_run
```

Read-back result:

```text
validation_run=SC4S_REAL_VALIDATE_20260614T005539Z
count=18
first=2026-06-14T00:55:40Z
last=2026-06-14T00:56:48Z
indexes=infraops, netops
source=sc4s
host=sc4s-test
```

Sourcetype distribution:

```text
infraops proxmox:ve:auth              count=2
infraops proxmox:ve:service:task      count=2
infraops proxmox:ve:task:summary      count=2
infraops truenas:hardware:disk        count=1
infraops truenas:host:auth            count=1
infraops truenas:middleware:auth      count=1
infraops truenas:replication          count=1
infraops truenas:storage:pool         count=1
infraops truenas:storage:snapshot     count=1
netops   ubiquiti:unifi:admin         count=1
netops   ubiquiti:unifi:client        count=1
netops   ubiquiti:unifi:device        count=1
netops   ubiquiti:unifi:firewall      count=1
netops   ubiquiti:unifi:threat        count=1
netops   ubiquiti:unifi:vpn           count=1
```

## Splunk dashboard XML read-back

The pack dashboard XML files were installed into a temporary Splunk app `sechub_resources_validation` on Splunk TEST and read back through Splunk's REST API:

```text
proxmox_overview: http=ok, count=1, title="Proxmox VE Control-plane Overview"
unifi_overview:   http=ok, count=1, title="Ubiquiti UniFi network telemetry Overview"
truenas_overview: http=ok, count=1, title="TrueNAS storage platform telemetry Overview"
```

## Caveats

- This is S6 lab replay/read-back validation using synthetic-equivalent fixtures, not real product/customer telemetry. It supports `quality_status=validated` and `trust_level=s6_verified`; it does not support `field_validated` or `field_verified`.
- Source host in read-back is `sc4s-test` because fixtures were replayed locally on the SC4S testbed; production relay attribution must be checked with real senders.
- The running SC4S container emitted startup healthcheck connection-refused messages while syslog-ng was starting and repeated TLS compression warnings inherited from the baseline configuration. The container was healthy before replay and all 18 fixture events were indexed.
- A previous CLI attempt accidentally caused Splunk TEST to ingest sudo command lines containing a password in argv; recent `osnix`/`pved1` events were deleted from Splunk TEST after discovery. Future Splunk CLI calls should pass credentials via stdin or local files only.
