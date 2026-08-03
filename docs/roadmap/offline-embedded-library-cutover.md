# Offline embedded Library cutover plan

## Scope and source

This breaking internal cutover makes the Manager's normal Library workflow wholly local. The vendored source is the immutable Forgejo object `839c21b2e8d2739b84eaf2075cad8a7d9ee0710f` from `origin/main` in `s6securitylabs/sechub-resources`; the dirty working tree is not a source. The snapshot includes all 67 `packs/*/pack.json` trees and their SC4S configuration, Splunk reference knowledge, fixtures, docs, and scripts needed for discovery, local validation, staging, apply planning, and review.

## Data ownership

`embedded_library/` is an immutable, repository-owned snapshot. `embedded_library/SNAPSHOT.json` records the upstream repository/ref/revision, pack count, and deterministic content metadata. Runtime state remains under `state/library/`: staged imports, validation records, backups, and apply evidence are local operator state and are never conflated with the embedded snapshot. Splunk content is reference-only unless an existing contract-valid Manager runtime plan explicitly identifies SC4S files; Manager is not a Splunk app installer.

## Migration stages

1. Vendor the pinned tree and generate/validate a local index from its manifests.
2. Replace runtime source, poll, refresh, HTTP, remote manifest, and remote entry logic with read-only snapshot discovery and local staging.
3. Keep the existing narrow validation/apply/backup boundary, but feed it only extracted local snapshot material.
4. Remove remote API/config/UI semantics; expose snapshot provenance and fail closed on malformed snapshot data.
5. Verify the complete snapshot, no-network access, local staging, provenance, legacy rejection, UI wording, and repository gates.

## File-level work

- Add `embedded_library/` snapshot trees and `SNAPSHOT.json`; add deterministic index/validation support in `src/sc4s_manager/library.py`.
- Update `src/sc4s_manager/app.py` routes to expose only embedded-library reads/imports and reject remote compatibility inputs/endpoints.
- Update catalogue discovery to include embedded manifests without making upstream claims into local validation proof.
- Update `frontend/src/api/library.ts`, `frontend/src/routes/Library.tsx`, dashboard/navigation wording, and tests to present an embedded offline Library.
- Update `docs/architecture.md`, contracts/runbooks as applicable, and a new ADR; remove active remote dependency statements.
- Add backend and frontend regression coverage for snapshot integrity, complete discovery, provenance, safe malformed-data failure, offline staging, and retired remote behavior.

## Acceptance criteria

- Exactly 67 source manifests are represented in the committed snapshot and discovery returns all valid packs.
- Known SC4S parser, Splunk knowledge, and fixture files are present and visible as applicable.
- Catalogue/detail/import execute with no HTTP client or network request.
- A local embedded pack can be staged and validated; malformed snapshot metadata fails closed.
- API/UI expose the pinned revision and describe the Library as embedded/local; legacy remote source, poll/sync, refresh, and configuration use is absent or rejected.
- Full backend gate plus frontend tests/build pass without weakening prior coverage.

## Rollback and migration

This is a code-and-data cutover, not an automatic deployment migration. Existing `state/library` remote caches are ignored by the new runtime and may be retained for forensic rollback only. Reverting the Manager commit restores the prior architecture; any already-created local import records/backups remain local state. Future snapshot refresh is a separate, explicit maintenance operation that changes the pinned tree and metadata through review; it is not a runtime sync feature.

## Non-goals

- No production deployment, network refresh service, polling, remote compatibility facade, Docker socket access, arbitrary command execution, or automatic Splunk TA installation.
- No claim of live SC4S-to-Splunk readback without a disposable runtime exercise.
