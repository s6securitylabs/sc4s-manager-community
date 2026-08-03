# Postfix / Dovecot mail syslog validation preflight — 2026-06-08

This is command-grounded blocked preflight evidence for the intended SC4S TEST -> Splunk TEST path. It is not replay/read-back validation and does not promote trust.

## Intended route

- Profile: `postfix_dovecot_mail`
- Listener: TCP line-delimited syslog on `127.0.0.1:20077`
- Expected index: `email`
- Fixture set: `postfix_dovecot_mail_records` (`5` events)
- Marker prefix: `SC4S_POSTFIX_DOVECOT_MAIL_TEST_`

## Local preflight result

```text
127.0.0.1:20077 ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8089 ConnectionRefusedError: [Errno 111] Connection refused
127.0.0.1:8000 ConnectionRefusedError: [Errno 111] Connection refused
```

The dedicated SC4S listener was not present, and local Splunk TEST management/web ports were not reachable. Fixture replay, SC4S/syslog-ng counter checks, HEC delivery, indexed Splunk read-back, and timestamp verification were not run.

## Required unblock

Provision a non-production SC4S/Splunk route for TCP 20077 with write/read access to `email`, then run `scripts/send_tcp_20077.sh` and confirm all markers through the profile validation SPL in `README.md` and `pack.json.validation_harness.readback.spl`.
