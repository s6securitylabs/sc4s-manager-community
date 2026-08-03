# NetApp ONTAP replay preflight — 2026-06-07

Purpose: command-grounded check for the profile-aware SC4S TEST -> Splunk TEST replay route before any trust/quality promotion.

## Commands
```text
$ ss -ltn sport = :20093
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ timeout 5 openssl s_client -connect 127.0.0.1:20093 -brief </dev/null
00F186804E770000:error:8000006F:system library:BIO_connect:Connection refused:crypto/bio/bio_sock2.c:183:calling connect()
00F186804E770000:error:10000067:BIO routines:BIO_connect:connect error:crypto/bio/bio_sock2.c:185:
connect:errno=111

$ python3 - <<PY (TCP reachability for Splunk management/web)
Splunk management 127.0.0.1:8089: not reachable (ConnectionRefusedError: [Errno 111] Connection refused)
Splunk web/search UI 127.0.0.1:8000: not reachable (ConnectionRefusedError: [Errno 111] Connection refused)
```

## Result

Blocked at listener/testbed preflight. No TCP/TLS listener was available on 127.0.0.1:20093 for the dedicated NetApp ONTAP route, and local Splunk management/web ports were not reachable from this host. No fixture replay, indexed read-back, trust promotion, or quality promotion was performed.
