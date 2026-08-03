# Kubernetes audit local replay preflight — 2026-06-07

This is command-grounded blocker evidence for the profile-aware replay/read-back harness. It is **not** replay/read-back validation and must not promote trust or quality.

## Commands run

```bash
date -u +%Y-%m-%d
ss -ltn 'sport = :20069'
timeout 3 bash -lc '</dev/tcp/127.0.0.1/20069'
timeout 3 bash -lc '</dev/tcp/127.0.0.1/8089'
timeout 3 bash -lc '</dev/tcp/127.0.0.1/8000'
```

## Result

- Date: `2026-06-07`.
- No local TCP listener was present on `127.0.0.1:20069` for the dedicated Kubernetes audit relay route.
- TCP connect to `127.0.0.1:20069` returned connection refused.
- Local Splunk TEST management/search port `8089` returned connection refused.
- Local Splunk web port `8000` returned connection refused.

Fixture replay, syslog-ng/SC4S parser counters, HEC delivery, indexed Splunk read-back, and Manager apply were not run. The harness remains blocked at the listener/testbed layer.
