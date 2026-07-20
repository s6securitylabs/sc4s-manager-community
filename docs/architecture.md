# SC4S Manager — Architecture

## Deployment and security boundary

- The Manager web/API process runs as non-root (UID/GID `10001` in the image).
- The supported Docker Compose deployment has **no** `/var/run/docker.sock` mount. Docker socket access is host-root equivalent and must not be added for convenience.
- Compose and host control are separate deployment modes. The shipped Compose stack does not include the narrow host control daemon or mount a host control socket; it does not make control daemon functionality exist inside the Docker-only deployment and must report runtime-control actions as unavailable.
- A narrow control daemon, when supported in a future host deployment, must accept only fixed SC4S actions over `/run/sc4s-manager/control.sock`: status, bounded logs, metrics, config validation, reload, restart, listeners, and warnings. It must not accept caller-selected shells, Docker commands, compose files, paths, or container names.
- The currently packaged systemd socket/service pair is not operationally supported: `control.py` binds its own Unix socket and does not use systemd socket activation. Starting both can produce `Address already in use`. Do not turn this into a Docker-socket or world-writable-socket workaround.
- All mutation routes require authorization. `/health` and `/api/health` are intentionally open liveness endpoints only.
- Secrets are redacted in API responses, diffs, audit logs, exports, and error messages. Operators must still avoid putting tokens in URLs, shell history, tickets, screenshots, or browser developer tools.
- File writes are atomic where supported; operators must retain external backups and prove post-change state.

## Authentication and trusted proxy contract

Manager does not require a named identity provider. It can sit behind any trusted reverse proxy that authenticates the request, removes client-supplied identity headers, and injects the exact headers Manager checks.

| Purpose | Header/configuration | Enforcement |
|---|---|---|
| Proxy trust | `X-SC4S-Manager-Proxy` equals `SC4S_MANAGER_PROXY_SECRET` | Required for proxy authorization. The proxy secret is shared infrastructure material, never a browser credential. |
| Audit identity | `X-Forwarded-User` or `X-Authentik-Username` | Used as the actor after proxy authorization. If absent, the peer address is recorded. |
| Admin groups (optional) | `SC4S_MANAGER_ADMIN_GROUPS` plus `X-Authentik-Groups` | Exact intersection after comma/semicolon/pipe parsing. Map another IdP's group claim to the implemented header name at the proxy. |
| Local automation | `X-SC4S-Manager-Token` equals `SC4S_MANAGER_API_TOKEN` | Accepted only from `127.0.0.1`/`::1`; not browser authentication. |
| Isolated temporary access | `SC4S_MANAGER_MANUAL_LOGIN_TOKEN` | Grants access for controlled temporary use. It is not a replacement for proxy auth, TLS, network restriction, or identity-aware audit. |

A reverse proxy must overwrite/remove all of the listed incoming headers before forwarding a verified identity. Do not accept these values directly from untrusted clients. Health endpoints remaining open is not proof that the proxy correctly protects authenticated UI/API routes.

## Apply-state model

Keep these states distinct:

1. **Desired/staged**: Manager has saved a proposed configuration or staged a Library pack.
2. **Validated**: syntax/config validation succeeded in the available validation environment.
3. **Applied**: files were written and an apply transaction records its result.
4. **Observed runtime**: SC4S process/container, listener, health, log, or counter data was actually read back.
5. **Verified downstream**: an approved event/marker was found at the intended Splunk destination.

Compose-only installations cannot honestly progress control-socket actions beyond unavailable. A Manager HTTP response or a saved file never substitutes for SC4S health or downstream readback.

## Apply workflow

For a deployment that has a working, narrow control boundary, a configuration change follows:

```
preview → validate → backup → apply → control action → post-check → rollback-ready
```

1. **Preview** — show files and values that would change.
2. **Validate** — syntax/config validation against the proposed state.
3. **Backup** — preserve current runtime files before writes.
4. **Apply** — atomically write approved configuration.
5. **Control/post-check** — execute only the required allowlisted reload/restart and read back health/listeners/counters.
6. **Rollback** — on validation, control, or post-check failure, restore the backup and restore the known-good runtime where a control action has already run.

Stop rather than claiming success if validation, control, or post-check evidence is absent. Use Splunk readback for ingestion proof.

## Library pack workflow

Packs are fetched from a configured SC4S Library source (default: [SecHub](https://sechub.s6ops.com)) and remain untrusted until local validation and explicit operator approval:

1. Fetch catalogue/entry metadata from the configured source.
2. Download a selected bundle and verify its SHA-256 against catalogue metadata.
3. Validate schema, parser artifacts, fixtures, path safety, and archive limits.
4. Stage a draft import; do not apply it automatically.
5. On explicit install/apply, write only eligible SC4S runtime files through the full apply workflow.
6. Retain reference-only artifacts for review; do not automatically apply Splunk apps, scripts, documentation, or test events.

Remote review/trust labels are advisory. A downloaded pack is not local deployment approval and a local validation result is not downstream Splunk proof.

### Library source configuration

Set `SC4S_LIBRARY_SOURCE_URL` in `manager.env` to use an approved alternative source, or `none` to start with no preconfigured source. Validate the source's catalogue, manifest, representative entry, and bundle from the real Manager client before relying on it.

### Bundle safety checks

Before staging pack content, Manager checks that ZIP members are relative/non-traversing, are not symlinks or duplicates, are within compressed/uncompressed and member-size limits, and match the advertised checksum.

## State layout

Manager state is rooted at `SC4S_MANAGER_ROOT` (Compose: `/opt/sc4s/manager`), including Library cache/imports, backups, audit records, templates, and frontend assets. This is mutable operational data: back it up before upgrade, give UID/GID `10001` appropriate access, and do not expose it as a public static directory.

## What Manager does not do

- It does not host the public pack catalogue.
- It does not let Library trust labels bypass local validation.
- It does not grant unrestricted host/Docker control to the web UI.
- It does not make control daemon functionality exist inside the Docker-only deployment.
- It does not silently treat saved configuration, HTTP liveness, or container health as Splunk indexing proof.
- It does not store secrets in generated pack exports by design; operators still must protect runtime environment files and evidence.
