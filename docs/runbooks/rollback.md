# Rollback Runbook

## Scope

This procedure reverts a failed **Manager Compose image upgrade** while preserving current SC4S configuration and ingestion. It does not automatically restore SC4S `local` configuration or HEC settings. Restore those only with incident approval and a known-good backup.

The repository installer has no rollback mode; its dry-run planner rejects lifecycle flags. Use the explicit Compose steps below or restore the host snapshot.

## Preconditions

- Freeze normal Manager changes and record the incident/change reference.
- Identify the previous Manager tag/digest from the pre-upgrade `docker compose images` output or approved change record.
- Locate the timestamped backup made by the upgrade runbook.
- Capture current evidence before changing anything:

```bash
cd /opt/sc4s
sudo docker compose -f compose.yaml ps
sudo docker compose -f compose.yaml logs --tail=200 manager sc4s
curl -fsS http://127.0.0.1:8090/health || true
curl -fsS http://127.0.0.1:8080/health || true
```

Do not continue if the rollback image reference is unknown. Escalate or restore the host snapshot instead of guessing an older `latest` image.

## 1. Revert the Manager image

Edit only `SC4S_MANAGER_VERSION` in `/opt/sc4s/.env` to the recorded known-good tag/digest. Keep `SC4S_IMAGE` unchanged unless the incident commander explicitly authorizes an SC4S rollback.

```bash
cd /opt/sc4s
sudo cp -a .env /opt/sc4s/manager/backups/pre-rollback-env-$(date -u +%Y%m%dT%H%M%SZ)
sudo editor .env
sudo docker compose -f compose.yaml config -q
sudo docker compose -f compose.yaml pull manager
sudo docker compose -f compose.yaml up -d --no-deps manager
sudo docker compose -f compose.yaml ps
sudo docker compose -f compose.yaml images
```

Expected: `config -q` is silent; only Manager is recreated; SC4S remains running; images show the recorded Manager reference. Abort and restore the saved `.env` if the rendered configuration, image reference, or bind mounts differ from the known-good deployment.

## 2. Rollback verification

```bash
curl -fsS http://127.0.0.1:8090/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/health
cd /opt/sc4s && sudo docker compose -f compose.yaml logs --tail=100 manager sc4s
sudo test -d /opt/sc4s/manager && sudo find /opt/sc4s/manager -maxdepth 2 -type d -print | sort
```

Rollback is complete only when all conditions hold:

1. `docker compose ps` shows both services running and Manager healthy.
2. Manager `/health` is HTTP 200 with `status: ok` **and** nested `sc4s.ok: true`.
3. SC4S `/health` is HTTP 200 on the configured status port.
4. Manager logs show no repeating startup/permission errors; SC4S logs show no new configuration or destination failure.
5. `docker compose images` shows the intended prior Manager reference, not `latest` or an unrecorded image.
6. Expected Manager state under `/opt/sc4s/manager` is present. Authenticate through the approved path and read back a non-destructive inventory.
7. For an ingestion-affecting incident, send/locate an approved marker and prove it in Splunk. Container health and Manager health do not prove indexing.

If any condition fails, retain logs, the failed and known-good image references, health output, and backup path; then escalate. Do not claim rollback success merely because Docker accepted `up -d`.

## Optional configuration restore

Only if the incident scope includes Manager/SC4S configuration corruption, compare the named backup before restoring. Stop and obtain approval before replacing `env/` and its `env_file` symlink, `manager.env`, `.env`, or `local/`; these files can contain current production routing and secrets. After an approved restore, run `docker compose config -q`, recreate the affected service deliberately, and repeat every verification item above.
