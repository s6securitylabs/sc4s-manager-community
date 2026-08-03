# SC4S Manager Next-Release Items 1, 2, 3, and 5 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Implement the next-release blockers for packaging/install/upgrade/rollback, runtime truth, source onboarding/parser preview, and SecHub Library import reliability/trust semantics.

**Architecture:** Keep Manager as a constrained SC4S control plane: backend APIs provide typed evidence, frontend routes present operator decisions, and live/runtime proof is collected through allowlisted control-daemon actions plus explicit acceptance scripts. Remote Library metadata remains advisory; local verification is only set by local validation evidence.

**Tech Stack:** Python stdlib HTTP backend under `src/sc4s_manager/`, control daemon in `src/sc4s_manager/control.py`, pytest backend tests, React/Mantine/TanStack Query frontend under `frontend/`, Vitest frontend tests, shell packaging scripts under `deploy/` and `scripts/`.

---

## Scope and sequencing

Implement roadmap blockers **1, 2, 3, and 5** in this order:

1. **Package/install/upgrade/rollback drill** — release hygiene first so every later feature can be packaged and rollback-tested.
2. **Runtime-health dashboard v1** — live truth API and UI, because onboarding and Library apply need runtime readback.
3. **Source onboarding and parser preview workflow** — sample classification, parser/pack match preview, and metadata preview.
4. **SecHub Library import reliability and trust semantics** — source health inventory, classified errors, and local verification gating.
5. **Integrated evidence run** — one lab pass proving the four items together without rewriting historical acceptance evidence.

Non-goals for this plan:

- No arbitrary shell/Docker/compose/path control through Manager API.
- No broad fleet/Kubernetes/multi-site support.
- No AI parser generation.
- No remote Review/quality metadata promoting local verified/validated state.
- No lossy filtering/reduction defaults.

---

## Phase 1 — Package/install/upgrade/rollback drill

### Task 1.1: Define the release artifact manifest contract

**Objective:** Make the release artifact contents explicit and testable before changing packagers.

**Files:**
- Create: `src/sc4s_manager/packaging.py`
- Create: `tests/test_release_packaging.py`
- Modify: `docs/runbooks/` only if a release artifact runbook already exists; otherwise create `docs/runbooks/release-artifact.md`

**Implementation notes:**

Add a pure-Python manifest builder that returns a typed dictionary, not a tarball yet:

```python
REQUIRED_ARTIFACT_PATHS = [
    "src/sc4s_manager/app.py",
    "src/sc4s_manager/control.py",
    "deploy/systemd/sc4s-manager.service",
    "deploy/systemd/sc4s-manager-control.service",
    "deploy/systemd/sc4s-manager-control.socket",
    "deploy/install/install.sh",
    "deploy/upgrade/upgrade.sh",
    "frontend/dist/index.html",
]
```

The manifest must include:

- `version`
- `git_commit`
- `created_at`
- `paths[]` with `path`, `size_bytes`, `sha256`
- `frontend_dist_present`
- `missing_required_paths[]`

**Tests:**

- `test_release_manifest_reports_missing_frontend_dist_without_building_it`
- `test_release_manifest_contains_systemd_control_daemon_units`
- `test_release_manifest_does_not_include_secret_values`

**Commands:**

```bash
./scripts/test.sh tests/test_release_packaging.py
```

Expected: new tests pass after implementation.

### Task 1.2: Add an explicit frontend build/package step

**Objective:** Ensure install/upgrade scripts never run hidden frontend builds while the release artifact can require prebuilt `frontend/dist`.

**Files:**
- Modify: `scripts/build_frontend.sh`
- Create: `scripts/build_release_artifact.py`
- Modify: `tests/test_packaging_foundations.py`
- Modify: `tests/test_release_packaging.py`

**Implementation notes:**

`build_release_artifact.py` should:

1. accept `--version` and `--output-dir`;
2. fail if `frontend/dist/index.html` is absent unless `--allow-missing-frontend` is explicitly passed for test-only dry runs;
3. call the manifest builder;
4. write `manifest.json` beside the tarball;
5. create `sc4s-manager-<version>.tar.gz` with deterministic root directory `sc4s-manager/`.

