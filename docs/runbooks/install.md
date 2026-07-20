# Install Runbook

## Scope and support boundary

This is the supported **Docker Compose** procedure for a host that runs SC4S in `/opt/sc4s`. It manages configuration and serves the Manager UI/API without giving that web container Docker-socket access.

At this revision, the Compose bundle does **not** provide a control daemon or a mounted host control socket. Do not expect Manager-triggered validate, reload, restart, Docker status/logs, metrics, or listener inspection to work in a Compose-only deployment. This is intentional; use the explicit host-side Compose commands in this runbook for lifecycle operations.

The supplied systemd control service/socket pair is an **optional host-control deployment**. It is not part of the Compose bundle and does not make controls available inside the Compose-only Manager container. In this mode, `sc4s-manager-control.socket` owns `/run/sc4s-manager/control.sock` (user/group `sc4s-manager`, mode `0660`) and starts the root-owned daemon with its listener on fd 3. The daemon consumes that listener without unlinking or rebinding it. Enable the socket unit, not the service unit; systemd starts the service on demand or when `sc4s-manager.service` requires it. Do not work around access failures by deleting socket permissions, making the socket world-writable, or mounting `/var/run/docker.sock`.

The install and upgrade scripts are planners only. `--execute`, `--apply`, and `--rollback` are rejected; they do not install, upgrade, or roll back a host.

## Prerequisites and stop criteria

Before making changes, record the intended Manager image tag/digest, the SC4S image tag/digest, the host, and a rollback image reference in the change record.

You need:

- Linux with Docker Engine and Docker Compose v2 approved for the environment.
- A pinned SC4S image. The current template uses `ghcr.io/splunk/splunk-connect-for-syslog/container3:3.43.0`; changing it is a separate SC4S compatibility review.
- A fixed Manager image using a release tag or digest. **Do not start a production-like host with `SC4S_MANAGER_IMAGE` ending in `:latest`.**
- HEC URL/token and Manager authentication material held in an approved secret store.
- Firewall/DNS approval for the syslog listeners and, if required, Manager's port 8090.
- Enough persistent disk for `/opt/sc4s/archive`, the `splunk-sc4s-var` volume, and `/opt/sc4s/manager` state/backups.

Stop before `docker compose up` if `docker compose version` fails, either required image reference is unpinned, a required secret is blank or still an example value, `docker compose config -q` fails, or the host cannot give UID/GID `10001` write access to the Manager-owned bind mounts.

## 1. Prepare the host layout and permissions

The Manager image runs as UID/GID `10001`. Root ownership alone is not sufficient: the container must be able to write `/opt/sc4s/local`, `/opt/sc4s/manager`, and `/opt/sc4s/env/env_file` when an operator saves configuration. `/opt/sc4s/env_file` remains the conventional SC4S Compose path, but is a symlink to the directory-mounted target so Manager can atomically replace the target without replacing a single-file bind mount or the symlink itself. Keep group ownership with GID `10001` and do not make secret files world-readable.

```bash
sudo install -d -o root -g 10001 -m 0770 \
  /opt/sc4s /opt/sc4s/env /opt/sc4s/local /opt/sc4s/archive /opt/sc4s/tls /opt/sc4s/manager
sudo docker volume create splunk-sc4s-var
sudo install -m 0644 deploy/compose/compose.yaml /opt/sc4s/compose.yaml
sudo install -m 0644 deploy/compose/.env.example /opt/sc4s/.env
sudo install -m 0640 -o root -g 10001 deploy/compose/env_file.example /opt/sc4s/env/env_file
sudo ln -sfn env/env_file /opt/sc4s/env_file
sudo install -m 0640 -o root -g 10001 deploy/compose/manager.env.example /opt/sc4s/manager.env
sudo chgrp 10001 /opt/sc4s/local /opt/sc4s/manager
sudo chmod 0770 /opt/sc4s/local /opt/sc4s/manager
sudo namei -l /opt/sc4s/env/env_file /opt/sc4s/env_file /opt/sc4s/local /opt/sc4s/manager
```

Expected: every parent directory is traversable; `env/env_file`, `local`, and `manager` are group-readable/writable by GID `10001`; and `env_file` resolves to `env/env_file`. If a local policy requires named users/groups instead of numeric GIDs, use an equivalent ACL for UID/GID `10001`; verify it before start. Do not recursively change ownership of unrelated SC4S archive or TLS data.

### SELinux hosts

The Compose template uses `:z` bind-label options for the mounted paths. On an enforcing SELinux host, retain those options and check labels before/after first start:

```bash
getenforce
ls -Zd /opt/sc4s/{env,local,archive,tls,manager} /opt/sc4s/env/env_file
```

