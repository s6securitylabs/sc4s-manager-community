# Sophos Firewall preflight — 2026-06-20

This is command-grounded blocker evidence for the initial Sophos Firewall SFOS syslog pack. It is not replay/read-back validation and must not promote Review status, `quality_status`, or `trust_level`.

## Commands run

```text
$ date -u
Sat Jun 20 11:01:37 AM UTC 2026

$ ss -ltn 'sport = :20097'
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ python TCP probes
Sophos Firewall listener 127.0.0.1:20097: blocked/refused (ConnectionRefusedError: [Errno 111] Connection refused)
Splunk management 127.0.0.1:8089: blocked/refused (ConnectionRefusedError: [Errno 111] Connection refused)
Splunk web 127.0.0.1:8000: connected
```

## Result

- Sophos Firewall TLS/RFC5425 listener on TCP 20097 was not present.
- Splunk management/search API on TCP 8089 was not reachable from this host.
- Splunk web on TCP 8000 accepted a TCP connection, but no authenticated search/read-back was attempted.
- Fixture replay, SC4S/syslog-ng counters, HEC delivery, and indexed Splunk read-back were not run.

## Required unblock

Provision a non-production SC4S TEST route for source tag `SOPHOS_FIREWALL` / listener TCP 20097, ensure `netfw`, `netauth`, and `netops` are searchable by the TEST role, replay `test-events/sophos_firewall_test_events.txt` through `scripts/send_tls_20097.sh`, then read back the markers and required fields with the SPL recorded in `pack.json` and `README.md`.