Do **not** run `npm install`, `npm ci`, or `npm run build` from install/upgrade scripts.

**Tests:**

- artifact builder fails cleanly when frontend dist is missing;
- artifact builder includes deploy units and Python source;
- dry-run install/upgrade tests still prove no `npm` invocation.

**Commands:**

```bash
./scripts/test.sh tests/test_packaging_foundations.py tests/test_release_packaging.py
```

### Task 1.3: Add package/install validator skeleton

**Objective:** Add a validator that can be run on a disposable host/root and record pass/fail evidence.

**Files:**
- Create: `scripts/validate_package_install.py`
- Create: `tests/test_package_install_validator.py`
- Create: `docs/acceptance/package-install-template.json`

**Implementation notes:**

Validator modes:

- `--artifact <tar.gz>`
- `--workdir <path>`
- `--dry-run` for CI-safe checks
- `--evidence-out <json>`

Evidence JSON fields:

- `ok`
- `version`
- `artifact_sha256`
- `install.started_at`, `install.finished_at`, `install.ok`
- `upgrade.ok`, `rollback.ok`
- `service_state.manager`, `service_state.control_daemon`
- `state_preservation.imports`, `state_preservation.backups`, `state_preservation.audit`
- `redaction.findings[]`
- `commands[]` with redacted argv/stdout/stderr summaries

Dry-run validator should prove artifact structure and script syntax only; live mode should be allowed to call systemd in a disposable VM/LXC.

**Commands:**

```bash
./scripts/test.sh tests/test_package_install_validator.py
python3 scripts/validate_package_install.py --dry-run --workdir /tmp/sc4s-manager-package-drill --evidence-out /tmp/sc4s-package-dry-run.json
```

### Task 1.4: Document live install/upgrade/rollback drill

**Objective:** Make the human/lab drill reproducible and evidence-backed.

**Files:**
- Create: `docs/runbooks/install-upgrade-rollback-drill.md`
- Modify: `docs/roadmap/next-release-roadmap.md` only to link this implementation plan, not to mark the blocker done.

**Runbook must include:**

- prerequisites for disposable VM/LXC;
- snapshot/rollback boundary;
- artifact build command;
- clean install command;
- upgrade command from current pilot layout;
- rollback command;
- service readback commands;
- expected evidence path under `docs/acceptance/package-install-<timestamp>.json`;
- redaction checklist.

**Verification:**

```bash
python3 scripts/validate_package_install.py --dry-run --workdir /tmp/sc4s-manager-package-drill --evidence-out /tmp/sc4s-package-dry-run.json
./scripts/test.sh tests/test_release_packaging.py tests/test_package_install_validator.py
```

---

## Phase 2 — Runtime-health dashboard v1

### Task 2.1: Add typed runtime state models and parser helpers

**Objective:** Convert existing `/api/stats`, control `status`, control `metrics`, logs, and listener checks into a stable runtime-state contract.

**Files:**
- Create: `src/sc4s_manager/runtime_state.py`
- Create: `tests/test_runtime_state.py`
- Modify: `src/sc4s_manager/app.py`

**Contract shape:**

```json
{
  "ok": true,
  "generated_at": "ISO-8601",
  "manager": {"version": "...", "health": "ok"},
  "control_daemon": {"ok": true, "provider": "unix_socket"},
  "sc4s": {"running": true, "status": "running", "health": "healthy", "image": "...", "image_version": "...", "supported_version": "3.43.0", "version_drift": false},
  "listeners": [{"protocol": "tcp", "port": 514, "desired": true, "live": true, "bind": "0.0.0.0"}],
  "counters": [{"name": "...", "component": "source|parser|destination|unknown", "metric": "processed", "value": 123}],
  "destinations": [{"id": "default_hec", "kind": "splunk_hec", "written": 0, "dropped": 0, "queued": null}],
  "warnings": [{"severity": "warning", "code": "version_drift", "message": "..."}],
  "redaction": {"secrets_present": false}
}
```

Do not remove `/api/stats`; add `/api/runtime/state` and keep `/api/stats` as compatibility until later cleanup.

**Tests:**

- metrics parser handles representative `syslog-ng-ctl stats` rows;
- HEC token/URL secrets are redacted;
- control-daemon failure becomes `control_daemon.ok=false`, not HTTP 500;
- version drift warning triggers on unsupported running image label.

