# SC4S Manager Tests

Owns backend regression, contract, validation, exporter, control, pack, catalogue, and acceptance-probe tests. Tests encode safety boundaries and must not be weakened to make product claims pass.

## Entry Points

- `test_manager.py` - app/manager behavior smoke and integration-style checks.
- `test_catalogue*.py` and `test_upstream_catalog.py` - catalogue merge, API, docs-index, and upstream behavior.
- `test_packs*.py` and `test_pack_validation.py` - pack inventory/schema/fixture validation.
- `test_library.py` - SecHub Resources sync/download/import/apply boundary tests.
- `test_control.py` - runtime-control boundary tests.
- `test_exporters.py` and `test_packaging_foundations.py` - bundle/export behavior.
- `test_acceptance_*` and `test_ci_functional*` - evidence/probe/functional acceptance helpers.

## Contracts & Invariants

- Security and control-plane tests protect real boundaries; do not convert them to warnings without a product decision.
- Catalogue tests must preserve provenance, source classes, trust/quality, candidate status, and validation state.
- Pack tests must enforce fixture semantics and reject unsafe/default-drop behavior where the contract requires it.
- Acceptance evidence tests should verify evidence shape and redaction, not fabricate proof.
- Targeted test runs may disable coverage through `scripts/test.sh`; full suite keeps the repository coverage gate.

## Patterns

Changing backend behavior:
1. Add/update the closest unit/contract test first.
2. Keep fixtures small and explicit.
3. Verify both positive behavior and safety failure modes.
4. Use `../scripts/test.sh <target>` for targeted checks, then broader checks if behavior spans areas.

Changing catalogue/community behavior:
1. Test candidate clamping and provenance preservation.
2. Test filters/facets/detail shape if UI/API visible.
3. Do not rely on generated data alone as the assertion source.

## Anti-patterns

- Skipping security tests because the lab route is trusted.
- Treating generated acceptance JSON as current live proof without reading its timestamp/scope.
- Weakening coverage/safety gates for unrelated targeted changes.

## Related Context

- Backend implementation: `../src/AGENTS.md`
- Contracts/evidence docs: `../docs/AGENTS.md`
