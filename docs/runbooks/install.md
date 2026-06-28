# Install Runbook

## Scope

This runbook covers a clean SC4S Manager install using the same Docker-first
operator process as SC4S. Do not paste real HEC tokens, API tokens, proxy
secrets, or private keys into this document or the repository.

## Distribution choices

SC4S Manager is Docker-first:

- **Primary path — Docker Compose in `/opt/sc4s`**: use the published GHCR image
  `ghcr.io/s6securitylabs/sc4s-manager:<version>` beside the pinned SC4S image in
  `deploy/compose/compose.yaml`.
- **Secondary path — GitHub release binary**: for a controlled single-host admin
  utility where SC4S already exists and a service manager/proxy supplies the same
  runtime directories and secrets.
- **Secondary path — GitHub release tarball/systemd**: for lab or transitional
  installs that cannot yet run the Compose bundle.

The binary and systemd paths must not become a separate product requirement set.
They use the same `/opt/sc4s` runtime layout, secret handling, validation order,
and no-Docker-socket rule as the Compose deployment.

## Preconditions

- Linux host with Docker Engine or Docker Desktop/Compose approved for the environment.
- SC4S runtime pinned to `ghcr.io/splunk/splunk-connect-for-syslog/container3:3.43.0` unless a version-drift review approves a different image.
- External secret source prepared for Splunk HEC token, manager API token, and
  proxy shared secret.
- DNS, firewall, listener ports, and `/opt/sc4s` disk capacity approved.
- `/opt/sc4s` is the operator-owned deployment directory, matching upstream SC4S
  guidance for local configuration and disk-buffer state.

## Docker Compose quick start

1. Create the SC4S deployment directory and local runtime subdirectories:

   ```bash
   sudo mkdir -p /opt/sc4s/{local,archive,tls,manager}
   sudo docker volume create splunk-sc4s-var
   ```

2. Download or copy `deploy/compose/` from the GitHub release tarball, then stage
   the files under `/opt/sc4s`:

   ```bash
   sudo cp deploy/compose/compose.yaml /opt/sc4s/compose.yaml
   sudo cp deploy/compose/.env.example /opt/sc4s/.env
   sudo cp deploy/compose/env_file.example /opt/sc4s/env_file
   sudo cp deploy/compose/manager.env.example /opt/sc4s/manager.env
   ```

3. Edit `/opt/sc4s/.env`, `/opt/sc4s/env_file`, and `/opt/sc4s/manager.env` using
   values from the approved secret store. Required values:
   Splunk HEC URL/token, Manager API token, and proxy shared secret.

4. Start SC4S and Manager from the SC4S directory:

   ```bash
   cd /opt/sc4s
   sudo docker compose -f compose.yaml up -d
   ```

5. Verify container and API health:

   ```bash
   cd /opt/sc4s
   sudo docker compose -f compose.yaml ps
   curl -fsS http://127.0.0.1:8090/health
   curl -fsS http://127.0.0.1:8080/health
   ```

The release Compose template does not mount `/var/run/docker.sock`. If no narrow
control socket is supplied at `/run/sc4s-manager/control.sock`, restart, reload,
Docker status, and syslog-ng counter actions are unavailable by design. Do not
grant Docker socket access just to make those controls green.

## Standalone binary quick start

1. Download `sc4s-manager-<version>-linux-x86_64` and `SHA256SUMS` from the
   GitHub release page.
2. Verify and install:

   ```bash
   sha256sum -c SHA256SUMS --ignore-missing
   chmod 0755 sc4s-manager-<version>-linux-x86_64
   sudo install -m 0755 sc4s-manager-<version>-linux-x86_64 /usr/local/bin/sc4s-manager
   ```

3. Create writable roots and provide secrets via environment or a service manager:

   ```bash
   sudo mkdir -p /opt/sc4s/local /opt/sc4s/tls /opt/sc4s-manager
   sudo chown -R sc4s-manager:sc4s-manager /opt/sc4s /opt/sc4s-manager
   export SC4S_ROOT=/opt/sc4s
   export SC4S_MANAGER_ROOT=/opt/sc4s-manager
   export SC4S_MANAGER_API_TOKEN='<from secret store>'
   export SC4S_MANAGER_PROXY_SECRET='<from secret store>'
   sc4s-manager
   ```

On first start the binary seeds its bundled frontend assets and built-in packs to
`SC4S_MANAGER_ROOT` only if they are absent. It does not overwrite existing
operator state, imports, backups, or audit logs.

## Dry Run

Run from the repository root:

```bash
deploy/install/install.sh --dry-run
```

The script must only print the plan. It must not create users, write system
paths, pull images, enable units, or restart services.

## Frontend Build

The dry-run installer is non-mutating. It checks whether `frontend/package.json`
exists and reports whether `frontend/dist/index.html` is already present, but it
must not run `npm`, create `node_modules/`, or write `frontend/dist/`.

Build the optional static frontend as an explicit packaging step before creating
a release artifact:

```bash
scripts/build_frontend.sh
```

That build script runs dependency installation (`npm ci` when a lockfile is
present, otherwise `npm install`) and `npm run build`. Production packaging
should include `frontend/dist/index.html` and `frontend/dist/assets/*` when the
static frontend is part of the release.

The manager service serves `frontend/dist/index.html` for `/`, `/index.html`, and
unknown non-API GET routes when the file exists. `/assets/*` is served from
`frontend/dist/assets/*` with static cache headers. Unknown `/api/*` routes
return JSON 404 and never fall through to the SPA. If the built frontend is
absent, `/` and `/index.html` use the inline fallback page.

## Install Steps

1. Create the `sc4s-manager` service account and group.
2. Create `/opt/sc4s`, `/opt/sc4s-manager`, `/opt/sc4s-manager`, and `/etc/sc4s-manager`
   with least-privilege ownership.
3. Install application files under `/opt/sc4s-manager`.
4. Store environment files under `/etc/sc4s-manager/` from the approved secret
   source. Use placeholders in version-controlled examples only.
5. Install `deploy/systemd/sc4s-manager-control.socket`,
   `deploy/systemd/sc4s-manager-control.service`, and
   `deploy/systemd/sc4s-manager.service` to `/etc/systemd/system/`.
6. Run syntax checks and unit tests from the installed release.
7. Enable and start the control socket, control daemon, and manager.
8. Verify `/health`, `/api/health`, config validation, version drift, and
   secret redaction smoke tests.

## Evidence

Record host, package version, SC4S image digest, unit status, health responses,
validation output, and redaction checks in the deployment ticket. Redact all
credential values.
