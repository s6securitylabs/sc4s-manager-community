# SC4S Manager community catalogue ingestion kanban

## Goal

Populate SC4S Manager with a searchable community catalogue that clearly separates official SC4S coverage, curated S6 packs, and community/source-corpus candidates from GitHub issues, pull requests, discussions, docs, tests, and examples.

This roadmap depends on the local docs index strategy in `sc4s-manager-local-docs-index-strategy.md`. The local docs index provides the pinned upstream documentation, parser inventory, provenance, and search metadata needed before community material can be triaged safely.

## Operating constraints

- `sc4s-inbuilt` and `sc4s-inbuilt-lite` describe official upstream SC4S material.
- `sechub-resource` describes curated S6 pack material.
- `community-extra` describes candidate material only.
- A local docs index hit is evidence context, not validation proof.
- Community issues, PRs, and discussion snippets must remain candidate-only until converted into file-backed artifacts and validated.

## Kanban lanes

1. **Discover** — collect candidate URLs, vendor/product names, upstream paths, and local docs index matches.
2. **Classify** — assign source class, input kind, provenance URL/path, and candidate warnings.
3. **Curate** — convert useful material into reviewable pack files, fixtures, and source notes.
4. **Validate** — run schema, fixture, parser/runtime, and Splunk-readback gates appropriate to the claim.
5. **Promote or park** — promote only validated curated work; otherwise leave it as `community-extra` backlog.

## Acceptance

- Community catalogue records reference the local docs index when upstream documentation or examples explain the candidate.
- Search surfaces candidate status and warnings before any operator can import or stage work.
- Promotion requires explicit maintainer review and validation evidence; no automated issue or docs scrape can mark a pack curated by itself.
