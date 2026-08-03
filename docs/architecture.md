# SC4S Manager — Architecture

## Security model

- The web/API process runs as a non-root user.
- The web/API process has no access to the Docker socket.
- SC4S restart and reload go through a narrow Unix socket to a local control service — the web process cannot issue arbitrary host commands.
- All mutating operations require authentication. `/health` and `/live` are
  process-liveness endpoints; `/ready` and `/api/health` report dependency readiness.
- Secrets are redacted in API responses, diffs, audit logs, exports, and error messages.
- File writes are atomic (write to temp, rename) to prevent corruption on failure.

## Authentication modes

SC4S Manager supports two authentication modes. Only one needs to be configured.

### Standalone mode (direct access)

For operators who access Manager directly from a browser without a reverse proxy, set a strong random token in `manager.env`:

```
SC4S_MANAGER_MANUAL_LOGIN_TOKEN=$(openssl rand -hex 32)
```

On first visit, Manager shows a login page. Paste the token to authenticate. A session cookie (`sc4s_manual_session`) is set for 24 hours. After that, sign out via the UI or clear the cookie to end the session.

### Proxy mode (Authentik / APISIX / nginx)

For deployments behind a trusted reverse proxy, set a shared secret that the proxy forwards on every request:

```
SC4S_MANAGER_PROXY_SECRET=<generated-secret>
```

The proxy must strip any client-supplied `X-SC4S-Manager-Proxy` header and inject
`X-SC4S-Manager-Proxy: <secret>` only on the trusted upstream hop. The web process
trusts the request only when this header exactly matches. If
`SC4S_MANAGER_ADMIN_GROUPS` is configured, one exact group from the trusted
forwarded group header must also match. Never forward an untrusted client value.

### API token (local scripts / automation)

For local automation (scripts running on the same host), set:

```
SC4S_MANAGER_API_TOKEN=<generated-token>
```

This token is accepted only from `127.0.0.1` / `::1`, via the `X-SC4S-Manager-Token` header.

## Apply workflow

Every configuration change follows this sequence:

```
preview → validate → backup → apply → post-check → rollback-ready
```

1. **Preview** — show the operator exactly what config files will change before touching anything
2. **Validate** — run SC4S config validation (syslog-ng `--syntax-only` equivalent) against the proposed state
3. **Backup** — copy current runtime files to a timestamped backup before any write
4. **Apply** — write new config through the control path
5. **Post-check** — validate config again in the live process; check counters and listener state
6. **Rollback-ready** — retain the backup and outcome. Automatic restoration on
   every failed control/post-check path is not yet a universal guarantee.

Desired configuration and live runtime state are always displayed separately. Saved config is not proof that SC4S is processing events — use Splunk readback to confirm.

## Pack import workflow

Packs are discovered from the committed embedded Library snapshot and treated as untrusted until locally verified:

1. Manager reads the pinned local snapshot index and manifest
2. Operator selects a pack and reviews its local detail and provenance
3. Manager stages its local files into an isolated draft import
4. Operator clicks Check pack — Manager validates schema, parser artifacts, fixture semantics, and path safety
5. Operator clicks Install to SC4S — Manager applies only runtime-safe SC4S config files, following the full apply workflow above
6. Reference-only files (Splunk knowledge, test events, scripts, docs) remain available for review and are never applied automatically

### Library snapshot configuration

The Library snapshot is shipped with Manager. Its immutable source revision is exposed for provenance; normal operation has no configurable remote source, refresh, or polling path. Refreshing the snapshot is a separately reviewed maintenance/release operation.

### Snapshot staging safety checks

Before any pack content is staged, Manager verifies:

- Pack paths resolve beneath the committed snapshot
- Declared runtime targets are restricted to Manager's SC4S allowlist
- Snapshot manifest/artifact metadata is structurally valid
- Snapshot metadata and every staged file are verified locally before staging

### State layout

Manager ships the snapshot and persists only local import state under `MANAGER_ROOT/state/library/`:

```
embedded_library/
  SNAPSHOT.json                         pinned source revision and integrity metadata
  packs/<pack-id>/                      SC4S, Splunk reference, fixture, docs, scripts
state/library/
  imports/<import_id>/
    bundle/                            extracted bundle (never applied directly)
    reference/                         non-runtime files for review only
    runtime-plan.json                  which files are eligible for apply
    record.json                        import record, provenance, apply status
```

## What Manager does not do

- Does not require or poll a public pack catalogue at runtime.
- Does not let Library trust labels or review status bypass local validation.
- Does not grant the web UI unrestricted host or Docker control.
- Does not store secrets in generated pack exports.
- Does not silently drop or reduce events.
- Does not apply unreviewed content without explicit operator confirmation at each step.