Expected: `getenforce` is `Enforcing` or `Permissive`; after Docker applies the `:z` mounts, the paths have a container-shareable label. If the Manager log contains `Permission denied` while Unix permissions are correct, stop the stack and have the platform team correct the SELinux label/policy. Do not disable SELinux globally or remove labels as a workaround. Network or special filesystems may not support relabeling; use a supported local filesystem or a reviewed SELinux policy.

## 2. Configure images and secrets

Edit only the copies in `/opt/sc4s`; do not commit them.

```bash
sudo editor /opt/sc4s/.env /opt/sc4s/env/env_file /opt/sc4s/manager.env
sudo stat -c '%a %U:%G %n' /opt/sc4s/env/env_file /opt/sc4s/manager.env
```

Set `SC4S_MANAGER_IMAGE` to the complete approved image reference, for example `ghcr.io/s6securitylabs/sc4s-manager-community:1.0.3` or `ghcr.io/s6securitylabs/sc4s-manager-community@sha256:<digest>`, and retain the previous value for rollback. Supply the real Splunk HEC endpoint/token in `env/env_file` (which SC4S reads via the `env_file` symlink). Generate `SC4S_MANAGER_PROXY_SECRET` and `SC4S_MANAGER_API_TOKEN` from the approved secret store; do not leave `change-me-with-random-value` in place.

Expected: both secret files report mode `640` (or stricter) and group `10001`/the approved Manager group. After Manager atomically replaces `env/env_file`, its owner may become UID `10001`; its restrictive mode and GID `10001` remain the access boundary. Treat `.env` as deployment configuration too: it selects published ports and image references.

## Authentication and reverse proxy

Choose one supported access pattern before exposing the UI. This product does not require a particular identity provider.

1. **Trusted reverse proxy (recommended).** Bind or firewall port 8090 so only the proxy or administration network reaches it. The proxy authenticates the user, removes any client-supplied copies of these headers, and injects:
   - `X-SC4S-Manager-Proxy`: exactly the secret in `SC4S_MANAGER_PROXY_SECRET`.
   - `X-Forwarded-User` or `X-Authentik-Username`: the audited operator identity.
   - If `SC4S_MANAGER_ADMIN_GROUPS` is set, `X-Authentik-Groups`: a comma/semicolon/pipe-separated group list with an exact allowed group.

   `X-Authentik-Groups` is the currently implemented group-header name, even if the proxy/IdP has a different native header. Map the authenticated group claim to this header at the proxy. Never pass a client-provided identity or proxy-secret header upstream.

2. **Temporary isolated/manual access.** Set a high-entropy `SC4S_MANAGER_MANUAL_LOGIN_TOKEN` in `/opt/sc4s/manager.env`, expose the port only on an isolated administration network, and rotate/remove it after use. This grants Manager access; it is not a substitute for SSO, authorization policy, audit identity, TLS, or network controls. Do not put manual tokens in tickets, shell history, bookmarks, screenshots, or URLs.

`SC4S_MANAGER_API_TOKEN` is accepted only from loopback clients via `X-SC4S-Manager-Token`; it is for local automation, not browser login. With neither proxy authorization nor a manual-login token, all routes except `/health` and `/api/health` correctly return authorization failure.

## 3. Validate and start

```bash
cd /opt/sc4s
sudo docker compose -f compose.yaml config -q
sudo docker compose -f compose.yaml pull
sudo docker compose -f compose.yaml up -d
sudo docker compose -f compose.yaml ps
```

Expected: `config -q` exits 0 without output; `pull` retrieves the pinned references; `ps` shows `sc4s` and `manager` as running (Manager becomes healthy after its healthcheck interval). Abort if either service repeatedly restarts, a different image is selected, or Compose reports a bind-mount/permission error.

## 4. Human verification after install

Run these from the host. They deliberately separate Manager liveness from SC4S readiness and from downstream Splunk proof.

```bash
cd /opt/sc4s
sudo docker compose -f compose.yaml ps
curl -fsS http://127.0.0.1:8090/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/health
sudo docker compose -f compose.yaml logs --tail=100 manager sc4s
sudo docker compose -f compose.yaml images
```

Expected outcomes:

- `manager` and `sc4s` are `running`; Manager is `healthy` once its healthcheck has passed.
- Manager `/health` returns HTTP 200 JSON containing `"status": "ok"`. Its `sc4s.ok` field must be `true` for SC4S HTTP health; otherwise Manager is alive but SC4S is not ready.
- SC4S `/health` returns HTTP 200. If its status port was changed, use the port configured in `.env` instead of `8080`.
- Logs contain no repeating permission, configuration, HEC authentication, or startup failure.
- `images` shows the intended pinned Manager and SC4S references.

