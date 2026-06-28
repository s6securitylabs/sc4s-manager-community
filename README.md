# SC4S Manager

SC4S Manager is the private operator control plane for managing SC4S-compatible ingestion environments. It helps operators import packs, validate them locally, preview configuration changes, apply those changes safely, observe runtime state, and roll back when needed.

SC4S Manager is intentionally separate from the **SC4S Library** and the public SecHub catalogue surface. The Library answers: *what reviewed packs exist and what evidence do they carry?* The Manager answers: *can this pack be safely used in my environment, and how do I operate it?*

## Product boundary

- **SC4S Manager** (`s6securitylabs/sc4s-manager`): private control plane, operator UI/API, local validation, pack import, SC4S configuration management, runtime visibility, audit, backup, apply, and rollback.
- **SecHub Resources** (`s6securitylabs/sechub-resources`): private canonical pack catalogue/source repository, submission review workflow, trust labels, evidence, generated artifact source, and downloadable pack generation.
- **Security Engineering Hub / SecHub** (`s6securitylabs/sechub` / `https://sechub.s6ops.com/`): the canonical V1 public surface for catalogue discovery, public artifact routes, and public submission intake.

Library artifacts are input to the Manager. They are not trusted until the Manager verifies checksum/signature, validates schema/fixtures, previews generated changes, and passes local deployment checks.

## What the Manager does

- Shows desired configuration and live runtime state separately.
- Imports packs from the SC4S Library or local files.
- Validates pack schemas, parser artifacts, fixture semantics, and generated outputs.
- Previews SC4S and Splunk configuration changes before apply.
- Applies approved changes through a narrow local control plane, not direct web access to the Docker socket.
- Creates backups before risky operations.
- Provides rollback paths for failed or unwanted changes.
- Surfaces listener health, SC4S container status, counters, parser warnings, and destination status.
- Exports evidence for customer handoff and implementation proof.
- Redacts secrets in API responses, diffs, audit logs, exports, and reports.

## What the Manager does not do

- It does not host the public pack catalogue.
- It does not let Library trust labels bypass local validation.
- It does not grant the web UI unrestricted host or Docker control.
- It does not store secrets in generated pack exports.
- It does not silently drop or reduce events by default.
- It does not turn unreviewed Library branches into deployable production content without operator review.

## Architecture principles

- Web/API process runs non-root.
- Web/API process has no Docker socket access.
- Mutating operations go through a narrow local control daemon over a Unix socket.
- Changes follow preview → validate → backup → apply → post-check → rollback-ready.
- Runtime state and desired configuration are displayed separately.
- All mutating actions are audited.
- Secrets and sensitive values are redacted everywhere by default.

## Core workflows

### 1. Import from SC4S Library

1. Fetch configured Library catalogue JSON.
2. Display pack trust level, evidence, limitations, and download eligibility without implying local apply.
3. Download selected bundle.
4. Verify checksum/signature metadata.
5. Validate pack schema, artifacts, and test events locally.
6. Store pack provenance and evidence in local inventory.
7. Keep imported pack as draft until the operator explicitly applies it.

### SC4S Library source/import/apply layout

Manager keeps remote Library content separate from local runtime state.

V1 source registry posture:

- `sechub.s6ops.com` is the canonical V1 SecHub public host for catalogue/download/checksum routes once deployed and live-read back.
- Do not point Manager at retired SecHub Resources hostnames or repository-only URLs for runtime catalogue sync.
- Private/automation consumers may still fetch the canonical `s6securitylabs/sechub-resources` repository, check out reviewed `main` or an approved release tag, and build/consume generated artifacts from that clean checkout.
- Regardless of source, Manager treats all fetched artifacts as untrusted input until local checksum, schema, fixture, preview, apply, and runtime/readback gates pass.

Manager state layout under `MANAGER_ROOT/state/library/`:

```text
state/library/
  sources.json                         source registry cache + last_sync metadata
  catalogue/<source_id>.json          cached remote catalogue payload
  downloads-manifest-<source_id>.json cached remote downloads manifest
  entries/<source_id>/<entry_id>.json cached remote entry detail
  downloads/<source_id>/<filename>    verified bundle zip cache
  imports/<import_id>/
    bundle/                           extracted bundle, never applied directly
    reference/                        non-runtime artifacts staged for review only
    runtime-plan.json                 runtime-safe apply plan
    record.json                       import record, provenance, apply status
```

