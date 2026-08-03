# SC4S Manager Documentation

Owns product requirements, API/data contracts, contribution guides, runbooks, acceptance evidence, reports, and roadmap material. Docs must distinguish normative contracts from historical evidence.

**Before modifying acceptance evidence or live-proof artifacts, read `acceptance/AGENTS.md` first** so you preserve timestamp/redaction rules and do not rewrite historical proof.

## Entry Points

- `product-requirements.md` - current Manager product boundary and acceptance intent.
- `contracts/` - stable API/export/pack contracts.
- `runbooks/` - operational install, upgrade, rollback, production configuration paths.
- `acceptance/` - release/deployment evidence and proof artifacts.
- `roadmap/` - future plans, gap analyses, and implementation roadmaps.
- `roadmap/next-release-roadmap.md` - current next-release must/should/want roadmap and validation matrix.
- `roadmap/product-market-research-and-key-drivers.md` - active market-research drivers that should shape roadmap priority and prevent generic telemetry-pipeline scope creep.
- `contributing/` - pack/community contribution guidance and templates.
- `library/` - explanatory docs for SC4S Manager catalogue/pack positioning.

## Contracts & Invariants

- Contract docs should describe current or intended interface behavior; acceptance evidence records what happened at a point in time.
- Do not rewrite historical evidence to match new intent. Add new evidence instead.
- Public/product docs must preserve the Manager/Library boundary: Library publishes catalogue/artifacts; Manager validates/applies/operates locally.
- Keep product Splunk TA releases distinct from SC4S Library pack ZIPs. Product TAs are installed through product runbooks; Manager only imports and applies contract-valid Library packs.
- Runbooks must preserve safety order: backup before mutation, validate before apply, post-check after apply, rollback-ready evidence retained.
- Acceptance docs must not contain secrets, tokens, customer identifiers, proxy shared secrets, or raw auth headers.

## Patterns

Changing a contract:
1. Update backend/frontend tests with the contract change.
2. Keep examples consistent with actual response/request shapes.
3. Surface provenance/trust/candidate semantics when catalogue/pack behavior changes.
4. Record open decisions instead of burying unresolved policy in examples.

Adding evidence:
1. Timestamp and scope it.
2. Redact secrets and sensitive identifiers.
3. State whether it is public-route protection, authenticated UI/API behavior, local test evidence, or live runtime proof.
4. Do not confuse health checks with workflow proof.

## Anti-patterns

- Treating stale roadmap text as implementation truth without checking code/tests.
- Mixing future design claims into acceptance evidence.
- Counting IdP redirects as authenticated UI coverage.
- Presenting warnings-only states as blocking failures unless risk is real.

## Related Context

- Backend/API implementation: `../src/AGENTS.md`
- UI implementation: `../frontend/AGENTS.md`
- Tests: `../tests/AGENTS.md`
