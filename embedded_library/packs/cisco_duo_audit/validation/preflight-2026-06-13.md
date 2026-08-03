# Cisco Duo Audit blocked local preflight

This scheduled-run preflight checks only local listener/Splunk reachability. It is not replay/read-back validation.

```console
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-06-13T21:02:32Z
```

```console
$ ss -ltn 'sport = :20088' || true
State Recv-Q Send-Q Local Address:Port Peer Address:Port
```

```console
$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/20088' && echo tcp/20088-open || echo tcp/20088-refused
tcp/20088-refused
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20088: Connection refused
```

```console
$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8089' && echo splunk-8089-open || echo splunk-8089-refused
splunk-8089-refused
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
```

```console
$ timeout 3 bash -lc '</dev/tcp/127.0.0.1/8000' && echo splunk-8000-open || echo splunk-8000-refused
splunk-8000-refused
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
```
