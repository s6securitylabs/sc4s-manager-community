# SC4S Manager community catalogue ingestion Kanban plan

## Goal
Populate SC4S Manager with a searchable, filterable catalogue that separates official SC4S built-in/Lite coverage, S6 curated packs, and community-sourced parser/config candidates from GitHub issues, PRs, discussions, docs, tests, and examples.

## Operating constraints
- Product name is SC4S Manager.
- `/opt/sc4s-manager` is service-owned; workers may need sudo for writes, and test artefacts must stay out of the repo unless intentionally generated source/evidence.
- Dev test bootstrap uses `/tmp/sc4s-manager-test-venv` and `COVERAGE_FILE=/tmp/sc4s-manager.coverage`.
- Community issue/PR content is not production-ready by default. Preserve provenance, URL attribution, source status, and validation state.
- Do not promote community candidates to curated/validated unless static checks and representative Splunk ingestion evidence exist.
- Tests must precede implementation for changed behavior.

## Target capability
1. Official catalogue remains populated from pinned upstream SC4S refs/tags.
2. Community candidates are ingested into a separate `community-extra` namespace.
3. Catalogue entries expose provenance, candidate status, validation state, source URLs, and confidence/trust level.
4. UI allows filtering by origin, vendor, product, quality/trust, artifact type, capability, source status, and validated-vs-candidate state.
5. Docs explain how candidates become curated SecHub Resources SC4S packs.
6. Release gates reject unvalidated community snippets being represented as validated/production-ready.

## Candidate lifecycle reference
- Detailed lifecycle and warning-state rules: `docs/roadmap/community-candidate-lifecycle.md`

## Dependency: local docs index
- Design and acceptance baseline: `docs/roadmap/sc4s-manager-local-docs-index-strategy.md`
- Community catalogue ingestion must reuse the local docs index metadata/facets model so official docs, curated extras, and candidate snippets stay separate in search.

## Acceptance criteria
- Backend unit tests prove parsing/normalization of issue/PR candidate records and separation from official/validated packs.
- API contract tests prove facets and candidate provenance are returned without breaking existing catalogue clients.
- Frontend tests/typecheck/build pass with modern filters for community/candidate fields.
- Full backend suite passes with coverage gate.
- Live manager API shows populated official catalogue plus any seeded community candidate fixtures with correct `community-extra` facets.
- No secrets or credentials are written into generated catalogue files or evidence.
