# Merged Catalogue API Contract

Version: 0.1
Status: Draft

## Purpose

The merged catalogue API exposes upstream SC4S built-ins and SecHub Resources curated extras through one searchable model while preserving provenance and relationship information.

The API must help operators answer:

- Does SC4S already support this source?
- Does SC4S Manager provide a curated/enhanced version?
- What artifacts are available?
- What public Review status exists, what community rating exists, and what local validation/evidence state Manager has produced?
- How does SC4S Manager improve on upstream?

## Source classes

Allowed source classes:

- `sc4s-inbuilt` — upstream SC4S full package/container content
- `sc4s-inbuilt-lite` — upstream SC4S Lite/addon content
- `sechub-resource` — curated SecHub Resources SC4S pack
- `community-extra` — future community submission path

## Relationship values

- `upstream_only`
- `new_pack`
- `extends_upstream`
- `overrides_upstream`
- `adds_postfilters`
- `adds_reduction_rules`
- `adds_splunk_knowledge`
- `docs_only`
- `deprecated`

## Public Review status and Community rating

Public catalogue consumers should display Review status before internal trust/quality fields.

Allowed public Review status values:

- `unreviewed` — submitted, generated, imported, upstream/source-corpus, or community material that has not yet been checked by S6/maintainers.
- `reviewed` — checked by S6/maintainers for source identity, metadata, packaging, obvious safety issues, and available validation evidence.
- `deprecated` — retained for compatibility/history but not recommended for new use.

Community rating is separate 1-5 star user feedback. It is not validation, not a trust score, and must never promote Review status or bypass Manager local validation.

## Internal trust/evidence fields

The API currently preserves these internal/advisory fields for compatibility and filtering while the UI language migrates:

- `unverified`
- `community_submitted`
- `trusted_contributor_verified`
- `s6_verified`
- `field_verified`

Internal trust fields are not popularity. Likes/upvotes/ratings are feedback signals only.

## Internal quality status, score, and verification

Suggested quality states:

- `catalogued` — known to exist, no curated validation
- `draft` — pack exists but incomplete
- `curated` — reviewed pack with tests/evidence
- `validated` — passed local/runtime validation gates
- `field_validated` — proven in a real lab/customer deployment with sanitised evidence
- `deprecated` — retained for history or compatibility only

The list API also exposes a numeric internal `quality_score` from 1-5 for compatibility filtering. Do **not** present this as the Community rating:

- 1 — draft/deprecated/very low confidence
- 2 — catalogued only
- 3 — curated/reviewed
- 4 — validated with local/runtime evidence
- 5 — field validated

`is_verified` is true when the effective entry has validation-grade evidence (`quality_score >= 4`). UI copy should not expose this as broad public verification; Manager-local validation state remains separate from upstream Review status.

## Community-candidate contract

`community-extra` entries are source-corpus candidates, not curated packs. They require stricter guardrails than official upstream or curated SC4S Manager entries.

Required behavior for `community-extra` records:

- preserve provenance fields such as `provenance_url`, source-kind detail, and artifact URLs;
- expose `source_status` in list filters and responses;
- default to public `review_status=unreviewed`, `source_status=candidate`, `trust_level=community_submitted`, `quality_status=catalogued`, and `validation.state=unvalidated_source_corpus`;
- clamp or ignore stronger self-asserted claims from the source payload; a community candidate must not become `reviewed`, `validated`, `s6_verified`, or production-ready merely because an issue/PR/discussion record says so;
- surface `candidate_warnings` to the UI so warning badges and explanatory text remain explicit.

`source_status` meanings:

- `candidate` — discovered source material awaiting curation and validation

Promoted curated packs should move into `sechub-resource` and stop presenting as `source_status=candidate`. Their Review status and internal trust/quality/validation fields then come from the reviewed pack workflow.

See `docs/roadmap/community-candidate-lifecycle.md` for the full lifecycle, promotion gates, and GitHub issue/PR examples.

## `GET /api/catalogue`

Returns a searchable list of catalogue entries.

Query parameters should include:

