# Upgrade Runbook

## Scope

This runbook upgrades the **Manager container only** in the supported `/opt/sc4s` Docker Compose deployment. It does not upgrade SC4S, change HEC settings, or make unavailable control-socket functions available. Review SC4S image changes separately.

`deploy/upgrade/upgrade.sh --dry-run` checks archive shape and prints a plan only. It rejects `--execute` and does not perform this upgrade. Do not present planner output as lifecycle evidence.

## Preconditions and abort criteria

Before changing anything, have all of the following:

- A verified target Manager image tag/digest and the exact current image reference.
- A rollback reference that has been pulled or is known available in the approved registry.
- A current backup of `/opt/sc4s/manager`, `/opt/sc4s/local`, `/opt/sc4s/env/` (including the `env_file` symlink), `/opt/sc4s/manager.env`, `/opt/sc4s/.env`, and `/opt/sc4s/compose.yaml`.
- A maintenance window if the proxy or Manager UI is operator-critical.
- Current Manager and SC4S health/readback evidence.

Abort and roll back immediately if Compose rendering fails, the target image cannot be pulled/verified, either container restarts repeatedly, Manager `/health` is not HTTP 200, `sc4s.ok` is false, expected Manager state is missing, or secrets appear in output. Do not upgrade while an SC4S configuration incident is unresolved.

## 1. Capture baseline and back up mutable state

```bash
set -euo pipefail
cd /opt/sc4s
UTC=$(date -u +%Y%m%dT%H%M%SZ)
sudo install -d -m 0700 /opt/sc4s/manager/backups/upgrade-${UTC}
sudo cp -a env env_file manager.env .env compose.yaml local \
  /opt/sc4s/manager/backups/upgrade-${UTC}/
sudo docker compose -f compose.yaml ps
sudo docker compose -f compose.yaml images
curl -fsS http://127.0.0.1:8090/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/health
```

Expected: the backup directory contains the listed mutable inputs, both services are running, and Manager health is JSON `status: ok` with `sc4s.ok: true`. Record the exact Manager image reference shown by `docker compose images`; it is the rollback target.

## 2. Pin, pull, and recreate only Manager

Edit `SC4S_MANAGER_VERSION` in `/opt/sc4s/.env` to the approved target tag or digest. Do not change `SC4S_IMAGE` in this procedure.

```bash
cd /opt/sc4s
sudo editor .env
sudo docker compose -f compose.yaml config -q
sudo docker compose -f compose.yaml pull manager
sudo docker compose -f compose.yaml up -d --no-deps manager
sudo docker compose -f compose.yaml ps
sudo docker compose -f compose.yaml images
```

Expected: Compose is silent for `config -q`; only `manager` is recreated; `sc4s` remains running with the original image. If Docker selects an unintended image, stop here and restore the saved `.env` before proceeding.

## 3. Verify the upgrade

```bash
curl -fsS http://127.0.0.1:8090/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/health
cd /opt/sc4s && sudo docker compose -f compose.yaml logs --tail=100 manager sc4s
```

Expected: Manager returns HTTP 200 and `status: ok`; the nested SC4S check remains `ok: true`; logs have no new repeating errors; `docker compose images` shows the approved Manager reference. Authenticate through the normal proxy/manual path and confirm a non-destructive inventory/readback works. In this Compose bundle, control-socket runtime actions remain unavailable by design both before and after upgrade.

Finally, verify that `/opt/sc4s/manager` state is still present and run the approved downstream marker/Splunk readback if the maintenance window includes ingestion assurance. Saved Manager state, Manager liveness, SC4S health, and Splunk indexing are separate checks.

## Recovery

If any post-check fails, use [Rollback Runbook](rollback.md) immediately. Preserve the failed container logs and do not retry repeatedly against a modified `.env`; each retry can obscure the known-good reference.
