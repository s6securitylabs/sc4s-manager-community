# SC4S Manager

A local web UI and control plane for [Splunk Connect for Syslog (SC4S)](https://splunk.github.io/splunk-connect-for-syslog/) operators.

SC4S Manager runs alongside SC4S on your host. It lets you browse and install reviewed packs from [SecHub](https://sechub.s6ops.com), manage SC4S sources, destinations and routes, validate configuration changes before applying them, and monitor SC4S runtime health — all without giving a web process direct access to your Docker socket.

## Quick start

SC4S Manager deploys with SC4S using Docker Compose.

**Prerequisites:** Docker Engine, `/opt/sc4s` directory, Splunk HEC URL and token.

```bash
# 1. Create the SC4S directory layout
sudo mkdir -p /opt/sc4s/{local,archive,tls,manager}

# 2. Copy the Compose bundle
sudo cp deploy/compose/compose.yaml /opt/sc4s/compose.yaml
sudo cp deploy/compose/.env.example /opt/sc4s/.env
sudo cp deploy/compose/env_file.example /opt/sc4s/env_file
sudo cp deploy/compose/manager.env.example /opt/sc4s/manager.env

# 3. Fill in your Splunk HEC URL/token and generate secret values
#    (edit /opt/sc4s/env_file and /opt/sc4s/manager.env)
sudo editor /opt/sc4s/env_file /opt/sc4s/manager.env

# 4. Start the stack
cd /opt/sc4s && sudo docker compose up -d
```

Manager is available at `http://<host>:8090` once the stack is up.

See [docs/runbooks/install.md](docs/runbooks/install.md) for the full install guide including secret handling, proxy setup, and post-install checks.

## What it does

- **Browse SecHub packs** — search the curated source catalogue, download reviewed packs, validate them locally before installing
- **Manage SC4S config** — add and remove sources, destinations, and routes through the UI; preview generated config before any change is applied
- **Validate before apply** — schema checks, parser syntax, fixture semantics, and a post-apply readback gate before config is considered live
- **Monitor runtime** — SC4S process status, listener health, syslog-ng counters, destination write/drop counts, parser warnings
- **Safe apply path** — backup before every change, rollback on validation failure, full audit log of all mutations
- **Export evidence** — download a bundle of applied config and validation evidence for handoff or review

## Packs

Packs are configuration bundles for a specific log source. They include SC4S parser config, Splunk props/transforms, test event fixtures, and CIM/OCSF field mappings.

The `packs/` directory in this repo contains built-in packs. Community pack submissions: see [docs/contributing/pack-submission-guide.md](docs/contributing/pack-submission-guide.md).

## Documentation

| Doc | What it covers |
|-----|----------------|
| [docs/runbooks/install.md](docs/runbooks/install.md) | Full install guide, secret handling, proxy setup |
| [docs/runbooks/upgrade.md](docs/runbooks/upgrade.md) | Upgrading SC4S Manager |
| [docs/runbooks/rollback.md](docs/runbooks/rollback.md) | Rolling back a failed change |
| [docs/contributing/pack-submission-guide.md](docs/contributing/pack-submission-guide.md) | How to submit a pack |
| [docs/contracts/packs-api.md](docs/contracts/packs-api.md) | Pack API contract |
| [docs/architecture.md](docs/architecture.md) | Security model, design principles, workflow detail |

## Repository layout

```
src/sc4s_manager/   Python backend — API, control logic, pack/library code
frontend/           React operator UI
packs/              Built-in packs (PAN-OS, Commvault, ...)
deploy/             Docker Compose bundle, systemd unit, install scripts
docs/               Runbooks, API contracts, contributing guides
scripts/            Validation and test tooling
tests/              Backend test suite
```

## Development

```bash
git clone https://github.com/s6securitylabs/sc4s-manager-community.git
cd sc4s-manager-community
./scripts/test.sh
```

The test script sets up a virtualenv and runs the full backend + frontend test suite.

## Licence

SC4S Manager is proprietary S6 Security Labs software. Use, copying, redistribution, hosted service operation, marketplace bundling, OEM use, or commercial deployment requires a separate written agreement with S6 Security Labs. See [LICENSE](LICENSE).