- `q`
- `vendor`
- `product`
- `origin`
- `relationship`
- `review_status`
- `trust_level`
- `quality_status`
- `min_quality_score`
- `is_verified`
- `source_status`
- `artifact_type`
- `has_reduction`
- `has_splunk_knowledge`
- `sc4s_version`
- `limit`
- `offset`

Response shape:

```json
{
  "entries": [
    {
      "id": "cisco_asa",
      "display_name": "Cisco ASA",
      "vendor": "Cisco",
      "product": "ASA",
      "origins": ["sc4s-inbuilt", "sechub-resource"],
      "effective_origin": "sechub-resource",
      "relationship_to_upstream": "extends_upstream",
      "trust_level": "s6_verified",
      "quality_status": "curated",
      "quality_score": 3,
      "is_verified": false,
      "source_status": null,
      "capabilities": {
        "parser": true,
        "filters": true,
        "postfilters": true,
        "log_reduction": true,
        "splunk_props_transforms": true,
        "cim_mapping": true,
        "ocsf_mapping": true,
        "fixtures": true,
        "syntax_validated": true,
        "splunk_ingestion_validated": false
      },
      "summary": "Curated Cisco ASA pack with richer parsing, reduction presets, and Splunk knowledge."
    }
  ],
  "count": 1,
  "limit": 50,
  "offset": 0
}
```

## `GET /api/catalogue/{id}`

Returns detailed catalogue entry.

Detail response should include:

- summary fields from list response
- upstream metadata
- SecHub Resources metadata
- provenance detail including source kind / source URL for community candidates
- artifact inventory
- presets
- field contract
- validation evidence summary including `validation.state`
- upstream comparison
- candidate warnings when applicable
- known limitations
- feedback summary

Example skeleton:

```json
{
  "id": "cisco_asa",
  "display_name": "Cisco ASA",
  "origins": ["sc4s-inbuilt", "sechub-resource"],
  "upstream": {
    "repo": "splunk/splunk-connect-for-syslog",
    "commit": "...",
    "sc4s_version": "...",
    "paths": []
  },
  "sc4s_manager": {
    "pack_version": "...",
    "schema_version": "0.1",
    "paths": []
  },
  "source_status": null,
  "artifacts": [
    {
      "type": "parser",
      "path": "packs/cisco_asa/sc4s/app_parsers/syslog/app-syslog-cisco_asa.conf",
      "kind": "syslog_ng_parser",
      "contains_secrets": false
    },
    {
      "type": "postfilter",
      "path": "packs/cisco_asa/sc4s/postfilters/app-postfilter-cisco_asa-noise.conf",
      "kind": "syslog_ng_postfilter",
      "contains_secrets": false
    }
  ],
  "presets": [
    {
      "id": "standard",
      "label": "Standard",
      "description": "Recommended SOC default.",
      "enabled_by_default": false,
      "reduction_rules": []
    }
  ],
  "field_contract": {
    "mapping_status": "partial",
    "cim": {},
    "ocsf": {},
    "ecs": {}
  },
  "comparison_to_upstream": {
    "relationship": "extends_upstream",
    "event_family_delta": [],
    "field_extraction_delta": [],
    "splunk_knowledge_added": true,
    "reduction_added": true
  },
  "validation": {
    "last_verified_at": null,
    "trust_level": "s6_verified",
    "evidence_paths": [],
    "state": "validated_pack"
  },
  "feedback": {
    "likes": 0,
    "rating_average": null,
    "comments_url": null
  }
}
```

The SecHub Resources SC4S pack contract treats `sc4s/app_parsers`, `sc4s/filters`, `sc4s/postfilters`, `sc4s/selectors`, and `sc4s/context` as canonical file-backed artifact directories. Reduction rules must reference reviewable `sc4s/postfilters/*.conf` artifacts rather than embedded parser text.

## `GET /api/library/*` — embedded offline Library contract

These endpoints expose the committed embedded snapshot separately from local staged/applied state. The single `source_id` is `embedded`; snapshot provenance includes an immutable source revision. Normal operation has no remote source, manifest, polling, entry, URL, or cache dependency.

