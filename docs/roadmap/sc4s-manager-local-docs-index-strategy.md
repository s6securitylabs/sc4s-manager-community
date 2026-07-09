# SC4S Manager local docs and upstream index strategy

## Scope and goals

SC4S Manager needs a local docs index that helps an operator find source-specific SC4S guidance without treating docs, tests, examples, GitHub issues, or snippets as release-ready packs. The index supports search, triage, and provenance; it does not auto-promote any source-corpus material into a curated pack.

Goals:

- make upstream SC4S documentation discoverable beside SC4S Manager packs;
- separate `sc4s-inbuilt`, `sc4s-inbuilt-lite`, `sechub-resource`, and `community-extra` records;
- preserve whether material is official, curated, or candidate;
- expose documentation, test fixture, and example references as evidence context, not as deployment approval.

## Upstream sources and pinning

The upstream SC4S source corpus should be fetched from explicit pinned inputs:

- `docs/sources/vendor` for vendor/product documentation pages;
- `package/etc/conf.d/conflib` for inbuilt parser and source configuration material;
- `package/lite/etc/addons` for SC4S Lite/add-on coverage;
- issue, PR, discussion, and example URLs only as candidate provenance.

Every refresh record must include `requested_ref` and `resolved_commit` so catalogue records can explain which upstream SC4S state they were derived from.

## Generated local indexes

Generated material should live under predictable generated paths, with source manifests and hashes kept separate from hand-curated packs:

- `catalogue/generated/upstream` for upstream parser/source inventory;
- `catalogue/generated/docs-index` for searchable documentation snippets and page metadata;
- optional FTS source files or SQLite FTS5 databases for local search acceleration.

Generated index output is rebuildable and should not be used as the only assertion source for curated pack behavior.

## Metadata, facets, and provenance

Each index item should carry operator-facing facets:

- source class: `sc4s-inbuilt`, `sc4s-inbuilt-lite`, `sechub-resource`, or `community-extra`;
- status: official, curated, or candidate;
- input kind: documentation, test fixture, example, issue, PR, or discussion;
- upstream path or URL;
- source ref fields: `requested_ref`, `resolved_commit`, and collection timestamp.

Community issue/PR snippets remain unvalidated candidate material and must carry warnings that they do not auto-promote into packs or imply local deployment approval.

## Update cadence and refresh workflow

Refresh the upstream docs index on an intentional cadence such as release preparation, dependency/source-corpus updates, or maintainer request. The workflow should:

1. fetch the requested upstream ref;
2. resolve and record the concrete commit;
3. regenerate docs and parser indexes;
4. run catalogue/index tests;
5. review any new `community-extra` candidates before deciding whether to curate them.

## Storage format and generated paths

The generated storage format should be deterministic JSON or JSONL plus optional SQLite FTS5 for local search. Store source records under `catalogue/generated/upstream` and search/index records under `catalogue/generated/docs-index`. Keep pack manifests, generated indexes, and acceptance evidence separate so historical proof is not rewritten during routine index refreshes.

## How docs, tests, and examples relate to catalogue entries

Documentation pages, examples, and upstream tests can explain a parser path, source family, or vendor/product expectation. They are not automatically a curated pack. A catalogue entry can reference them as context, but promotion requires file-backed artifacts, fixture validation, parser/runtime checks, and, for production-grade claims, Splunk readback evidence.

Community issue/PR snippets remain unvalidated until they are converted into reviewable `.conf`, `.csv`, fixture, and documentation files and pass the Manager validation path. Do not auto-promote them from `community-extra` into `sechub-resource`.

## Acceptance tests to add

Acceptance tests should verify:

- required upstream sources and pinned ref metadata are present;
- generated paths are deterministic and rebuildable;
- provenance fields distinguish official, curated, and candidate entries;
- documentation, test fixture, and example records remain advisory;
- SQLite FTS5 search, when enabled, returns source records without changing trust or quality status;
- `community-extra` records cannot become curated packs without explicit review and validation evidence.
