# Microsoft Defender XDR local replay preflight — 2026-06-07

This evidence records a local preflight for the curated/unverified `microsoft_defender_xdr` profile. It is command-grounded blocker evidence only; it is not SC4S replay, HEC delivery, indexed Splunk read-back, S6 verification, or field validation.

## Listener preflight

```text
$ ss -ltn sport = :20067
State Recv-Q Send-Q Local Address:Port Peer Address:Port

$ timeout 3 bash -c '</dev/tcp/127.0.0.1/20067'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20067: Connection refused
exit=1
```

## Splunk TEST reachability preflight

```text
$ timeout 3 bash -c '</dev/tcp/127.0.0.1/8089'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
exit=1

$ timeout 3 bash -c '</dev/tcp/127.0.0.1/8000'
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
exit=1
```

## Result

- Blocker layer: `listener`.
- No TCP listener was reachable on `127.0.0.1:20067`.
- Local Splunk TEST management/web ports were also unavailable on `127.0.0.1:8089` and `127.0.0.1:8000`.
- Fixture replay, SC4S/syslog-ng counters, HEC delivery, and Splunk indexed read-back were not run.
