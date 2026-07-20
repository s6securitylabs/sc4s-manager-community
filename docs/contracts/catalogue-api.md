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

## `GET /api/library/*` — SecHub Resources import/apply contract

These endpoints are Manager-only. They expose remote SecHub Resources content separately from local curated packs and never imply that a downloaded bundle is already active. The former marketplace-era remote-library endpoints were removed in the 2026-06-11 taxonomy hard migration; clients must use the Library endpoints below.

Protected routes:

- `GET /api/library/sources` — source registry, cache metadata, primary URL
- `POST /api/library/sync` — refresh catalogue + downloads manifest cache for a source
- `GET /api/library/catalogue` — remote catalogue list with `source_id`, `downloadable_only`, and `search`
- `GET /api/library/entry` — remote entry detail plus apply-eligibility summary
- `POST /api/library/download` — fetch bundle, reject redirects, verify SHA256, and cache the zip only
- `POST /api/library/import/validate` — extract the verified bundle into Manager state, split runtime-safe vs reference-only artifacts, validate any embedded `pack.json`, and create an import record
- `GET /api/library/imports` — staged import records available for review/apply
- `POST /api/library/import/apply` — revalidate the staged runtime plan, back up changed targets, apply runtime-safe files only, validate locally, reload via control path, and roll back on validation failure

V1 source behavior:

- `sechub.s6ops.com` is the canonical V1 SecHub public source for Manager catalogue sync.
- Do not point Manager at retired SecHub Resources hostnames or repository-only URLs for runtime catalogue sync.
- Private/automation paths may fetch `s6securitylabs/sechub-resources`, check out reviewed `main` or an approved release tag, and consume generated artifacts from that clean checkout.
- The Manager import/apply contract is unchanged: all remote or repository-built artifacts are untrusted until local checksum, schema, fixture, preview, runtime, and optional Splunk/readback validation passes.

Bundle contract:

- bundle `manifest.json` identifies the pack with `pack_id` and `pack_version`, plus `schema_version` and per-artifact `source_path`/`target_path`/`sha256`
- bundles that carry the full pack contract embed `pack.json`; when present it is validated with the local pack schema/fixture validators and the import record stores the result under `pack_validation`
- bundles without `pack.json` stay importable; `pack_validation` records that the embedded manifest check was skipped

State layout under `MANAGER_ROOT/state/library/`:

```text
sources.json
catalogue/<source_id>.json
downloads-manifest-<source_id>.json
entries/<source_id>/<entry_id>.json
downloads/<source_id>/<filename>
imports/<import_id>/bundle/
imports/<import_id>/reference/
imports/<import_id>/runtime-plan.json
imports/<import_id>/record.json
```

Safety contract:

- only HTTPS URLs from the configured source allowlist are permitted
- redirects are rejected for catalogue JSON, entry JSON, and bundle downloads
- bundle members must reject traversal, symlinks, duplicates, oversized payloads, and unsafe targets
- only `local/config/` and `local/context/` are runtime-safe apply targets
- `env_file.d/`, `splunk_app/`, `test-events/`, `scripts/`, and docs remain reference-only staged artifacts
- import/apply is explicit two-step operator flow: validate first, then apply
- backups are taken before overwriting existing runtime files
- failed validation, reload, or explicit negative post-check triggers rollback and an audit trail rather than partial activation; after a control action has run, Manager re-issues reload for restored files and returns separate rollback runtime evidence

Example validate response skeleton:

```json
{
  "ok": true,
  "import_id": "imp_pan_panos_20260601T000000000000Z",
  "source_id": "official",
  "entry_id": "pan_panos",
  "apply_allowed": true,
  "reference_only": false,
  "runtime_files": [
    {
      "kind": "config",
      "source_path": "local/config/app_parsers/panos.conf",
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
  "verification": {
    "zip_sha256": "...",
    "manifest_verified": true,
    "artifact_count": 4
  }
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
