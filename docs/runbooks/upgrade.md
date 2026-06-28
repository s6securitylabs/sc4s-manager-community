# Upgrade Runbook

## Scope

This runbook defines the upgrade path for SC4S Manager application packaging,
systemd units, and templates. SC4S image changes require separate version drift
review before changing the pinned `3.43.0` runtime.

## Dry Run

```bash
deploy/upgrade/upgrade.sh --artifact ./dist/sc4s-manager-VERSION.tar.gz --dry-run
```

The script validates that the artifact exists and prints the plan. It must not
change files, units, symlinks, users, containers, or services.

## Frontend Build and Static Routing

The dry-run upgrade planner is non-mutating. It validates the artifact and
reports whether the working tree already has `frontend/dist/index.html`, but it
must not run `npm`, create `node_modules/`, or write `frontend/dist/`.

Build the optional static frontend as an explicit packaging step before creating
the upgrade artifact:

```bash
scripts/build_frontend.sh
```

That build script runs dependency installation (`npm ci` with a lockfile,
otherwise `npm install`) and `npm run build`. A release that includes the static
frontend should carry `frontend/dist/index.html` and `frontend/dist/assets/*` in
the artifact.

After upgrade, the manager service serves `/assets/*` from
`frontend/dist/assets/*`, returns `frontend/dist/index.html` for unknown non-API
GET routes, and keeps unknown `/api/*` routes as JSON 404 responses. If
`frontend/dist/index.html` is absent, only `/` and `/index.html` use the inline
fallback UI.

## Upgrade Steps

1. Capture current service status, application version, SC4S image ID, and
   health responses.
2. Back up `/opt/sc4s-manager`, `/etc/sc4s-manager`, systemd unit files, and manager
   state metadata to `/opt/sc4s-manager/backups`.
3. Stage the new artifact in a temporary release directory.
4. Run shell syntax checks and unit tests from the staged release.
5. Validate config through the manager/control path.
6. Stop only the manager after recording control socket health.
7. Switch `/opt/sc4s-manager` to the staged release.
8. Reload systemd and restart the control socket, control daemon, and manager.
9. Run post-checks: `/health`, `/api/health`, config validation, version drift,
   metrics endpoint, and redaction smoke.
10. Save upgrade evidence without secrets.

## Abort Criteria

- Artifact checksum mismatch.
- Unit syntax failure.
- Test failure in staged release.
- Config validation failure.
- Post-check failure after restart.
- Any secret value appears in logs, reports, diffs, or API output.
