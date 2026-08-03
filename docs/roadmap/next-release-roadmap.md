# SC4S Manager Next Release Roadmap

Date: 2026-06-14
Status: Draft roadmap for the release after the current public/pilot V1 candidate
Scope: SC4S Manager control plane, operator UI/API, runtime evidence, SecHub/Library import path, packaging, and release validation

## Executive verdict

The current `main` branch is suitable for a protected controlled/pilot V1 release candidate: final acceptance, E2E UI evidence, CRUD operator journeys, and live Splunk indexed readback all validate. The next release should not chase broad product sprawl. It should turn the pilot candidate into a repeatable operator product by hardening installation, runtime observability, source onboarding evidence, fallback triage, packaging, and release evidence.

Recommended next-release theme:

> Make SC4S Manager boring to operate: installable, observable, reversible, evidence-backed, and clear about what is staged, applied, live, and Splunk-proven.

## Current baseline

Current validated baseline:

- Branch: `main`
- Current acceptance gate: `python3 scripts/validate_acceptance_evidence.py --require-final --require-e2e-ui --require-crud-journeys` passes.
- Backend/package suite: `./scripts/test.sh` passes with 216 backend tests and pack validation.
- Frontend suite/build: Vitest passes with 37 tests and production build succeeds.
- Live proof exists for:
  - protected public route boundary;
  - authenticated/internal UI/API readback;
  - CRUD source, destination, route, import/apply, delete, rollback, and negative security journeys;
  - SC4S -> HEC -> Splunk indexed marker readback.

Release posture:

- **Good for:** controlled/pilot public release behind Authentik/APISIX/Cloudflare.
- **Not yet good for:** broad enterprise GA, unattended customer installs, multi-environment fleet operation, or public claims beyond the validated lab scope.

## Next release goal

Ship a stronger V1.x release that a Splunk/SC4S operator can install or upgrade, use for real onboarding work, diagnose runtime problems, and export defensible evidence without needing Jarvis-level handholding.

The next release should close five practical gaps:

1. **Operational repeatability:** install, upgrade, rollback, and package versioning are tested as product workflows.
2. **Runtime truth:** Manager shows live SC4S/container/listener/counter/destination state, not only saved config.
3. **Onboarding evidence:** a source can be onboarded from sample/fixture/pack through parser preview, apply, marker replay, and Splunk readback.
4. **Failure visibility:** fallback/lastchance, drops, queues, HEC failures, and validation failures are surfaced with next actions.
5. **Release evidence:** every release has a single evidence bundle that proves what passed, what was skipped, and what remains pilot-only.

## Must do for the next release

These are release blockers. If they are not done, call the next build another pilot refresh rather than a next release.

Implementation plan: [docs/roadmap/implementation-plan-1-2-3-5.md](implementation-plan-1-2-3-5.md)

### 1. Package/install/upgrade/rollback drill

Problem:

The current evidence proves the running lab and local tests. It does not yet prove a clean operator install/upgrade/rollback path as a repeatable product workflow.

Deliverables:

- Versioned release artifact with backend, frontend `dist`, systemd units, control daemon unit/socket, env template, and runbooks.
- Clean install drill on a disposable VM/LXC or clean directory-based test host.
- Upgrade drill from the current pilot layout to the next release layout.
- Rollback drill back to the previous known-good Manager build and SC4S config state.
- Evidence artifact under `docs/acceptance/` with timestamps, commands, redacted config, service state, and rollback result.

Acceptance gate:

```bash
./scripts/test.sh
cd frontend && npm test -- --run && npm run build
python3 scripts/validate_acceptance_evidence.py --require-final --require-e2e-ui --require-crud-journeys
# plus a new packaging/install validator once implemented
```

Required proof:

- fresh install starts Manager and control daemon;
- upgrade preserves local state, imports, backups, audit history, and auth config;
- rollback restores the prior service state and leaves SC4S healthy;
- no package step runs hidden `npm install` or writes generated frontend assets unexpectedly.

### 2. Runtime-health dashboard v1

Problem:

