# SC4S Manager security acceptance

## Scope

This acceptance note records the security boundaries expected for the public community release package. It is not live production proof and must not contain real secrets, tokens, credentials, customer identifiers, proxy shared secrets, OAuth headers, or HEC values.

## Required boundaries

- Manager mutation paths require an intended trusted proxy header, local API token, or manual login flow.
- Health/read-only static frontend routes may be reachable so the application can render, but API mutation routes must fail closed without authorization.
- Runtime control is limited to fixed SC4S Manager actions and does not expose arbitrary shell, Docker socket, compose paths, container names, or host paths.
- Archive/import operations must enforce path containment and reject traversal or unsafe member paths.
- Evidence, logs, JSON reports, screenshots, and release artifacts must redact secret-like settings while preserving typed metadata such as booleans and arrays.

## Template values

Example configuration files use placeholders only, such as `<set-a-long-random-value>` or `<provide-via-secret-store>`. They must never ship live credential values.

## Release checklist

- [ ] Compose and systemd templates contain no literal secret assignments.
- [ ] Package/install dry-run evidence uses redacted values.
- [ ] Public/community material states that local validation and operator approval are required before apply.
- [ ] Any live route proof distinguishes public route protection from authenticated UI/API behavior.
