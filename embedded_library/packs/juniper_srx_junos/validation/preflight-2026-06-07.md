# Juniper SRX/Junos local replay preflight - 2026-06-07

Repository: /home/jarvis/work/sechub-resources
Profile: packs/juniper_srx_junos
Intended route: TCP syslog listener 127.0.0.1:20044 -> SC4S TEST -> Splunk TEST index netfw

## Listener check: ss -ltn sport = :20044
State Recv-Q Send-Q Local Address:Port Peer Address:Port

## TCP connect check: 127.0.0.1:20044
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/20044: Connection refused
connect failed

## Splunk management check: 127.0.0.1:8089
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8089: Connection refused
connect failed

## Splunk web check: 127.0.0.1:8000
bash: connect: Connection refused
bash: line 1: /dev/tcp/127.0.0.1/8000: Connection refused
connect failed

## Result
Blocked at listener layer: no local TCP syslog listener on 127.0.0.1:20044. Splunk TEST management/web checks also refused local TCP connections. No fixture replay, SC4S/syslog-ng counter check, HEC delivery, or Splunk indexed read-back was performed.
