# Community staging area

This directory is the non-core staging area for SC4S Library pack submissions.

Use `community/<pack_id>/` only for local, non-publishing Manager development state that follows the SC4S Library pack schema. Canonical promotion occurs in Forgejo `s6-infra/sechub-resources`; this directory is not a product or Library publication source.

Community-stage rules:

- Catalog origin is `community-extra`.
- Default trust should be `community_submitted` unless a reviewer has explicitly raised it.
- Default quality should be `catalogued` or `draft` until validation evidence exists.
- Likes, ratings, and comments are feedback signals only; they must not change trust or quality by themselves.
- Functional configuration remains file-backed: `.conf` and `.csv` artifacts plus declared fixtures/evidence.
- Promotion means recreating or moving the reviewed candidate into canonical SecHub Resources `packs/<pack_id>/`. Manager's checked-in `packs/` remain pinned fixtures, not the canonical destination.

The example scaffold lives under `docs/contributing/templates/community-pack/` so contributors can copy a safe starting point without accidentally shipping the template itself as a real pack.

For catalogue and UI behavior, keep candidate records aligned with `docs/roadmap/community-candidate-lifecycle.md`: `community-extra` entries remain `source_status=candidate` and `validation.state=unvalidated_source_corpus` until a curated pack promotion path is completed.