- `GET /api/library/sources` — embedded snapshot identity and provenance
- `GET /api/library/source-health` — local snapshot integrity check; no network request
- `GET /api/library/catalogue` — local pack list with `downloadable_only` and `search`
- `GET /api/library/entry` — local pack detail and apply-eligibility summary
- `POST /api/library/import/validate` — stage local files, split runtime versus reference roles, and create an import record
- `GET /api/library/imports` — staged import records available for review/apply
- `POST /api/library/import/apply` — revalidate the staged runtime plan, back up changed targets, apply runtime-safe files only, validate locally, reload via control path, and retain rollback evidence

There are no Library sync or download endpoints. Remote source identifiers are rejected. Snapshot provenance remains advisory source material: it does not set local validation or live state.

Package action boundary:

- Manager stages only declared `export_artifacts` whose targets are below `local/config/` or `local/context/`.
- Splunk TAs, scripts, docs, and fixtures are copied as reference material only. Product TA filenames, URLs, and titles never grant installability.
- Snapshot availability and source metadata do not set local validation or live state.

Snapshot contract:

- `embedded_library/SNAPSHOT.json` declares source repository/ref/revision/tree, the exact pack count, and a deterministic content SHA256.
- Every snapshot pack has a local `pack.json`; declared artifacts must resolve below the selected pack directory.
- Runtime target paths must be relative, traversal-free, and under `local/config/` or `local/context/`.
- Snapshot content-hash, manifest, and artifact failures fail closed before an import record is created.

State layout under `MANAGER_ROOT/state/library/`:

```text
imports/<import_id>/bundle/
imports/<import_id>/reference/
imports/<import_id>/runtime-plan.json
imports/<import_id>/record.json
```

Safety contract:

- no network source, URL allowlist, redirect, or download path participates in normal operation
- snapshot artifacts and runtime targets must reject traversal and paths outside their allowlisted local roots
- only declared runtime artifacts under `local/config/` and `local/context/` are staged for apply
- all other snapshot files remain reference-only staged artifacts and are never applied
- import/apply is explicit two-step operator flow: validate first, then apply
- backups are taken before overwriting existing runtime files
- failed validation triggers rollback and an audit trail rather than partial activation

Example validate response skeleton:

```json
{
  "ok": true,
  "import_id": "imp_pan-panos-sc4s_20260601T000000000000Z",
  "source_id": "embedded",
  "entry_id": "pan_panos",
  "apply_allowed": true,
  "reference_only": false,
  "runtime_files": [
    {
      "kind": "runtime",
      "source_path": "sc4s/app_parsers/syslog/app-pan_panos.conf",
      "target_path": "local/config/app_parsers/panos.conf",
      "sha256": "..."
    }
  ],
  "reference_files": [
    {
      "kind": "docs",
      "source_path": "README.md",
      "target_path": "README.md",
      "sha256": "..."
    }
  ],
  "snapshot": {"source_revision": "839c21b2e8d2739b84eaf2075cad8a7d9ee0710f"}
}
```

Example apply response skeleton:

```json
{
  "ok": true,
  "import_id": "imp_pan_panos_20260601T000000000000Z",
  "apply": true,
  "apply_allowed": true,
  "changed_targets": [
    "local/config/app_parsers/panos.conf",
    "local/context/vendor_product_by_source.csv"
  ],
  "validation": {"ok": true},
  "control": {"ok": true},
  "post_check": {
    "health": {"ok": true}
  },
  "rolled_back": false
}
```

## Mutability rules

- Refreshing the catalogue/cache must not mutate releaseable `packs/` content.
- Importing upstream material into a curated pack requires explicit curation workflow.
- Generated catalogue data should record upstream commit/ref and refresh timestamp.

## UI requirements

The UI should provide:

- catalogue list/search
- product-first filters by origin, product, vendor, verification checkbox, minimum 1-5 quality score, capability, and SC4S version
- pack detail page
- upstream vs SC4S Manager comparison panel
- presets/reduction panel
- artifacts/evidence panel
- feedback panel

## Non-goals for v0.1

- Auto-merging upstream parser changes into curated packs.
- Treating likes as verification.
- Detection-content store beyond pack metadata hooks.