Runtime-safe apply boundary:

- only `local/config/` and `local/context/` targets are eligible for apply
- `env_file.d/`, `splunk_app/`, `test-events/`, `scripts/`, and docs stay staged as reference-only artifacts
- bundle zip members must pass path, size, duplicate, traversal, and symlink safety checks
- bundle SHA256 must match the entry download metadata; v1 does not require signing
- apply always revalidates staged runtime artifacts against `manifest.json` before copying
- apply creates backups, validates config, reloads through the local control path, and rolls back on validation failure

### 2. Save a staged source

1. Select or clone a pack.
2. Save listener/source parameters as staged changes.
3. Preview generated env/parser/Splunk changes.
4. Validate SC4S configuration and parser syntax.
5. Send marker or fixture events through the real listener where safe.
6. Verify counters and indexed events when Splunk access is configured.
7. Apply through the control daemon.
8. Record audit and evidence.

### 3. Operate and troubleshoot

- View container/control-plane health.
- View listener/socket state.
- View syslog-ng/source/parser/filter/destination counters.
- View recent warnings and failed validation checks.
- Export evidence bundles for handoff.
- Roll back to the last known-good backup.

## Release deployment

SC4S Manager is Docker-first, matching the normal SC4S operator process:

- Install from `/opt/sc4s`.
- Keep SC4S runtime settings in `/opt/sc4s/env_file`.
- Keep Manager settings in `/opt/sc4s/manager.env`.
- Keep local parser/config material under `/opt/sc4s/local`.
- Keep archive/TLS material under `/opt/sc4s/archive` and `/opt/sc4s/tls`.
- Keep syslog-ng disk-buffer state in the `splunk-sc4s-var` Docker volume.

Primary release path:

```bash
sudo mkdir -p /opt/sc4s/{local,archive,tls,manager}
sudo cp deploy/compose/compose.yaml /opt/sc4s/compose.yaml
sudo cp deploy/compose/.env.example /opt/sc4s/.env
sudo cp deploy/compose/env_file.example /opt/sc4s/env_file
sudo cp deploy/compose/manager.env.example /opt/sc4s/manager.env
cd /opt/sc4s
sudo docker compose -f compose.yaml up -d
```

The template runs the pinned SC4S image and
`ghcr.io/s6securitylabs/sc4s-manager:<version>` without mounting the host Docker
socket into Manager. Standalone binary and systemd/tarball releases remain
secondary controlled-host paths; they must keep the same `/opt/sc4s` layout,
secret handling, and runtime-control boundary.

See `docs/runbooks/install.md` and `docs/runbooks/release-artifact.md` for the
line-by-line process.

## Repository layout

```text
src/sc4s_manager/          Manager API, control logic, pack/catalogue code
frontend/               Operator UI
packs/                  Built-in/local packs
catalogue/              Generated/imported catalogue data
community/              Community/candidate source material and ingestion notes
docs/contracts/         API and data contracts
docs/runbooks/          Install, upgrade, rollback, and operations runbooks
docs/acceptance/        Deployment and release evidence
docs/roadmap/           Feature plans and implementation roadmaps
docs/product-requirements.md  Manager PRD/spec
scripts/                Test, validation, install, and evidence scripts
```

## Development

Clone the canonical repository:

```bash
git clone https://github.com/s6securitylabs/sc4s-manager.git
cd sc4s-manager
```

## Test bootstrap

Use the repository bootstrap script for development checks:

```bash
./scripts/test.sh
```

The script uses writable temp defaults for virtualenv, coverage, pytest cache, and validation evidence so tests can run without writing generated state into the repository.

## Product requirements

The Manager PRD/spec lives at:

- `docs/product-requirements.md`

Read it before changing Manager import behavior, pack lifecycle, validation/apply workflows, runtime observability, security boundaries, or Library integration assumptions.

## Licence

SC4S Manager is proprietary S6 Security Labs software. Use, copying, redistribution, hosted service operation, marketplace bundling, OEM use, or commercial deployment requires a separate written agreement with S6 Security Labs. See `LICENSE`.
