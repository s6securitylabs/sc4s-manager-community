# SC4S Manager Acceptance Evidence

Owns timestamped acceptance artifacts, live-route probes, install/rollback drill notes, and release-readiness proof. This directory records what happened during a scoped validation run; it is not the place to redefine product contracts or retrofit old evidence to match new intent.

## Purpose & Scope

- Preserve reviewable proof for browser/API coverage, deployment drills, rollback checks, and ingestion validation.
- Keep machine-readable evidence (`.json`, structured snapshots) paired with human-readable narrative where needed.
- Treat `evidence/` as append-only historical output except for explicit cleanup/redaction work.
- Normative product/API behavior belongs in `../contracts/`, `../product-requirements.md`, and implementation/tests, not here.

## Entry Points

- `README.md` - acceptance program overview and evidence map.
- `browser-public-route.md` - operator-readable interpretation of unauthenticated browser checks.
- `browser-*-live.json` and `api-acceptance-*.json` - structured probe outputs from specific runs.
- `security-acceptance.md` and `real-ingestion-validation.md` - scenario-focused acceptance narratives.
- `evidence/browser-routes/<timestamp>/` - timestamped route snapshots captured from a single probe run.

## Contracts & Invariants

- Every artifact must make its scope and time basis clear; never present stale evidence as current live proof.
- Historical evidence is additive: append a new timestamped run instead of rewriting old results to fit the latest design.
- Redact secrets, tokens, customer identifiers, proxy headers, and other raw auth material without corrupting the surrounding structured evidence.
- Distinguish public-route checks, authenticated browser/API checks, local dry runs, deployment drills, and real-ingestion validation; they are not interchangeable.
- Health/status snapshots alone are insufficient proof for import/apply/rollback/operator workflow claims.
- Evidence should stay traceable to the script or workflow that generated it so reviewers can reproduce or challenge it.

## Patterns

Adding a new acceptance run:
1. Capture outputs into a new timestamped path under `evidence/` when the run produces multiple artifacts.
2. Keep filenames scoped to the workflow being proved (`browser-routes`, `api-acceptance`, `rollback-drill`, etc.).
3. Add a short narrative markdown companion when raw JSON/text needs operator interpretation or caveats.
4. Cross-check related scripts/tests under `../../scripts/` and `../../tests/` if the evidence format changes.

Refreshing a standing proof document:
1. Update the narrative to point at the new timestamped evidence set.
2. Preserve or explicitly supersede older references instead of silently replacing them.
3. Call out blockers, partial coverage, and environment limits instead of rounding them into success.

## Anti-patterns

- Overwriting old JSON snapshots in place when the goal is to capture a new run.
- Treating an IdP redirect, 200 health endpoint, or static page load as proof of authenticated workflow success.
- Mixing roadmap/design aspirations into run evidence.
- Hand-editing generated JSON in ways that blur what the probe actually observed.

## Related Context

- Parent docs policy: `../AGENTS.md`
- Contracts and public interfaces: `../contracts/`
- Validation and probe scripts: `../../scripts/`
- Regression coverage for evidence shape: `../../tests/AGENTS.md`
