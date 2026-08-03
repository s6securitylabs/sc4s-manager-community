# SC4S Manager Community Staging

Owns unpromoted community pack material. This is a staging lane for reviewable `.conf`, `.csv`, fixture, and documentation diffs before any promotion into curated packs.

## Entry Points

- `README.md` - staging rules and candidate stance.
- `community/<pack_id>/` - future staged pack material.
- `../docs/contributing/templates/community-pack/` - safe starter template, not a real shipped pack.

## Contracts & Invariants

- Default origin is `community-extra`.
- Default trust is `community_submitted`; default quality is `catalogued` or `draft` until evidence exists.
- Candidate material is local/staged input, not Library-published approval and not deployed Manager state.
- Likes, ratings, comments, issue mentions, or PR popularity must not change trust/quality by themselves.
- Promotion to curated `packs/` requires review, validation, evidence, and removal of candidate-only state.
- Functional behavior remains file-backed; do not bury parser/filter/Splunk logic inside prose or JSON blobs.

## Patterns

Promoting a community candidate:
1. Convert useful source material into first-party files under a staged pack shape.
2. Preserve source URLs, source kind, and artifact-level provenance.
3. Validate schema, fixtures, parser/config safety, and evidence.
4. Move/promote only after review into curated pack location and update trust/quality from evidence.

## Anti-patterns

- Presenting a candidate as validated because the source issue/PR claims it works.
- Copying opaque snippets without attribution, license review, and reviewable artifact conversion.
- Applying or deploying community-stage material without operator validation.

## Related Context

- Catalogue generated candidates: `../catalogue/AGENTS.md`
- Backend import/catalogue behavior: `../src/AGENTS.md`
- Contribution docs: `../docs/AGENTS.md`
