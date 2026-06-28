# SC4S Manager Frontend

Owns the operator UI: route shell, catalogue/pack screens, API client types, local user-facing state, and browser-level behavior. It presents evidence and operator decisions; it does not invent backend truth.

## Entry Points

- `src/main.tsx` - application bootstrap.
- `src/components/AppLayout.tsx` - navigation shell and global layout.
- `src/routes/*.tsx` - dashboard, catalogue, pack, export screens.
- `src/api/packs.ts` and `src/api/library.ts` - typed API clients and response normalization.
- `src/lib/*.ts` - navigation, URL, security, and download helpers.
- `src/**/*.test.ts(x)` - frontend contract and behavior tests.

## Contracts & Invariants

- UI must distinguish Library/catalogue confidence from local deployment readiness.
- Candidate/community entries must visibly remain candidate/unvalidated and must not look production-ready.
- Zod/type parse failures are frontend/backend contract bugs even when HTTP status is 200.
- Show desired, staged, applied, and live state separately. Do not imply an unapplied draft is active.
- Redacted or missing sensitive values must not be re-expanded or guessed in the UI.
- Mantine widgets may need targeted tests; role-selector brittleness alone is not proof of user-visible breakage.

## Patterns

Changing a UI-facing API field:
1. Update backend tests/contract first where possible.
2. Update `src/api/packs.ts` / `src/api/library.ts` parsing and defaults.
3. Update route components and empty/loading/error states.
4. Add or update route/API tests.
5. Run frontend type/tests/build when code changes warrant it.

Adding operator workflow UI:
1. Lead with the operator question and risk state.
2. Show evidence, limitations, and required next validation.
3. Separate preview from apply and apply from live proof.
4. Preserve rollback/audit expectations in labels and actions.

## Anti-patterns

- Hiding warnings behind generic metadata panels.
- Treating a catalogue row or download link as deployment approval.
- Hardcoding filter universes that should come from catalogue facets.
- Swallowing failed requests or schema errors into plausible-looking empty states.

## Related Context

- Backend/API: `../src/AGENTS.md`
- Contract docs: `../docs/AGENTS.md`
