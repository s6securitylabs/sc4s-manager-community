# SC4S Manager Product Requirements

## 1. Purpose

SC4S Manager is the private operator control plane for SC4S-compatible ingestion environments. It lets operators import reviewed packs, validate them locally, preview generated changes, apply configuration safely, observe runtime health, and roll back when needed.

The Manager is not the catalogue. It consumes SC4S Library/SecHub artifact sources as untrusted input and turns them into validated local configuration only after operator-controlled checks pass.

## 2. Problem statement

SC4S is powerful but operationally file-centric. Enterprise operators need a safer path for source onboarding, parser validation, evidence capture, and controlled changes than editing raw config directly on a host. They also need a clear separation between externally shared pack knowledge and local environment-specific deployment decisions.

SC4S Manager solves this by providing a secure UI/API and narrow control plane around import, validation, preview, apply, observability, evidence, and rollback.

The active market-research driver is documented in `docs/roadmap/product-market-research-and-key-drivers.md`. It frames the durable product wedge as SC4S-native log-source lifecycle management: source onboarding, parser visibility, Splunk metadata correctness, runtime health, fallback/lastchance triage, TA/CIM readiness, safe deployment, rollback, and evidence. Apto's SC4S critique adds a second driver: close the limitations that push enterprises toward Cribl, especially scale visibility, resilience/persistent buffering, multi-destination routing, reduction/transformation ergonomics, and richer pipeline observability. Roadmap work should preserve this focus and avoid drifting into a full SIEM or generic telemetry platform before the Splunk-syslog lane is credible.

## 3. Goals

- Provide an operator UI/API for saving staged SC4S source onboarding changes and operating SC4S safely.
- Import packs from the SC4S Library or local files.
- Validate pack schema, test events, parser artifacts, and generated configuration locally.
- Preview all generated changes before apply.
- Apply changes through a constrained control daemon, not direct web access to host/Docker primitives.
- Maintain backups and rollback paths for risky changes.
- Show runtime state, counters, warnings, and destination health.
- Support resilient buffering, retry/backpressure visibility, and failure-mode reporting for Splunk HEC and saved downstream routes.
- Support controlled multi-destination routing and policy-driven reduction/transformation where it can be previewed, validated, audited, and rolled back.
- Capture evidence for customer handoff, acceptance, and troubleshooting.
- Redact secrets in responses, diffs, logs, reports, and exports.

## 4. Non-goals

- Hosting the public SecHub catalogue.
- Publishing community pack submissions.
- Treating SecHub trust labels as deployment approval.
- Providing unrestricted shell, host, or Docker control through the web UI.
- Silently dropping events or enabling lossy reduction by default.
- Replacing Splunk or SC4S; the Manager configures, validates, and observes them.

## 5. Primary users

- **SC4S operators:** import packs, save staged source changes, apply/rollback changes.
- **SOC engineers:** validate sourcetypes, field extraction, event families, and Splunk readiness.
- **Platform engineers:** operate the Manager service, SC4S runtime, auth proxy, and deployment lifecycle.
- **Maintainers:** develop pack lifecycle, catalogue import, validation, and control-plane features.

## 6. Product boundary with SC4S Library and SecHub

SC4S Library is the Manager-facing pack catalogue and artifact source. SecHub is the public discovery surface. SC4S Manager is the local operating plane.

Manager responsibilities:

- fetch configured Library catalogue sources
- display trust/quality labels without overstating them
- download pack bundles
- verify checksum/signature metadata
- validate pack schema and fixtures locally
- preview generated changes
- apply only after operator approval
- store local import/deployment state and evidence

SC4S Library/SecHub responsibilities:

- maintain canonical pack metadata and evidence
- enforce submission/manual-PR workflow
- generate catalogue JSON and downloadable bundles
- define trust labels and download eligibility

A SC4S Library pack can be curated or validation-backed and still fail local Manager validation if environment-specific settings, SC4S version, transports, destinations, or customer constraints do not match.

## 7. Core workflows

### 7.1 Runtime visibility

The Manager must show desired configuration separately from live runtime state:

