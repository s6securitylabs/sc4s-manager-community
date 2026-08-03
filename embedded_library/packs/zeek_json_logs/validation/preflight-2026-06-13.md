# Zeek JSON logs local replay preflight — 2026-06-13

Scope: command-grounded preflight for the intended SC4S TEST -> Splunk TEST route for the `zeek_json_logs` pack.

Commands expected for a live testbed:

```bash
ss -ltn sport = :20083
nc -vz 127.0.0.1 20083
nc -vz 127.0.0.1 8089
nc -vz 127.0.0.1 8000
```

Observed in this autonomous repository run: no local SC4S listener or Splunk TEST service was available on the expected endpoints, so fixture replay, parser counters, HEC delivery, and indexed Splunk read-back were not executed.

This is blocked-preflight evidence only. It is not replay/read-back validation and must not raise `quality_status`, `trust_level`, Review status, or verified labels.
