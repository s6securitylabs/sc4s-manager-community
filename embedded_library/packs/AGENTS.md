# SecHub Resources packs

`packs/` owns source-component manifests, SC4S/syslog-ng and Splunk artifacts, safe fixtures, helper scripts, research notes and validation evidence. Operator-facing product deployment identity belongs under `products/`.

## Required posture

- `pack.json` is a manifest, not an embedded parser language. Refer to reviewable artifact files.
- New or expanded packs remain `curated` or lower and `unverified` until current replay/readback evidence proves more. Blocked preflight is not validation.
- State source identity and mode, transport/envelope/event boundaries, timestamp/timezone policy, collection path, credential/checkpoint owner, default index/sourcetype, provenance, redistribution state, limitations and required-field coverage.
- Use explicit evidence-needed values such as `unknown_requires_evidence`; never disguise missing source shape as a structured claim.
- Preserve raw context by default. Filtering, dropping, masking and reduction are opt-in, documented, artifact-backed and include rollback plus replay/readback expectations.
- Use safe fixtures with unique markers. Do not include tenant IDs, real users/hosts, tokens, proprietary vendor content or unsafe samples.
- Research notes belong under `packs/<pack_id>/docs/research/` and use `<publisher-or-researcher>-<topic>-<YYYYMMDD>.md`. Open with title, author/organisation, canonical URL, publication/access dates and licence/terms. Store derived analysis; quote only what is technically necessary. Public availability is not redistribution permission. Keep any permitted private full-text cache outside pack/export paths and do not reference it from distributable artifacts.
- Do not hand-edit generated product mirrors, release archives or `site/`.

## Checks

Before editing, inspect `git status --short`. For source-shape changes run:

```bash
python3 scripts/audit_source_shape_display_fields.py
```

Then run focused fixture/hash checks and the repository gate:

```bash
scripts/run_ci.sh
```

Before claiming promotion, confirm replay through the intended route and destination readback for count, index, sourcetype, source, timestamps and required normalized fields.
