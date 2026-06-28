# SC4S Manager — Architecture

## Security model

- The web/API process runs as a non-root user.
- The web/API process has no access to the Docker socket.
- SC4S restart and reload go through a narrow Unix socket to a local control service — the web process cannot issue arbitrary host commands.
- All mutating operations require authentication. The `/health` endpoint is the only open route.
- Secrets are redacted in API responses, diffs, audit logs, exports, and error messages.
- File writes are atomic (write to temp, rename) to prevent corruption on failure.

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
6. **Rollback** — if post-check fails, restore from the backup automatically

Desired configuration and live runtime state are always displayed separately. Saved config is not proof that SC4S is processing events — use Splunk readback to confirm.

## Pack import workflow

Packs are downloaded from a Library source (default: [SecHub](https://sechub.s6ops.com)) and treated as untrusted until locally verified:

1. Fetch the remote catalogue JSON from the configured Library source
2. Operator selects a pack and clicks Download
3. Manager downloads the bundle ZIP and verifies its SHA256 checksum against the catalogue manifest
4. Operator clicks Check pack — Manager validates schema, parser artifacts, fixture semantics, and path safety
5. Validated pack is staged as a draft import; nothing is applied yet
6. Operator clicks Install to SC4S — Manager applies only the SC4S config files (`local/config/`, `local/context/` targets), following the full apply workflow above
7. Reference-only files (Splunk apps, test events, scripts, docs) are kept in the import staging area but never applied automatically

### Library source configuration

By default, Manager connects to `https://sechub.s6ops.com` as its Library source. To use a private or alternative source, set `SC4S_LIBRARY_SOURCE_URL` in `manager.env`:

```
# Use a private pack hub
SC4S_LIBRARY_SOURCE_URL=https://your-internal-hub.example.com

# Disable the pre-configured source entirely
SC4S_LIBRARY_SOURCE_URL=none
```

### Bundle safety checks

Before any pack content is staged, Manager verifies:

- ZIP member paths are relative, contain no traversal (`../`), and are not absolute
- No symlinks in the archive
- No duplicate member paths
- Total uncompressed size and per-member size within configured limits
- SHA256 of the downloaded ZIP matches the entry manifest

### State layout

Manager persists Library state under `MANAGER_ROOT/state/library/`:

```
state/library/
  sources.json                          source registry and last-sync metadata
  catalogue/<source_id>.json           cached remote catalogue
  entries/<source_id>/<entry_id>.json  cached remote entry detail
  downloads/<source_id>/<filename>     verified bundle ZIP cache
  imports/<import_id>/
    bundle/                            extracted bundle (never applied directly)
    reference/                         non-runtime files for review only
    runtime-plan.json                  which files are eligible for apply
    record.json                        import record, provenance, apply status
```

## What Manager does not do

- Does not host the public pack catalogue.
- Does not let Library trust labels or review status bypass local validation.
- Does not grant the web UI unrestricted host or Docker control.
- Does not store secrets in generated pack exports.
- Does not silently drop or reduce events.
- Does not apply unreviewed content without explicit operator confirmation at each step.
