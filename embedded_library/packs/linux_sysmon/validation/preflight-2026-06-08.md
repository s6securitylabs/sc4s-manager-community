# Linux Sysmon replay preflight — 2026-06-08

This is command-grounded blocker evidence only. It is not replay/read-back validation and must not promote trust or quality labels.

## Intended route

- Profile: `linux_sysmon`
- Listener: TCP syslog, `127.0.0.1:20072`
- Expected index: `osnix`
- Fixture marker prefix: `SC4S_LINUX_SYSMON_TEST_`

## Local preflight result

This scheduled maintenance host does not have the dedicated SC4S listener or a local Splunk TEST endpoint available for this profile. Replay, HEC delivery, indexed read-back, and eventtype/tag verification were not run.

```text
$ ss -ltn sport = :20072
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ python3 socket connect checks
linux_sysmon listener 127.0.0.1:20072: ConnectionRefusedError: [Errno 111] Connection refused
splunk management 127.0.0.1:8089: ConnectionRefusedError: [Errno 111] Connection refused
splunk web 127.0.0.1:8000: ConnectionRefusedError: [Errno 111] Connection refused
```

Promotion requires a real Linux Sysmon relay plus Splunk read-back evidence proving expected count, sourcetypes, timestamps, source, EventID/provider/channel, process/network/file/config fields, and no unwanted drops.
