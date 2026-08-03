# ADR 0003: Vendor an immutable offline Library snapshot

Status: Accepted

## Decision

SC4S Manager normal operation uses a repository-committed embedded Library snapshot, not SecHub Resources URLs, remote catalogue polling, remote manifests, entry records, or a cross-repository import contract. The initial snapshot is sourced read-only from `s6securitylabs/sechub-resources` Forgejo `origin/main` revision `839c21b2e8d2739b84eaf2075cad8a7d9ee0710f`.

The snapshot carries provenance and is treated as immutable release content. It remains advisory source material: local staging, validation, operator approval, narrow apply, post-check, and rollback evidence still decide Manager state. Embedded Splunk knowledge is reference material only; it does not authorize arbitrary application installation.

## Consequences

- Direct offline installs discover and review the full embedded catalogue without outbound network access.
- Snapshot refresh is an explicit maintenance/release change with a new pinned revision and validation, not a runtime operation.
- Previous remote `/api/library` source/sync/download semantics and `SC4S_LIBRARY_SOURCE_URL` configuration are retired. No compatibility alias is retained for normal operation.
- Existing remote cache files can remain as forensic state but are not runtime inputs.

## Supersedes

This supersedes the remote-publication dependency in ADR 0002 where it concerns Manager retrieval. The product TA versus Manager-importable SC4S content boundary remains in force.
