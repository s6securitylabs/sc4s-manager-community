# SC4S Manager

A local web UI for [Splunk Connect for Syslog (SC4S)](https://splunk.github.io/splunk-connect-for-syslog/) operators. Manager can stage sources, destinations, routes and Library packs, validate proposed configuration, and report runtime evidence. A saved configuration is **not** proof that SC4S is ingesting events: verify listeners, SC4S health, counters, and Splunk readback separately.

## Deployment boundary

The supported operator path is the Docker Compose bundle in `/opt/sc4s`, beside a pinned SC4S image. It deliberately does **not** mount `/var/run/docker.sock` and it does **not** run the host control daemon. Therefore a Compose-only deployment can manage desired configuration but cannot use Manager's control-socket actions (validate through the daemon, reload, restart, Docker status, logs, metrics, or listener inspection). Those controls must show unavailable; do not add a Docker-socket mount to bypass this boundary.

The packaged systemd control units provide an optional narrow host-control boundary. The socket unit owns `/run/sc4s-manager/control.sock` with mode `0660`; the root-only daemon consumes that listener through systemd socket activation and retains the fixed action allowlist. This is a separate topology from Compose: enabling it does not add host control to a Compose-only Manager container unless a separately reviewed deployment mounts that narrow socket. See the install runbook before enabling it.

## Quick start (Compose, configuration management only)

Read the [install runbook](docs/runbooks/install.md) first. In particular, set and record a fixed Manager release tag or digest before starting; do not substitute `latest` for the reviewed release reference.

```bash
# Run from a checkout or extracted release that contains deploy/compose/.
sudo install -d -o root -g 10001 -m 0770 /opt/sc4s/{env,local,archive,tls,manager}
sudo docker volume create splunk-sc4s-var
sudo install -m 0640 -o root -g 10001 deploy/compose/env_file.example /opt/sc4s/env/env_file
sudo ln -sfn env/env_file /opt/sc4s/env_file
sudo install -m 0640 -o root -g 10001 deploy/compose/manager.env.example /opt/sc4s/manager.env
sudo install -m 0644 deploy/compose/.env.example /opt/sc4s/.env
sudo install -m 0644 deploy/compose/compose.yaml /opt/sc4s/compose.yaml
sudo editor /opt/sc4s/.env /opt/sc4s/env/env_file /opt/sc4s/manager.env
cd /opt/sc4s
sudo docker compose -f compose.yaml config -q
sudo docker compose -f compose.yaml up -d
sudo docker compose -f compose.yaml ps
curl -fsS http://127.0.0.1:8090/health
```

Expected: `config -q` is silent with exit code 0; both `sc4s` and `manager` are running; `/health` is JSON with `"status": "ok"`. The nested `sc4s.ok` result must also be true before treating SC4S as ready. Stop and investigate if a container restarts, the health request fails, or either image is unpinned.

The published Manager port is not an authentication boundary. Put it behind an approved reverse proxy or restrict it with a host firewall before exposing it beyond the administrator network. See [authentication and proxy setup](docs/runbooks/install.md#authentication-and-reverse-proxy).

## What it does

- **Browse SC4S Library packs** — download packs, verify their checksum, validate them locally, and stage them before explicit apply.
- **Manage SC4S configuration** — preview changes to sources, destinations, and routes before applying them.
- **Preserve evidence** — retain validation, backup, audit and export material subject to the configured storage and retention policy.
- **Report state honestly** — distinguish desired configuration from unavailable, observed, and verified runtime state.

## Operator documentation

| Document | Use it for |
|---|---|
| [Install runbook](docs/runbooks/install.md) | host preparation, Compose start, authentication, verification, and common failures |
| [Upgrade runbook](docs/runbooks/upgrade.md) | safe Compose image upgrade and abort criteria |
| [Rollback runbook](docs/runbooks/rollback.md) | reverting a Manager image and proving the rollback |
| [Install/upgrade/rollback drill](docs/runbooks/install-upgrade-rollback-drill.md) | disposable-host release evidence; not a production procedure |
| [Release artifact](docs/runbooks/release-artifact.md) | building and checking a distributable artifact |
| [Architecture](docs/architecture.md) | security, proxy-header and control-boundary contract |

## Development

```bash
git clone https://github.com/s6securitylabs/sc4s-manager-community.git
cd sc4s-manager-community
./scripts/test.sh
```

## Licence

SC4S Manager is proprietary S6 Security Labs software. Use, copying, redistribution, hosted service operation, marketplace bundling, OEM use, or commercial deployment requires a separate written agreement with S6 Security Labs. See [LICENSE](LICENSE).
