# Fortinet FortiGate/FortiOS replay preflight — 2026-06-07

Profile: `fortinet_fortigate_fortios`
Target route: dedicated SC4S TEST TLS/RFC5425 listener on `127.0.0.1:20032`
Expected read-back: three `SC4S_FORTINET_FORTIGATE_TEST_*` fixture markers in Splunk TEST index `netfw`.

## Verdict

Blocked at the listener/testbed layer. No fixture replay, SC4S/syslog-ng counter check, HEC delivery, or Splunk indexed read-back was performed.

## Command evidence

```text
$ ss -ltn sport = :20032
State Recv-Q Send-Q Local Address:Port Peer Address:Port
```

Only the header row was returned, so no local TCP listener was bound to port `20032`.

```text
$ timeout 5 openssl s_client -connect 127.0.0.1:20032 -servername localhost </dev/null
0001E55D41770000:error:8000006F:system library:BIO_connect:Connection refused:crypto/bio/bio_sock2.c:183:calling connect()
0001E55D41770000:error:10000067:BIO routines:BIO_connect:connect error:crypto/bio/bio_sock2.c:185:
connect:errno=111
```

TLS connection to the intended Fortinet listener was refused before any RFC5425 fixture send could occur.

```text
$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8089'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused

$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8000'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
```

Local Splunk management (`8089`) and web/search (`8000`) ports were also unreachable, so indexed read-back could not be attempted from this host.

## Follow-up needed

Start or provide access to the SC4S TEST listener and Splunk TEST search tier, then run `packs/fortinet_fortigate_fortios/scripts/send_tls_20032.sh` and verify the profile-aware SPL in `pack.json.validation_harness.readback.spl`.
