# SC4S Manager Release Artifact

## What is the release artifact?

A SC4S Manager release is a `sc4s-manager-<version>.tar.gz` tarball with a `manifest.json` placed beside it. The tarball extracts under a deterministic root directory `sc4s-manager/`.

The manifest records the artifact version, git commit, creation timestamp, the SHA-256 and size of each included file, whether the frontend dist was present at package time, and any required paths that were absent.

## Required contents

The manifest contract (`src/sc4s_manager/packaging.py:REQUIRED_ARTIFACT_PATHS`) requires release/install paths that support three operator distribution modes:

1. GitHub release tarball for systemd/manual installs.
2. Docker image plus Compose template.
3. Single-file Linux binary for operators who do not want a Python checkout.

Required paths inside the tarball include:

```
sc4s-manager/src/sc4s_manager/app.py
sc4s-manager/src/sc4s_manager/control.py
sc4s-manager/src/sc4s_manager/standalone.py
sc4s-manager/Dockerfile
sc4s-manager/deploy/compose/compose.yaml
sc4s-manager/deploy/compose/.env.example
sc4s-manager/deploy/compose/env_file.example
sc4s-manager/deploy/compose/manager.env.example
sc4s-manager/scripts/build_binary.py
sc4s-manager/.github/workflows/release.yml
sc4s-manager/deploy/systemd/sc4s-manager.service
sc4s-manager/deploy/systemd/sc4s-manager-control.service
sc4s-manager/deploy/systemd/sc4s-manager-control.socket
sc4s-manager/deploy/install/install.sh
sc4s-manager/deploy/upgrade/upgrade.sh
sc4s-manager/frontend/dist/index.html
```

## Building a release artifact

1. Build the frontend first (required; never run from install/upgrade scripts):

   ```bash
   scripts/build_frontend.sh
   ```

2. Build the release tarball:

   ```bash
   python3 scripts/build_release_artifact.py --version 0.9.0 --output-dir dist/
   ```

   This writes `dist/sc4s-manager-0.9.0.tar.gz` and `dist/manifest.json`.

3. Build the standalone Linux binary from a Python environment with PyInstaller:

   ```bash
   python3 -m venv /tmp/sc4s-manager-build
   . /tmp/sc4s-manager-build/bin/activate
   pip install --upgrade pip pyinstaller
   python3 scripts/build_binary.py --version 0.9.0 --output-dir dist/
   ```

   This writes `dist/sc4s-manager-0.9.0-linux-x86_64`. The binary embeds the
   Manager app, built frontend assets, and built-in packs. On first start it
   seeds those assets into `SC4S_MANAGER_ROOT` only when they are absent.

4. Inspect the manifest to confirm no required paths are missing:

   ```bash
   python3 -c "import json; m=json.load(open('dist/manifest.json')); print(m['missing_required_paths'])"
   ```

5. Generate checksums before uploading release assets:

   ```bash
   (cd dist && sha256sum * > SHA256SUMS)
   ```

## Docker image and Compose

The release workflow publishes:

```text
ghcr.io/s6securitylabs/sc4s-manager:<version>
ghcr.io/s6securitylabs/sc4s-manager:latest
```

Operators deploy from `/opt/sc4s`, following the same directory and environment
file pattern as upstream SC4S:

```bash
sudo mkdir -p /opt/sc4s/{local,archive,tls,manager}
sudo docker volume create splunk-sc4s-var
sudo cp deploy/compose/compose.yaml /opt/sc4s/compose.yaml
sudo cp deploy/compose/.env.example /opt/sc4s/.env
sudo cp deploy/compose/env_file.example /opt/sc4s/env_file
sudo cp deploy/compose/manager.env.example /opt/sc4s/manager.env
# edit /opt/sc4s/.env, /opt/sc4s/env_file, and /opt/sc4s/manager.env using values from the approved secret store
cd /opt/sc4s
sudo docker compose -f compose.yaml up -d
```

The Compose bundle keeps SC4S settings in `/opt/sc4s/env_file`, Manager settings
in `/opt/sc4s/manager.env`, local parser/config material in `/opt/sc4s/local`,
archive/TLS material in `/opt/sc4s/archive` and `/opt/sc4s/tls`, and syslog-ng
state in the `splunk-sc4s-var` Docker volume.

The Compose template deliberately does **not** mount `/var/run/docker.sock`.
Without a host-provided narrow control socket, Manager runtime restart/reload
control is unavailable and should be reported as unknown/unavailable rather than
faked. This keeps the web-adjacent Manager container away from host-root Docker
control.

## Dry-run / CI-only builds

For CI pipelines where the frontend has not been pre-built, pass `--allow-missing-frontend`. This is for test use only and must not be used for release candidates distributed to operators:

```bash
python3 scripts/build_release_artifact.py --version 0.0.1-ci --output-dir /tmp/test-artifact --allow-missing-frontend
```

## What the artifact does NOT do

- Does not run `npm`, `npm ci`, `npm run build`, or any frontend build step.
- Does not contain secrets, tokens, or unredacted credentials.
- Does not contain the full git history or development toolchain.

## Install and upgrade

- See `docs/runbooks/install.md` for clean install steps.
- See `docs/runbooks/upgrade.md` for upgrade steps.
- See `docs/runbooks/install-upgrade-rollback-drill.md` for the full drill procedure.
