# SC4S Manager

SC4S Manager is the private operator control plane for SC4S-compatible ingestion environments. It imports packs, validates them locally, previews and applies configuration through a narrow control path, observes runtime state, and supports rollback/evidence workflows.

## Intent Layer

**Before modifying code in a subdirectory, read its AGENTS.md first** to understand local patterns and invariants.

- **Backend/control plane**: `src/AGENTS.md` - Manager API, catalogue/pack logic, validation, exporters, runtime control.
- **Operator UI**: `frontend/AGENTS.md` - React/Mantine UI, route behavior, typed API client, user-facing states.
- **Product/contract docs**: `docs/AGENTS.md` - PRD, contracts, runbooks, acceptance evidence, roadmaps.
- **Acceptance evidence**: `docs/acceptance/AGENTS.md` - release/live-proof artifacts, redaction rules, timestamped evidence handling.
- **Catalogue data**: `catalogue/AGENTS.md` - generated/imported catalogue data and provenance boundaries.
- **Community staging**: `community/AGENTS.md` - unpromoted community pack candidates.
- **Tests**: `tests/AGENTS.md` - backend regression and contract tests.

## Architecture

```text
src/sc4s_manager/          Manager API, control logic, pack/catalogue code
frontend/               Operator UI
packs/                  Built-in/local packs
catalogue/              Generated/imported catalogue data
community/              Community/candidate source material and ingestion notes
docs/contracts/         API and data contracts
docs/runbooks/          Install, upgrade, rollback, and operations runbooks
docs/acceptance/        Deployment and release evidence
docs/roadmap/           Feature plans and implementation roadmaps
scripts/                Test, validation, install, and evidence scripts
```

## Operating Persona

When authoring prompts, review guidance, validation scripts, roadmap criteria, UI text, API evidence, or operator workflows, use this stance:

> Act like a cyber security operations engineer responsible for safe log onboarding, parser validation, SOC usability, and defensible Splunk/SC4S evidence.

That means prioritising real event semantics, source/version/log-format clarity, parser-path proof, Splunk readback, CIM/SOC usefulness, reduction safety, staged-vs-applied-vs-live state, rollback/limitations, and evidence a SOC reviewer can challenge. Avoid generic assistant, marketing, or developer-only framing.

## Global Invariants

- Manager consumes Library/local artifacts as untrusted input. Library Review status and Community rating are advisory; local validation gates import/apply.
- Product Splunk TA TGZ releases are advisory product-deployment artifacts and are never Manager-importable packs. Manager may link to them separately but only imports contract-valid SC4S Library ZIPs.
- Distinguish embedded catalogue entry, staged local import, draft config, applied config, validation evidence, backup/rollback artifact, and audit record.
- Mutating operations follow preview → validate → operator approval → backup → apply via narrow control daemon → post-check → rollback-ready evidence.
- Web/API code must not expose unrestricted shell, host, container, compose, path, or Docker socket control.
- Redact secrets in API/UI/diffs/logs/reports/evidence; do not corrupt typed metadata while redacting.
- Runtime state and desired configuration are separate. Do not imply staged/validated config is already live.
- Community/source-corpus material remains candidate/Unreviewed until curation, validation, and local evidence promotion.

## Commands

```bash
./scripts/test.sh
```

The test script validates packs/fixtures and runs pytest with writable temp defaults for venv, cache, coverage, and evidence.

## Related Context

- Product requirements: `docs/product-requirements.md`
- Catalogue API contract: `docs/contracts/catalogue-api.md`
- Pack export contract: `docs/contracts/pack-export-contract.md`
- Canonical repository: `s6securitylabs/sc4s-manager`
