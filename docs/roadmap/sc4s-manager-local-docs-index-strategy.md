# SC4S Manager local docs and upstream index strategy

## Scope and goals
SC4S Manager needs a catalogue and supporting local docs index that clearly separates official upstream coverage from SecHub Resources curated content and community candidates. The goal is to let the API/UI answer coverage questions without blurring provenance: official upstream material stays official, curated SC4S Library packs use the canonical `sechub-resources-pack` provenance, and community issue/PR snippets remain candidate records until validation proves otherwise.

## Upstream sources and pinning
Pinned upstream collection starts from tagged SC4S refs and stores both requested_ref and resolved_commit for reproducibility. The primary sources are upstream parser/config trees under package/etc/conf.d/conflib, Lite add-ons under package/lite/etc/addons, and upstream documentation under docs/sources/vendor when mirrored locally. Official sources populate sc4s-inbuilt and sc4s-inbuilt-lite namespaces only.

Community issue/PR snippets remain unvalidated inputs and do not auto-promote into official or curated records. They must stay marked candidate until tests, parser validation, and representative Splunk evidence say otherwise.

## Generated local indexes
Generate two local artifacts:
- catalogue/generated/upstream for the structured official catalogue extracted from pinned upstream refs.
- catalogue/generated/docs-index for documentation, examples, and source-note indexing used by search and review workflows.

The docs index should support SQLite FTS5 so local lookups can join catalogue records with mirrored documentation, issue notes, and parser examples quickly.

## Metadata, facets, and provenance
Every entry should keep provenance first-class: origin namespace, requested_ref, resolved_commit, source URLs where applicable, artifact type, vendor, product, and relationship to upstream. Facets must preserve sc4s-inbuilt, sc4s-inbuilt-lite, sechub-resources-pack, and community-extra as separate populations.

Status language should remain explicit:
- official for upstream shipped SC4S content
- curated for SC4S Manager maintained packs and bundles
- candidate for community-derived material awaiting proof

## Update cadence and refresh workflow
Refresh upstream and local docs indexes on deliberate pinned-version updates, not opportunistically. A refresh workflow should:
1. pin or change requested_ref
2. resolve and record resolved_commit
3. regenerate catalogue/generated/upstream and catalogue/generated/docs-index
4. review diffs for provenance drift, duplication, and accidental promotion
5. rerun API/UI tests before commit

## Storage format and generated paths
Structured outputs live as JSON under catalogue/generated/upstream and catalogue/generated/docs-index. Generated records should be deterministic and safe to diff. Paths for mirrored docs, test fixture metadata, and example content should stay relative to the repository so downstream tooling can join them without guessing host-specific locations.

## How docs, tests, and examples relate to catalogue entries
Documentation, test fixture, and example artifacts should enrich catalogue entries without changing their trust level on their own. Documentation can explain vendor/product behavior, a test fixture can prove parser expectations, and an example can illustrate config shape; none of them should silently upgrade a community candidate into curated or validated status. Promotion requires explicit review plus validation evidence.

## Acceptance tests to add
Acceptance coverage should verify:
- upstream generators preserve requested_ref and resolved_commit
- docs-index generation writes expected files under catalogue/generated/docs-index
- facets preserve separation among sc4s-inbuilt, sc4s-inbuilt-lite, sechub-resources-pack, and community-extra
- official, curated, and candidate states render distinctly in API/UI output
- docs, test fixture, and example records remain linked by provenance without mutating validation state
- community issue/PR snippets remain unvalidated and do not auto-promote
