# SC4S Manager Release Artifact

## Purpose and limits

A release tarball is `sc4s-manager-<version>.tar.gz` with a sibling `manifest.json`. It extracts beneath the deterministic `sc4s-manager/` root. The manifest records the version, source commit, creation time, per-file SHA-256/size, frontend presence, and missing required paths.

A successful build or dry-run artifact validator proves artifact shape only. It does **not** prove Docker image availability, host permissions, Compose startup, authentication, SC4S health, upgrade, rollback, or Splunk indexing.

## Required release surface

The packaging contract includes application code, Dockerfile, Compose template/examples, dry-run planner scripts, frontend distribution, and systemd unit files. The systemd control socket/service pair is an optional host-control deployment surface: its socket unit owns the `0660` local socket and the root control service consumes it through systemd socket activation. It does not change the Compose-only support boundary or add a Docker-socket mount.

The operator-supported deployment surface is:

- `deploy/compose/compose.yaml`
- `deploy/compose/.env.example`
- `deploy/compose/env_file.example`
- `deploy/compose/manager.env.example`
- `frontend/dist/index.html` and `frontend/dist/assets/`

## Build and inspect

From the repository root:

```bash
scripts/build_frontend.sh
python3 scripts/build_release_artifact.py --version <version> --output-dir dist/
python3 -c "import json; m=json.load(open('dist/manifest.json')); print(m['missing_required_paths'])"
(cd dist && sha256sum sc4s-manager-<version>.tar.gz manifest.json > SHA256SUMS)
sha256sum -c dist/SHA256SUMS
```

Expected: the missing-path list is `[]`; checksum verification reports `OK`. Do not use `--allow-missing-frontend` for an operator release. That flag exists for controlled CI tests only.

Validate the actual generated tarball, not merely the checkout:

```bash
python3 scripts/validate_package_install.py \
  --dry-run \
  --artifact dist/sc4s-manager-<version>.tar.gz \
  --workdir /tmp/sc4s-manager-artifact-check \
  --evidence-out /tmp/sc4s-manager-artifact-dry-run.json
```

Expected: exit 0 with redacted dry-run JSON. Abort publication if required paths or frontend assets are missing, checksum verification fails, or the validator fails.

## Image and Compose handoff

A release image should be published with an immutable version tag and preferably recorded digest. Before `up -d`, an operator must set and record the approved version/digest in `/opt/sc4s/.env`; never replace the reviewed reference with `latest`.

The Compose layout is fixed:

- SC4S environment: `/opt/sc4s/env/env_file`, with `/opt/sc4s/env_file` as the Compose-compatible symlink
- Manager environment: `/opt/sc4s/manager.env`
- Local SC4S configuration: `/opt/sc4s/local`
- Archive/TLS: `/opt/sc4s/archive`, `/opt/sc4s/tls`
- Manager state/backups: `/opt/sc4s/manager`
- syslog-ng disk buffer: `splunk-sc4s-var` Docker volume

The Manager runs as UID/GID `10001`; release notes must link to the ownership and SELinux preparation in [install.md](install.md#1-prepare-the-host-layout-and-permissions). The template has no Docker-socket mount and no host control daemon. Runtime control unavailable in Compose is an honest expected state, not a release defect to bypass.

## Release evidence required before claiming installable lifecycle support

1. Build/frontend/package validation passes for the final archive.
2. Intended operators can retrieve the archive, checksum, and pinned image reference.
3. A disposable Docker host follows [install.md](install.md) literally with correct bind-mount ownership and, where relevant, SELinux labels.
4. The same host completes the Compose upgrade and rollback drill with redacted evidence.
5. The evidence distinguishes Manager health, SC4S health, runtime-control availability, and downstream Splunk readback.

See [install.md](install.md), [upgrade.md](upgrade.md), [rollback.md](rollback.md), and the [disposable-host drill](install-upgrade-rollback-drill.md).