Operators need to see live truth quickly: process/container state, listeners, syslog-ng counters, destination health, dropped/queued/written counters, and recent warnings. Saved config without live state invites bad decisions.

Deliverables:

- API endpoint or endpoints for runtime state:
  - Manager service health;
  - control daemon health;
  - SC4S container/process status;
  - running SC4S image/version;
  - live listener sockets and bind addresses;
  - syslog-ng source/parser/destination counters;
  - HEC/syslog destination written/dropped/queued counters;
  - recent warnings/errors from SC4S logs.
- Dashboard UI cards that clearly distinguish:
  - saved/staged config;
  - applied config;
  - live runtime state;
  - Splunk-proven state.
- Tests for schema stability and redaction.

Acceptance proof:

- live API readback from the lab;
- screenshot or structured browser artifact for the dashboard;
- counter deltas before/after a marker send;
- no secret leakage from HEC URLs/tokens or proxy headers.

### 3. Source onboarding and parser preview workflow

Problem:

The product wedge is source lifecycle management, not just CRUD forms. Operators need to understand what an emitted event looks like, which parser path it will hit, what metadata will be assigned, and what validation is needed before apply.

Deliverables:

- UI/API workflow to paste or upload representative sample events safely.
- Format classification hints:
  - RFC3164/RFC5424;
  - CEF/LEEF;
  - raw/headerless;
  - JSON/CSV-ish;
  - multiline or boundary ambiguity.
- Candidate parser/pack match preview with why it matched or failed.
- Expected Splunk metadata preview:
  - index;
  - sourcetype;
  - source;
  - host/fromhost;
  - timestamp policy.
- Convert accepted samples into redacted fixture candidates where appropriate.

Acceptance proof:

- at least one known-good Cisco ASA path previews correctly;
- at least one nonmatching/fallback sample reports a clear next action instead of false success;
- tests prove samples do not auto-promote trust or validation state;
- sample content is redacted or stored only as explicitly approved fixture material.

### 4. Fallback/lastchance and wrong-metadata triage

Problem:

A healthy SC4S process can still be operationally wrong if events land in fallback/lastchance, wrong index, wrong sourcetype, wrong host, or unexpected timestamp windows.

Deliverables:

- Runtime/API detection for fallback/lastchance counters and recent events where Splunk access is configured.
- UI triage panel that answers:
  - which source or sender appears to be failing parser classification;
  - expected vs observed sourcetype/index/source/host;
  - likely cause: listener mismatch, parser miss, destination/index mismatch, timestamp issue, or Splunk search permission issue;
  - recommended next validation step.
- Evidence link from triage result to marker replay/readback when available.

Acceptance proof:

- fixture or live marker producing expected metadata is shown as good;
- intentionally unmatched sample/route is shown as fallback/needs action;
- no fallback candidate is presented as validated support.

### 5. SecHub Library import reliability and trust semantics

Problem:

J12 now proves import/apply/rollback, but the next release should make SecHub/Library source handling robust enough that failures are explainable to an operator rather than looking like generic HTTP or Python errors.

Deliverables:

- Configured source inventory page with live fetch status for catalogue, manifest, entries, bundles, checksums, and sidecars.
- Better error classification:
  - DNS failure;
  - Cloudflare/bot-policy/client-header mismatch;
  - manifest missing;
  - checksum mismatch;
  - bundle too large;
  - unsafe archive path/member;
  - schema/API mismatch.
- Preserve current trust semantics:
  - remote Review/quality labels are advisory;
  - local `is_verified`/validated state requires locally generated validation JSON with runtime and Splunk stages where claimed.

Acceptance proof:

- live Manager HTTP client can fetch the configured Library catalogue/manifest endpoints;
- at least one curated pack import validates and applies in the lab;
- a deliberately broken source reports a controlled actionable error;
- tests prove remote metadata alone cannot set local verified state.

### 6. Release evidence bundle and one-command release gate

Problem:

Acceptance evidence exists, but release decisions should not require hunting through multiple JSON files and old reports.

Deliverables:

