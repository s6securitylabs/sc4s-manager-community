# Pack Export Contract

Version: 0.1

Exports must be generated from `export_artifacts` in `pack.json`, not hard-coded path lists.

## Bundle structure

```text
<pack-id>-<pack-version>.zip
  manifest.json
  sc4s/...
  splunk/...
  test-events/...
  scripts/...
  README.md
```

## `manifest.json`

Each exported bundle includes pack id/version/schema, `created_at`, and artifacts with source path, target path, kind, sha256, rendered, contains_secrets, and required.

## Secret policy

- `contains_secrets=true` artifacts must never be exported without an explicit redaction/rendering path.
- Current bundled Commvault artifacts are static and declare `contains_secrets=false`.
- Export logs and API responses must redact token-like values.

## Installer behaviour

Install/apply is out of scope for the zip endpoint. Future install endpoints must use preview, backup, validation, apply, and post-check. No raw copy into production SC4S paths without those gates.
