# SC4S Manager Install/Upgrade/Rollback Drill

Run this release drill only on a disposable Docker-capable VM/LXC. It produces evidence about the artifact and the **Compose lifecycle**; it is not a production deployment procedure. Take a host snapshot labelled `CLEAN-BASELINE` before mutation and redact evidence before storing it.

## Important implementation boundary

`deploy/install/install.sh` and `deploy/upgrade/upgrade.sh` are dry-run planners. `--execute`, `--apply`, and `--rollback` intentionally return exit code 2. A prior drill command using those flags is invalid and must not be counted as live install/upgrade/rollback proof.

The Compose bundle has no control daemon. Do not test systemd control socket activation as part of this drill and do not add a Docker socket mount. Control-socket absence is expected in the Compose deployment.

## Prerequisites

- Disposable host with Docker Engine, Docker Compose v2, internet/registry access as required, and a snapshot.
- A built `sc4s-manager-<version>.tar.gz`, adjacent `manifest.json`, checksums, and two known Manager image references: a baseline and a candidate.
- Non-production HEC/test destination credentials and a safe marker/readback plan.
- A temporary evidence directory outside the repository, for example `/tmp/sc4s-manager-drill`.

## 1. Verify artifact shape without mutation

```bash
mkdir -p /tmp/sc4s-manager-drill
python3 scripts/validate_package_install.py \
  --dry-run \
  --artifact sc4s-manager-<version>.tar.gz \
  --workdir /tmp/sc4s-manager-drill \
  --evidence-out /tmp/sc4s-manager-drill/package-dry-run.json
```

Expected: exit 0 and a redacted JSON report. This proves package structure/planner behavior only; it does not prove service installation or lifecycle.

## 2. Install baseline Compose stack

Extract the artifact, use its Compose template, and follow the permission/authentication instructions in [install.md](install.md). Set a fixed baseline Manager version in `.env`, not `latest`.

```bash
tar -xzf sc4s-manager-<version>.tar.gz
cd sc4s-manager
sudo install -d -o root -g 10001 -m 0770 /opt/sc4s/{env,local,archive,tls,manager}
sudo docker volume create splunk-sc4s-var
sudo install -m 0644 deploy/compose/compose.yaml /opt/sc4s/compose.yaml
sudo install -m 0644 deploy/compose/.env.example /opt/sc4s/.env
sudo install -m 0640 -o root -g 10001 deploy/compose/env_file.example /opt/sc4s/env/env_file
sudo ln -sfn env/env_file /opt/sc4s/env_file
sudo install -m 0640 -o root -g 10001 deploy/compose/manager.env.example /opt/sc4s/manager.env
sudo editor /opt/sc4s/.env /opt/sc4s/env/env_file /opt/sc4s/manager.env
cd /opt/sc4s
sudo docker compose -f compose.yaml config -q
sudo docker compose -f compose.yaml up -d
sudo docker compose -f compose.yaml ps
curl -fsS http://127.0.0.1:8090/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/health
```

Record the baseline Manager/SC4S image references, `ps`, redacted health output, and a listing/hash of state to be preserved under `/opt/sc4s/manager`.

## 3. Upgrade candidate Manager image

Back up `/opt/sc4s/manager`, `local`, `env/` (including the `env_file` symlink), `manager.env`, `.env`, and `compose.yaml`, then follow [upgrade.md](upgrade.md) to pin, pull, and recreate only `manager`. Record the pre/post image references and retain state-preservation evidence.

The candidate fails the drill if Compose rewrites SC4S, Manager or SC4S fails health, state disappears, unexpected permissions fail, or the configured test marker cannot be proven downstream when downstream proof is in scope.

## 4. Roll back to baseline Manager image

Follow [rollback.md](rollback.md) using the image reference recorded in step 2. Record the returned Manager image reference, `docker compose ps`, redacted health responses, logs, and preserved state listing. A green `docker compose up -d` alone is not a rollback pass.

## 5. Record evidence and gate it honestly

Create evidence based on `docs/acceptance/package-install-template.json`. A real Compose drill should set `install.ok`, `upgrade.ok`, and `rollback.ok` only after the corresponding observed checks pass. Identify `control_daemon` as unavailable/not exercised for this Compose topology instead of fabricating success.

```bash
python3 scripts/validate_acceptance_evidence.py --require-package-drill
```

Expected: this gate fails until a timestamped, redacted `docs/acceptance/package-install-<timestamp>.json` with real lifecycle evidence exists. A dry-run report is insufficient. If the host lacks Docker/systemd/safe downstream access, record the concrete blocker and keep the release lifecycle claim blocked.

## Redaction checklist

- No HEC/API/proxy/manual tokens, cookies, private keys, or authorization headers.
- No unapproved internal hostnames or addresses.
- Artifact and image digests are recorded; secret values are not.
- Command evidence records arguments only after token/header redaction.
