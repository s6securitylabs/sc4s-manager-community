# SC4S Manager Catalogue Data

Owns generated/imported catalogue data used by Manager. This area is source/index data for discovery and import workflows, not deployed runtime state.

## Entry Points

- `generated/upstream/` - upstream SC4S built-in/Lite catalogue snapshots and drift reports.
- `generated/community/` - community/source-corpus candidate catalogue snapshots.

## Contracts & Invariants

- Generated catalogue records remain separate from local imported/applied pack state.
- Preserve origin/effective origin, source status, provenance URL/source kind, relationship to upstream, trust/quality, validation state, and candidate warnings.
- Community/source-corpus data is untrusted input. It must stay candidate/unvalidated until curated and promoted.
- Upstream SC4S coverage is useful inventory, not SC4S Manager validation evidence.
- Generated data must not contain secrets, customer identifiers, tokens, private URLs, or raw auth state.

## Patterns

Refreshing or adding catalogue data:
1. Keep upstream/community source classes explicit.
2. Record enough provenance to reopen the source thread/ref later.
3. Run backend catalogue tests after changing schema/shape.
4. Keep promotion to `../packs/` or `../community/` as a separate review task.

## Anti-patterns

- Treating generated rows as applied configuration.
- Letting issue/PR text self-assert validated or production-ready status.
- Hiding provenance after dedupe or merge.

## Related Context

- Backend catalogue logic: `../src/AGENTS.md`
- Community staging: `../community/AGENTS.md`
- Contract docs: `../docs/AGENTS.md`