### Task 2.2: Extend the control daemon with listener and bounded log-warning readback

**Objective:** Give runtime-state enough live input without broadening the control surface dangerously.

**Files:**
- Modify: `src/sc4s_manager/control.py`
- Modify: `tests/test_control.py`
- Modify: `src/sc4s_manager/runtime_state.py`

**Allowed actions to add:**

- `listeners`: fixed `ss`/`netstat` equivalent inside the SC4S container or host namespace, returning only parsed listener rows;
- `warnings`: bounded `docker logs --tail N` parse for warning/error/fallback terms; keep max lines <= 500.

Do **not** accept arbitrary command, container, path, or log filter parameters.

**Tests:**

- unsupported action still rejected;
- `listeners` ignores caller-supplied command/path;
- `warnings` clamps requested line count;
- audit record is written for new actions.

### Task 2.3: Add frontend runtime API client and Dashboard cards

**Objective:** Surface saved/staged/applied/live/Splunk-proven distinctions on the dashboard.

**Files:**
- Create: `frontend/src/api/runtime.ts`
- Create: `frontend/src/api/runtime.test.ts`
- Modify: `frontend/src/routes/Dashboard.tsx`
- Modify: `frontend/src/routes/UserJourneyCoverage.test.tsx` if dashboard coverage text changes.

**UI cards:**

- Manager/control daemon status;
- SC4S process/image/version drift;
- live listeners vs desired ports;
- source/parser/destination counter summary;
- destination warnings/drops/queued/written;
- recent runtime warnings/errors;
- explicit note: “Saved config is not live proof; use marker replay/Splunk readback for proof.”

**Commands:**

```bash
cd frontend && npm test -- --run Dashboard runtime
cd frontend && npm run build
./scripts/test.sh tests/test_runtime_state.py tests/test_control.py
```

### Task 2.4: Add marker counter-delta evidence capture

**Objective:** Prove counters change around a marker send without relying on screenshots alone.

**Files:**
- Create: `scripts/capture_runtime_counter_delta.py`
- Create: `tests/test_runtime_counter_delta.py`
- Modify: `docs/acceptance/AGENTS.md` only if a new evidence class needs explicit redaction rules.

**Implementation notes:**

Script steps:

1. GET `/api/runtime/state` before marker;
2. call existing `scripts/send_marker_event.py` or accept `--marker-command` in live mode;
3. GET `/api/runtime/state` after marker;
4. write evidence JSON with before/after counters and redacted request metadata.

Dry-run tests should use fixture JSON only.

---

## Phase 3 — Source onboarding and parser preview workflow

### Task 3.1: Add sample event classifier

**Objective:** Safely classify representative samples without storing/promoting them.

**Files:**
- Create: `src/sc4s_manager/sample_preview.py`
- Create: `tests/test_sample_preview.py`
- Modify: `src/sc4s_manager/app.py`

**Endpoint:**

`POST /api/samples/classify`

Request:

```json
{"sample": "<raw event>", "source_hint": "optional", "transport": "udp|tcp|tls|unknown"}
```

Response fields:

- `ok`
- `format_hints[]`: `rfc3164`, `rfc5424`, `cef`, `leef`, `json`, `csvish`, `raw_headerless`, `multiline`, `boundary_ambiguous`
- `timestamp_hint`
- `host_hint`
- `redacted_sample_preview`
- `stored`: always false unless a later explicit fixture-save endpoint is added
- `limitations[]`

**Tests:**

- Cisco ASA syslog sample classifies as syslog-ish and Cisco-ish;
- JSON sample classifies as JSON;
- multiline sample reports boundary ambiguity;
- secret-looking strings are redacted;
- classifier does not write files.

### Task 3.2: Add parser/pack match preview

**Objective:** Show likely parser/pack path with reasons and confidence without claiming validation.

**Files:**
- Modify: `src/sc4s_manager/sample_preview.py`
- Modify: `tests/test_sample_preview.py`
- Modify: `src/sc4s_manager/app.py`

**Endpoint:**

`POST /api/samples/preview`

Response fields:

