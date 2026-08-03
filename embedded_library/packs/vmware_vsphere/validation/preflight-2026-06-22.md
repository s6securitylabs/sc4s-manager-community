# VMware vSphere local replay preflight — 2026-06-22

## Scope

Command-grounded blocker check for the pack-level `validation_harness`. This is **not** replay/read-back validation. No fixture events were sent, no SC4S/syslog-ng counters were checked, no HEC delivery was attempted, and no Splunk indexed read-back was performed.

Expected replay path when a lab is available:

- Listener/source tag: `VMWARE_VSPHERE`
- Transport: TLS syslog / RFC5425, octet-counted
- Port: `20051`
- Expected indexes: `infraops`, `netfw`
- Fixture set: `vmware_vsphere_mixed_syslog`
- Expected marker prefix: `SC4S_VMWARE_VSPHERE_TEST_`
- Expected event count: `6`

## Commands and results

```console
$ ss -ltn 'sport = :20051'
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ timeout 5 openssl s_client -connect 127.0.0.1:20051 -brief </dev/null
40971D70A8760000:error:8000006F:system library:BIO_connect:Connection refused:../crypto/bio_sock2.c:183:calling connect()
40971D70A8760000:error:10000067:BIO routines:BIO_connect:connect error:../crypto/bio_sock2.c:185:
connect:errno=111

$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8089'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused

$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8000'
# exit 0; TCP connect succeeded, but no authenticated Splunk search/read-back was run.
```

## Verdict

Blocked at the source listener and Splunk management/search-auth layers:

- No local TLS/RFC5425 listener was bound on `127.0.0.1:20051`.
- TLS connect to `127.0.0.1:20051` returned `connect:errno=111`.
- Local Splunk management/search endpoint `127.0.0.1:8089` refused the TCP connection.
- Local Splunk Web `127.0.0.1:8000` accepted TCP, but that is not indexed read-back evidence.

Keep `validation_harness.status=blocked`, `quality_status=curated`, and `trust_level=unverified` until replay through the intended route and Splunk indexed read-back evidence are captured.
