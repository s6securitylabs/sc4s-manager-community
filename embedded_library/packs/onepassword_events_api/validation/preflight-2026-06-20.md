# 1Password Events API relay preflight — 2026-06-20

This is blocked preflight evidence only. It is not replay/read-back validation.

Commands expected for a real validation run:

```bash
ss -ltn sport = :20098
nc -vz 127.0.0.1 20098
nc -vz 127.0.0.1 8089
nc -vz 127.0.0.1 8000
```

Autonomous repository run result: no 1Password SC4S TEST listener or authenticated Splunk TEST search path was available in this checkout, so fixture replay, SC4S/syslog-ng counters, HEC delivery, and indexed read-back were not attempted. A real promotion requires three marked records read back from `index=netauth sourcetype=1password:events` with expected family, action/category/type, actor/target, object/item, client, source IP/session, and raw JSON fields.