- `classification`
- `candidate_matches[]` with `pack_id`, `vendor_product`, `reason`, `confidence`, `requires_operator_review`
- `expected_metadata` with `index`, `sourcetype`, `source`, `host`, `timestamp_policy`
- `next_actions[]`
- `validated`: always false unless backed by live validation evidence ID

**Initial matching strategy:**

- Use built-in `SOURCE_CATALOG` and local packs inventory.
- Cisco ASA recogniser can match `%ASA-`/`%FTD-` style markers to `cisco_asa`.
- Unknown/fallback case must return no validated match and a clear next action.

### Task 3.3: Add Onboarding Preview UI route

**Objective:** Give operators a paste/upload preview flow that leads with risk and next action.

**Files:**
- Create: `frontend/src/api/samples.ts`
- Create: `frontend/src/api/samples.test.ts`
- Create: `frontend/src/routes/OnboardingPreview.tsx`
- Create: `frontend/src/routes/OnboardingPreview.test.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`
- Modify: `frontend/src/lib/navigation.ts`

**UI requirements:**

- textarea paste area plus optional source hint;
- classify/preview button;
- visible redaction warning;
- matched parser/pack candidates with “preview only — not applied, not validated” status;
- expected Splunk metadata panel;
- fallback/no-match panel with next actions;
- no auto-save of sample content.

**Commands:**

```bash
cd frontend && npm test -- --run OnboardingPreview samples navigation
cd frontend && npm run build
./scripts/test.sh tests/test_sample_preview.py
```

### Task 3.4: Add fixture candidate export only as explicit opt-in

**Objective:** Convert approved samples into fixture candidates without accidental storage.

**Files:**
- Modify: `src/sc4s_manager/sample_preview.py`
- Modify: `tests/test_sample_preview.py`
- Create: `docs/runbooks/sample-fixture-candidates.md`

This is optional for the first implementation pass. If added, require:

- explicit `POST /api/samples/fixture-candidate`;
- `approved_for_storage: true` in request;
- sanitized filename;
- storage under Manager state candidate area, not active pack fixtures;
- response says candidate material is unreviewed and not validation evidence.

---

## Phase 4 — SecHub Library import reliability and trust semantics

### Task 5.1: Add Library source health model

**Objective:** Show live fetch status for catalogue, manifest, entries, bundles, checksums, and sidecars.

**Files:**
- Modify: `src/sc4s_manager/library.py`
- Modify: `tests/test_library.py`
- Modify: `src/sc4s_manager/app.py`

**Endpoint:**

`GET /api/library/source-health?source_id=official`

Response fields:

- `source_id`
- `checks[]` with `name`, `url`, `ok`, `status_code`, `elapsed_ms`, `content_type`, `size_bytes`, `sha256`, `error_code`, `message`
- `catalogue.entry_count`
- `manifest.download_count`
- `sample_entry.ok`
- `sample_bundle.ok`
- `sidecars[]` if the contract exposes sidecars
- `overall_ok`

Use the real Manager fetch functions so Cloudflare/bot-policy/header mismatches are visible to Manager, not only curl.

### Task 5.2: Classify fetch/import errors into operator actions

**Objective:** Replace generic Python/HTTP errors with stable error codes and next actions.

**Files:**
- Modify: `src/sc4s_manager/library.py`
- Modify: `tests/test_library.py`
- Modify: `frontend/src/api/library.ts`
- Modify: `frontend/src/routes/Library.tsx`

**Error codes:**

- `dns_failure`
- `http_forbidden_or_bot_policy`
- `http_not_found`
- `manifest_missing`
- `checksum_mismatch`
- `bundle_too_large`
- `unsafe_archive_member`
- `schema_contract_mismatch`
- `timeout`
- `unknown_fetch_error`

Each code must include a short operator-facing `next_action`.

**Tests:**

- DNS/socket error maps to `dns_failure`;
- HTTP 403 maps to bot-policy/client-header guidance;
- missing manifest download maps to `manifest_missing`;
- checksum mismatch remains blocking;
- unsafe archive path remains blocking and does not extract.

### Task 5.3: Strengthen local verified-state gate

**Objective:** Prove remote metadata cannot set local `is_verified` or validated status.