- SC4S container health and image/version
- Manager/control daemon health
- listener sockets and saved source settings
- syslog-ng counters for sources, parsers, filters, and destinations
- HEC/syslog destination written/dropped/queued/processed counters
- recent parser/config warnings
- last validation/apply/rollback result

### 7.2 Pack import

Import from SC4S Library or local bundle:

1. Fetch or select bundle.
2. Verify checksum/signature metadata.
3. Validate `pack.json` schema.
4. Validate fixture semantics and required evidence fields.
5. Inspect parser/config artifacts for unsafe/default-drop behavior.
6. Record provenance, trust labels, and limitations.
7. Store pack as local draft/available, not automatically deployed.

### 7.3 Source configuration

1. Select imported or built-in pack.
2. Save source-specific listener and destination settings as staged changes.
3. Generate env/parser/Splunk artifacts.
4. Present diff preview.
5. Run validation checks.
6. Require operator confirmation.
7. Backup current state.
8. Apply via control daemon.
9. Run post-apply checks.
10. Record audit/evidence.

### 7.4 Validation and evidence

Validation should support:

- SC4S config syntax validation
- parser/config artifact validation
- replaying fixture or marker events through real listeners where safe
- listener/destination counter checks
- Splunk indexed-event proof where credentials are configured
- exportable evidence bundle with timestamps, pack version, source version, and validation result

### 7.5 Rollback

Before mutating operations, the Manager must create enough backup state to restore the last known-good configuration. Rollback should be visible, auditable, and followed by health checks.

## 8. Security and safety requirements

- Web/API process runs non-root.
- Web/API process has no Docker socket access.
- Mutating operations use a narrow local Unix-socket control daemon.
- The control daemon exposes fixed actions, not arbitrary command execution.
- Secrets are never returned raw through API/UI/diffs/logs/reports.
- Authenticated identity is included in audit records where available.
- Manual/emergency access is auditable and clearly marked.
- Importing a pack cannot apply it automatically.
- Default packs must not silently drop events or enable lossy reduction.

## 9. Data model requirements

Manager-local state should distinguish:

- Library catalogue entry
- downloaded bundle metadata
- verified local import
- draft source configuration
- applied source configuration
- validation evidence
- backup/rollback artifact
- audit record

This separation prevents catalogue metadata from being confused with deployed state.

## 10. API/UI requirements

The UI must prioritize operator questions before raw metadata:

- What is this source/pack?
- Why would I use it?
- When is it appropriate or unsafe?
- Where does it send/listen/store data?
- How do I validate it?
- What will change if I apply it?
- How do I roll back?

Metadata can follow, but must not be the primary experience.

## 11. Acceptance criteria

A Manager release is deployment-ready when:

- install/upgrade/rollback runbooks are current
- local test suite passes from a clean checkout
- API acceptance probes pass
- authenticated browser route evidence exists
- pack import from the SC4S Library works for at least one curated bundle
- checksum verification and local validation are enforced before apply
- apply creates backup/audit evidence
- rollback drill evidence exists
- Splunk indexed-event proof exists where required for release scope
- no secrets appear in API output, diffs, logs, reports, or test artifacts

## 12. Development and validation

Canonical local workspace:

```text
/home/jarvis/work/sc4s-manager
```

Canonical repository:

```text
s6securitylabs/sc4s-manager
```

Canonical test bootstrap:

```bash
./scripts/test.sh
```

Developers should not use `10.10.1.183:/opt/sc4s-manager` as the active development workspace unless explicitly directed. It is a runtime/test host, not the canonical working tree.

## 13. Open decisions

- Whether imported SecHub bundles require signatures in v1 or SHA256-only is acceptable until release.
- Which validation checks are mandatory before apply vs warning-only.
- Which parts of community/candidate lifecycle belong in Manager UI before public SecHub release.
- How much Splunk read-back evidence is required for non-production deployments.
- Which market-driver items become v1 pilot blockers versus v1.x roadmap items: runtime-health dashboard, source onboarding/parser preview, fallback/lastchance triage, Splunk indexed proof, TA/CIM readiness evidence, commercial packaging, and enterprise approval/RBAC.