Then use the authorized proxy/manual path to open the UI and perform a non-destructive readback. A proxy may require browser SSO; use its normal login flow rather than sending proxy secret headers from a browser.

For a local automation probe only, replace the placeholder without echoing the token:

```bash
read -rsp 'Manager API token: ' SC4S_MANAGER_API_TOKEN; echo
curl -fsS -H "X-SC4S-Manager-Token: ${SC4S_MANAGER_API_TOKEN}" \
  http://127.0.0.1:8090/api/stats | python3 -m json.tool
unset SC4S_MANAGER_API_TOKEN
```

Expected: the response includes Manager health plus control/runtime fields. In Compose-only mode, control-related fields may be unavailable/`ok: false`; that is expected and must not be reported as live SC4S control. Prove event delivery separately with an approved marker event and Splunk search/readback for the configured destination.

## Optional: enable the systemd host control boundary

Use this only for a reviewed host-systemd Manager deployment where the Manager process runs as `sc4s-manager` and can access the socket group. It is **not** a step for the Compose procedure above. Confirm `/opt/sc4s/compose.yaml` (or the approved fixed `/opt/sc4s/docker-compose.yml`) and the fixed `SC4S` container identity are the intended runtime before enabling the root daemon.

```bash
sudo install -m 0644 deploy/systemd/sc4s-manager-control.socket /etc/systemd/system/sc4s-manager-control.socket
sudo install -m 0644 deploy/systemd/sc4s-manager-control.service /etc/systemd/system/sc4s-manager-control.service
sudo systemctl daemon-reload
sudo systemctl enable --now sc4s-manager-control.socket
sudo systemctl start sc4s-manager-control.service
sudo systemctl status --no-pager sc4s-manager-control.socket sc4s-manager-control.service
sudo stat -c '%a %U:%G %F %n' /run/sc4s-manager/control.sock
```

Expected: both units are active, the socket reports `660 sc4s-manager:sc4s-manager socket`, and the control-service journal contains `systemd socket activation`, not `Address already in use`. Do not enable the service separately: it has no `[Install]` section because the socket unit owns lifecycle activation. To exercise the protocol without Docker-side mutation, send an unsupported action and expect a controlled rejection:

```bash
python3 - <<'PY'
import json, socket
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.connect('/run/sc4s-manager/control.sock')
    client.sendall(b'{"action":"not-allowed"}\n')
    print(json.loads(client.recv(65536)))
PY
sudo journalctl -u sc4s-manager-control.service -b --no-pager
```

Expected: the response is `{"ok": false, ...}` and the journal still reports systemd activation. An accepted status/reload/restart request remains constrained to the fixed allowlist and fixed SC4S identity; it is not arbitrary host control.

## Troubleshooting and safe recovery

| Symptom | Check | Safe recovery / abort point |
|---|---|---|
| Manager exits with `Permission denied` or cannot save config | `sudo docker compose -f compose.yaml logs --tail=100 manager`; `namei -l` and `ls -Zd` on the affected mount | Stop (`docker compose down`), correct only the GID `10001`/ACL and SELinux label, then restart. Do not run the container as root or make files world-writable. |
| Manager is healthy but `sc4s.ok` is false | `curl -v http://127.0.0.1:8080/health`; `docker compose logs --tail=200 sc4s` | Repair SC4S configuration/HEC connectivity before applying Manager changes. A Manager HTTP 200 alone is not readiness. |
| `docker compose config -q` fails | Read the reported variable/YAML line | Restore the last known-good `.env`, `env_file`, or `manager.env`; do not start a partially rendered stack. |
| UI/API is 401/403 | Confirm the proxy strips/injects headers; confirm proxy secret and exact group mapping; or confirm isolated manual-token setup | Do not weaken authorization or send shared secrets from client browsers. Fix proxy configuration or keep the service private. |
| Runtime controls say socket missing/refused | `docker compose exec manager sh -c 'ls -l /run/sc4s-manager || true'` | Expected for this Compose bundle. Use host-side `docker compose` lifecycle commands. Do not add a Docker-socket mount. |
| `sc4s-manager-control.service` logs `Address already in use` | `journalctl -u sc4s-manager-control.socket -u sc4s-manager-control.service -b --no-pager`; `systemctl cat sc4s-manager-control.socket sc4s-manager-control.service` | The installed units or daemon are stale. Restore the matching packaged pair, run `daemon-reload`, restart the socket then the service, and confirm the journal says `systemd socket activation`. Do not delete the socket or change it to world-writable. |

## Evidence to retain

Record host, UTC time, Manager and SC4S image digests, `docker compose ps`, redacted `/health` output, SC4S health result, authorization method, and downstream marker/Splunk proof in the deployment ticket. Never include HEC tokens, API tokens, proxy secrets, manual-login tokens, or identity-provider cookies.
