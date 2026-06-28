# Pack API Contract (`/api/packs`)

Version: 0.1

The pack API is served from `/api/packs` for the React/Mantine frontend and export backend. It must not leak server-local filesystem roots. The former profile-era API route was removed in the 2026-06-11 taxonomy hard migration and must return `404 Not Found` rather than acting as a compatibility alias.

## `GET /api/packs`

Response `200`:

```json
{
  "packs": ["PackSummary"],
  "count": 1
}
```

`pack_root` is intentionally excluded from the stable contract.

## `GET /api/packs/{pack_id}`

Response `200`: `PackDetail`. For v0.1, `PackDetail` is the pack summary plus full `test_event_sets` and `export_artifacts`.

Unknown pack_id response `404`:

```json
{
  "error": "pack not found",
  "code": "pack_not_found"
}
```

Generic API error shape:

```json
{
  "error": "human readable error",
  "code": "stable_machine_code_optional",
  "details": {}
}
```

## `GET /api/packs/{pack_id}/export`

Response `200`: a zip bundle (`Content-Disposition: attachment`). The bundle contains `manifest.json` (with `pack_id`, `pack_version`, `schema_version`, `created_at`, and per-artifact checksums) plus each `export_artifacts` member at its `source_path`. See `docs/contracts/pack-export-contract.md`.

## `GET|POST /api/packs/{pack_id}/validate-fixtures`

Response `200`:

```json
{
  "pack_id": "commvault_commcell",
  "results": [{"id": "...", "event_count": 3, "families": {}, "markers": 3}]
}
```

## Pack contract source of truth

- Manifest schema: `schemas/pack.schema.json`
- Backend validation: `src/sc4s_manager/packs.py`
- Frontend Zod schemas must be a direct translation of the same fields.

## Stable v0.1 fields

- `schema_version`: pack manifest contract version, currently `0.1`.
- `version`: pack content version.
- `supported_transports`: explicit transport/protocol/framing/envelope/payload fields.
- `test_event_sets`: explicit event boundary, uniqueness, delimiter/multiline, timestamp policy, and field delimiting metadata.
- `event_families`: regex engine plus expected output sourcetype.
- `export_artifacts`: source path, target path, kind, rendered/static flag, secret policy, required flag.
- `provenance`: `origin` and `pack_class` use the source classes from `docs/contracts/catalogue-api.md`; curated Library packs use `sechub-resource`.
- `relationship_to_upstream`: includes `new_pack` for packs with no upstream SC4S equivalent.
