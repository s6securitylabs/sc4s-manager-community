# SC4S Manager Backend

Owns the Python Manager API, catalogue/pack model, validation/export logic, runtime-control client, and test-path helpers. This layer is the authority for backend contracts consumed by the UI and scripts.

## Entry Points

- `sc4s_manager/app.py` - Manager API surface and route composition.
- `sc4s_manager/control.py` - narrow runtime-control client/boundary.
- `sc4s_manager/catalogue.py` and `upstream_catalog.py` - catalogue merge/import/upstream inventory logic.
- `sc4s_manager/packs.py` and `pack_validation.py` - pack inventory and validation behavior.
- `sc4s_manager/library.py` - SecHub Resources sync/download/import/apply boundary.
- `sc4s_manager/exporters.py` - SC4S/Splunk/pack export handling.
- `sc4s_manager/ci_functional.py` and `test_paths.py` - acceptance/test support paths.

## Contracts & Invariants

- Mutation endpoints must never provide arbitrary shell, Docker, compose, container, path, or command execution.
- Runtime control is fixed-action and scoped to Manager/SC4S operations: status, logs, validate, reload/restart where supported, metrics, and evidence readback.
- API responses must preserve typed metadata. Redaction must not change booleans/lists/objects into strings.
- Catalogue import preserves provenance, source status, trust/quality, validation state, and candidate warnings.
- Imported packs are draft/local until validation and explicit operator approval; import is not apply.
- Path containment must use canonical resolved paths, not string-prefix checks.
- Archive/import handling must bound size, member count, per-member size, and total expanded size.

## Patterns

Adding an API/contract field:
1. Update backend model/serializer and tests together.
2. Update `../docs/contracts/` if public or UI-facing.
3. Update frontend API schema/client in `../frontend/`.
4. Add candidate/trust/security regression tests when catalogue/import behavior changes.

Adding runtime control:
1. Prove the action belongs in the SC4S allowlist.
2. Keep request schema strict and path/service identity fixed.
3. Add audit/evidence behavior and tests.
4. Validate staged/applied/live readback stays separate.

## Anti-patterns

- Treating HTTP 200 as success when payload shape violates the UI contract.
- Letting Library trust labels bypass local validation.
- Calling health-only checks proof that import/apply/runtime workflows work.
- Logging proxy headers, HEC tokens, shared secrets, or raw auth state.

## Related Context

- UI expectations: `../frontend/AGENTS.md`
- Tests: `../tests/AGENTS.md`
- Docs/contracts: `../docs/AGENTS.md`