- New release evidence bundle command, for example:

```bash
python3 scripts/build_release_evidence_bundle.py --release-version <version> --output docs/acceptance/releases/<version>/
```

- Bundle contents:
  - git commit/branch/status;
  - backend test result summary;
  - frontend test/build summary;
  - protected-route proof;
  - authenticated UI/API proof;
  - CRUD journey proof;
  - runtime marker/Splunk proof;
  - package/install/upgrade/rollback proof;
  - known limitations;
  - skipped stages with explicit reason.
- Validator flag for next release, for example:

```bash
python3 scripts/validate_acceptance_evidence.py --require-release-bundle <version>
```

Acceptance proof:

- the release bundle validator fails when required proof is absent;
- the validator distinguishes warning-only skipped dev checks from release-blocking skipped runtime/Splunk checks;
- generated bundle contains no secrets.

## Should do if time permits

These should be pulled in if the release blockers are under control.

### 7. Splunk TA/CIM readiness evidence

Add a per-pack readiness panel and validation result for:

- expected TA dependency or absence;
- CIM/datamodel relevance;
- props/transforms/eventtypes/tags coverage;
- fields required for common SOC searches;
- known limitations.

Minimum useful proof: Cisco ASA or Palo Alto path shows expected fields and notes what is not proven.

### 8. Destination and queue diagnostics

Expose destination-level health beyond simple HEC config:

- HEC health and token/index allowlist checks with redaction;
- destination written/dropped/queued/retry counters;
- backpressure warnings;
- test destination marker with Splunk readback where safe.

Keep all token handling file/env-based and redacted.

### 9. Policy-driven reduction preview

Start narrow: preview-only noise reduction for one high-volume source family.

Requirements:

- no lossy reduction enabled by default;
- show estimated event-volume impact from fixture or recent sample only;
- generate reviewable postfilter/filter `.conf` artifacts;
- rollback and audit included.

### 10. Audit/export polish

Improve operator handoff evidence:

- export audit trail for source/destination/route/apply/rollback actions;
- include actor where available;
- include before/after target paths without secret values;
- include evidence links for validation/readback.

### 11. Browser SSO journey proof

Current evidence intentionally separates public Authentik protection from authenticated/internal route proof. If public demo confidence matters, add a true browser SSO journey capture through the public hostname, with cookies/tokens redacted.

Do not block the next release on this unless the release is marketed as public self-serve rather than protected pilot.

## Want to do / later roadmap

These are valuable but should not block the next release.

### Multi-site and fleet management

- Multiple SC4S environments/sites.
- Per-site source inventory and drift.
- Central evidence dashboard.
- Site-specific destination/index policy.

Do this after the single-site install/upgrade/runtime story is boring.

### Persistent buffering and resilience management

- Persistent queue visibility.
- Disk buffer sizing guidance.
- Splunk outage simulation and recovery proof.
- Data-loss risk indicators.

This is strategically important because it addresses a common reason teams look at Cribl, but it needs careful SC4S/syslog-ng design.

### Multi-destination routing beyond Splunk HEC/syslog

Potential destinations:

- secondary syslog relay;
- object storage archive;
- Kafka or HTTP collector;
- Splunk HEC fan-out.

Only ship routes that can be previewed, validated, monitored, and rolled back.

### Community candidate promotion workflow in the UI

- Show `community-extra` candidates in catalogue with strong warnings.
- Allow maintainers to stage candidates into file-backed artifacts.
- Require provenance, fixtures, validation, and Splunk evidence before promotion.

Do not let GitHub issue/PR popularity become trust or validation.

### AI-assisted parser suggestions

Useful only if constrained:

- suggestions are draft-only;
- generated parser/config is file-backed and reviewable;
- fixture tests and live validation are mandatory;
- never auto-promote to validated/verified.

### Kubernetes/OpenShift deployment mode

Useful for enterprise environments, but defer until:

- single-node deployment is robust;
- control daemon boundaries are stable;
- runtime evidence collection does not assume Docker-only semantics.

## Release sequencing