**Files:**
- Modify: `src/sc4s_manager/library.py`
- Modify: `src/sc4s_manager/catalogue.py` if local catalogue summaries expose verified flags
- Modify: `tests/test_library.py`
- Modify: `tests/test_catalogue.py` if catalogue display changes

**Rule:**

Local `is_verified=true` or local `validated_pack` can only be emitted when a locally generated validation JSON includes all claimed required stages, for example:

- `syslog_ng_syntax.ok=true`
- `runtime_pack_validation.ok=true`
- `splunk_readback.ok=true` when Splunk-proven is claimed

Remote Review, quality status, validation harness metadata, prose, dates, filenames, and evidence-looking paths are advisory only.

### Task 5.4: Add Library source inventory UI health panel

**Objective:** Let an operator see whether the configured SecHub source contract is healthy and why not.

**Files:**
- Modify: `frontend/src/api/library.ts`
- Modify: `frontend/src/routes/Library.tsx`
- Create/modify: `frontend/src/routes/Library.test.tsx`

**UI requirements:**

- source cards show last sync and live health;
- per-contract check rows for catalogue, manifest, entries, bundle, checksums, sidecars;
- controlled errors show code and next action;
- trust warning: “remote labels are advisory; local verification requires local validation evidence.”

**Commands:**

```bash
./scripts/test.sh tests/test_library.py tests/test_catalogue.py
cd frontend && npm test -- --run Library library
cd frontend && npm run build
```

---

## Phase 5 — Integrated evidence and release decision support

### Task 5.1: Add an implementation evidence checklist

**Objective:** Record what must be captured after code lands without pretending evidence already exists.

**Files:**
- Create: `docs/acceptance/next-release-items-1-2-3-5-checklist.md`

Checklist sections:

- package/install dry-run evidence;
- live clean install evidence;
- upgrade evidence;
- rollback evidence;
- `/api/runtime/state` live readback;
- dashboard screenshot/browser artifact;
- counter delta evidence before/after marker;
- sample preview good Cisco ASA path;
- sample preview fallback path;
- Library source-health live fetch;
- curated pack import/apply readback;
- deliberately broken source controlled error;
- trust-semantics negative test result;
- redaction review.

### Task 5.2: Wire validators into the existing acceptance gate without making them fake-pass

**Objective:** Add flags that fail when evidence is absent, but keep existing V1 gate behavior stable.

**Files:**
- Modify: `scripts/validate_acceptance_evidence.py`
- Modify: `tests/test_acceptance_evidence.py`

Candidate flags:

```bash
--require-package-drill
--require-runtime-dashboard
--require-source-preview
--require-library-health
```

Default behavior must not require new evidence. Each new flag must fail with a clear missing-evidence message until real evidence JSON exists.

### Task 5.3: Full validation command set before claiming done

Run after implementation:

```bash
./scripts/test.sh
cd frontend && npm test -- --run && npm run build
python3 scripts/validate_acceptance_evidence.py --require-final --require-e2e-ui --require-crud-journeys
python3 scripts/validate_acceptance_evidence.py --require-package-drill --require-runtime-dashboard --require-source-preview --require-library-health
```

The second validator is expected to fail until live/lab evidence is captured. Do not mark the roadmap blockers complete until it passes with timestamped evidence under `docs/acceptance/`.

---

## Implementation ownership split

Recommended subagent lanes:

- **Lane A — Packaging/release hygiene:** Phase 1 and Phase 5 validator flags.
- **Lane B — Runtime truth:** Phase 2 backend/control/frontend dashboard.
- **Lane C — Source preview:** Phase 3 backend/frontend sample workflow.
- **Lane D — Library reliability/trust:** Phase 4 backend/frontend Library health and trust semantics.

Merge order: A → B → C → D → integrated validator/evidence pass.

## Definition of done

This implementation plan is complete only when:

- code/tests for all four blockers are merged;
- `./scripts/test.sh` passes;
- frontend tests/build pass;
- existing final/E2E/CRUD acceptance still passes;
- new evidence-gate flags exist and fail clearly before evidence;
- live lab evidence is captured and the new evidence-gate flags pass;
- secrets/tokens/proxy headers are absent from generated evidence and UI artifacts;
- roadmap text is updated from “planned” to “implemented/evidenced” only after real readback.