### Milestone 1: release hygiene and packaging

Goal: make the current candidate installable and releasable.

Tasks:

1. Define release versioning and artifact layout.
2. Add packaging/install validator.
3. Run clean install drill.
4. Run upgrade drill from current pilot layout.
5. Run rollback drill.
6. Add release evidence bundle skeleton.

Exit criteria:

- package/install/upgrade/rollback evidence exists and validates;
- existing final/E2E/CRUD gates still pass.

### Milestone 2: runtime truth dashboard

Goal: show live SC4S state and counters clearly.

Tasks:

1. Add runtime-state API schema.
2. Read control daemon/service state.
3. Read SC4S process/container status and version.
4. Read listener sockets.
5. Parse syslog-ng stats into stable source/parser/destination rows.
6. Add dashboard cards and warnings.
7. Add marker-send counter delta evidence.

Exit criteria:

- operator can see whether a saved source is actually live;
- marker traffic changes visible counters;
- redaction tests pass.

### Milestone 3: onboarding preview and fallback triage

Goal: help operators understand whether a source will parse and where it lands.

Tasks:

1. Add sample-event classification endpoint.
2. Add parser/pack match preview.
3. Add expected metadata preview.
4. Add fallback/lastchance detection.
5. Add triage UI with next-action guidance.
6. Validate one good path and one deliberate fallback path.

Exit criteria:

- Cisco ASA path previews and validates;
- unmatched sample is clearly marked as not validated;
- Splunk readback can be attached to the evidence trail.

### Milestone 4: Library import reliability and release bundle

Goal: make SecHub import failures and release proof boring.

Tasks:

1. Add Library source health checks for catalogue/manifest/entries/bundles.
2. Classify fetch/import failures.
3. Strengthen local verified-state gating.
4. Finish release evidence bundle command.
5. Add `--require-release-bundle` validator.
6. Run full lab release acceptance.

Exit criteria:

- J12 stays green;
- broken source failure is actionable;
- release bundle gives a one-page go/no-go verdict and machine-readable proof.

## Validation matrix

A next-release candidate is ready only when all of these are true:

- Local backend/package validation: `./scripts/test.sh` passes.
- Frontend validation: `npm test -- --run && npm run build` passes.
- Final acceptance: `--require-final` passes.
- UI journey evidence: `--require-e2e-ui` passes.
- CRUD journey evidence: `--require-crud-journeys` passes.
- Package/install/upgrade/rollback evidence passes the new validator.
- Runtime dashboard evidence includes live state and counter deltas.
- Source onboarding preview has good-path and fallback-path proof.
- Library import has live success and controlled failure proof.
- Release bundle validates and contains no secrets.

## Non-goals for the next release

- Do not build a generic SIEM or observability pipeline.
- Do not expose arbitrary shell, Docker socket, compose path, or container control in the web/API process.
- Do not treat SecHub Review status as deployment approval.
- Do not mark a pack locally verified from remote metadata, dates, prose, manifest claims, or evidence-looking paths.
- Do not enable lossy filtering/reduction by default.
- Do not block the release on multi-site fleet management, Kubernetes, or AI parser generation.

## Suggested product language for the next release

Use this wording:

> SC4S Manager V1.x is a protected SC4S operating plane for source onboarding, runtime visibility, safe apply/rollback, and Splunk evidence in controlled environments.

Avoid this wording until broader proof exists:

- enterprise GA;
- universal telemetry pipeline;
- automatic parser generation;
- production verified for every Library pack;
- self-serve public SaaS.

## Immediate next actions

Implementation planning for blockers 1, 2, 3, and 5 is tracked in `docs/roadmap/implementation-plan-1-2-3-5.md`.

1. Execute the packaging/install/upgrade/rollback implementation lane from the plan.
2. Add the runtime-state API schema, control-daemon readback, and dashboard cards.
3. Implement source sample classification/parser preview for one proven source family and one fallback case.
4. Implement SecHub Library source-health/error-classification/trust-semantics work.
5. Run the full lab acceptance gate and publish the release bundle once evidence exists.
