# SC4S Manager catalogue, pack, and upstream-sync requirements

Date: 2026-05-27
Status: Draft requirements and gap-analysis baseline
Scope: SC4S built-in catalogue, SecHub Resources curated packs, pack/log-conf artifact model, upstream sync, SOC-engineer feature expectations

> **2026-07-13 boundary amendment:** ADR 0002 governs this roadmap. “Pack,” “release,” “deployment bundle,” and “product” language below refers only to SC4S Library compatibility/import behavior unless explicitly labelled as a Resources product bundle or Product TA. Manager does not own, package, install, apply, or roll back Product TA TGZs. Canonical product and Library publication belongs to Forgejo `s6-infra/sechub-resources`; Manager's checked-in packs are pinned fixtures.

## 1. Executive summary

SC4S Manager should not treat upstream SC4S docs, GitHub issues, or parser snippets as release-ready content. They are source material. The product needs a curated catalogue layer that merges:

1. **SC4S built-ins** — parsers, filters, postfilters, destinations, source docs, and examples already shipped by upstream SC4S.
2. **SecHub Resources curated packs** — our curated, tested, community-submission-friendly pack/log-conf sets with richer parsing, filtering, log reduction, Splunk knowledge objects, fixtures, validation evidence, and operational guidance.

The merged catalogue must let operators search both worlds together while preserving provenance, version, support status, and override/extension relationships. SC4S Manager should be able to stay in sync with the original SC4S repo while continuing to ship higher-quality packs for SOC use cases.

The strategic positioning is:

- Upstream SC4S provides useful baseline coverage.
- SC4S Manager adds local compatibility validation, reduction controls, SOC-friendly field semantics, evidence inspection, selective SC4S apply, and rollback. Product deployment completeness and Product TA releases remain in canonical Resources product bundles.
- Functional config remains real `.conf` files so future community submissions look like ordinary SC4S/syslog-ng/Splunk artifacts, not opaque JSON strings or generated-only magic.

## 2. Principles

1. **Corpus is source, not product.**
   - Upstream docs/issues/examples are research inputs only.
   - No issue-body parser or copied snippet ships without curation, review, testing, provenance, and license/attribution checks.

2. **Config is files.**
   - Parser, filter, postfilter, selector, props, transforms, eventtypes, tags, and related rules are stored as explicit files.
   - `pack.json` describes and references artifacts; it must not become a custom parser language.

3. **Provenance is never hidden.**
   - Every catalogue item declares origin: `sc4s-inbuilt`, `sc4s-inbuilt-lite`, `sechub-resources-pack`, or later `community-extra`.
   - Items declare upstream commit/version, SecHub Resources SC4S pack version, and relationship to upstream.

4. **SC4S Manager may extend, not silently replace.**
   - If SC4S ships a basic Cisco parser and SC4S Manager ships a richer Cisco pack, the merged catalogue must show the relationship explicitly.
   - Operators must be able to tell what comes from upstream and what comes from SC4S Manager.

5. **SOC outcomes matter more than parser existence.**
   - A parser that merely assigns a sourcetype is not enough.
   - A SOC-ready pack should support detection, triage, reduction, field consistency, Splunk CIM alignment where appropriate, and validation evidence.

6. **Stay upstream-compatible.**
   - Keep artifact layout close to SC4S/syslog-ng conventions.
   - Avoid proprietary config shapes unless they generate reviewable `.conf` artifacts and remain optional metadata.

## 3. Source classes

### 3.1 `sc4s-inbuilt`

Definition: capabilities shipped in upstream SC4S full container/package.

Examples:

- `package/etc/conf.d/conflib/syslog/app-*.conf`
- `package/etc/conf.d/conflib/netsource/app-*.conf`
- `package/etc/conf.d/conflib/post-filter/app-*.conf`
- `package/etc/conf.d/destinations/*`
- `docs/sources/vendor/**/*.md`

Release behaviour:

- Indexed/catalogued by SC4S Manager.
- Not vendored into SC4S Manager release bundles unless explicitly imported/curated.
- Used to detect coverage, gaps, duplicates, extension opportunities, and upstream changes.

### 3.2 `sc4s-inbuilt-lite`

Definition: capabilities shipped in upstream SC4S Lite/addon trees.

Examples:

- `package/lite/etc/addons/*/*.conf`

Release behaviour:

- Catalogued separately from full built-ins.
- Merged into operator search results with clear Lite provenance.

### 3.3 `sechub-resources-pack`

Definition: curated SecHub Resources SC4S pack/log-conf sets.

Examples:

- `packs/commvault_commcell/pack.json`
- `packs/<pack>/sc4s/**/*.conf`
- `packs/<pack>/splunk/default/*.conf`
- `packs/<pack>/test-events/*`

Release behaviour:

- Releaseable artifacts.
- Must pass pack schema validation, fixture tests, export tests, syntax validation where possible, and evidence requirements.

### 3.4 Future: `community-extra`

Definition: external submissions that follow SecHub Resources SC4S pack/artifact contract but are not yet promoted to core extras.

Release behaviour:

- Accepted through review pipeline.
- Can be marked experimental/community until fully validated.

## 4. Required artifact layout

Canonical pack layout:

```text
packs/<pack_id>/
  pack.json
  README.md
  sc4s/
    app_parsers/
      syslog/
        app-<pack_id>.conf
      raw/
      cef/
      leef/
      json/
    filters/
      f-<pack_id>-<rule>.conf
    postfilters/
      app-postfilter-<pack_id>-<rule>.conf
    selectors/
      sc4s-lp-<pack_id>-<destination>.conf
    destinations/
      d-<pack_id>-<destination>.conf
    context/
      *.csv
      *.conf
  splunk/
    default/
      props.conf
      transforms.conf
      eventtypes.conf
      tags.conf
      macros.conf
      savedsearches.conf
    metadata/
      default.meta
  test-events/
    *.log
    *.json
    *.pcap
  tests/
    README.md
  docs/
    source-notes.md
    validation-evidence.md
```

Rules:

- Functional SC4S/syslog-ng and Splunk configuration lives in `.conf`/`.csv` files.
- `pack.json` references every release artifact through `export_artifacts`.
- Reduction/filtering implementation lives in postfilter/filter `.conf` files.
- Fixtures declare boundaries, multiline behaviour, timestamp policy, expected counts, and expected family/sourcetype outcomes.

### 4.1 Naming convention guidance

Naming should stay close to upstream SC4S conventions even when the exact name feels less elegant. Upstream convention encodes the application/parser family in the filename:

- `app-syslog-<vendor_product>.conf`
- `app-raw-<vendor_product>.conf`
- `app-cef-<vendor_product>.conf`
- `app-leef-<vendor_product>.conf`
- `app-json-<vendor_product>.conf`
- `app-netsource-<vendor_product>.conf`
- `app-postfilter-<vendor_product>-<rule>.conf`

For SecHub Resources SC4S packs, prefer convention over aesthetics:

- If a file defines a syslog application path, use `app-syslog-<pack_id>.conf`.
- If it defines a raw/headerless application path, use `app-raw-<pack_id>.conf`.
- If it deliberately combines multiple application paths in one file, use either:
  - separate conventional files where practical, or
  - `app-<pack_id>.conf` only when a combined file is intentional and documented.

`app-commvault_commcell.conf` is logically readable, but it loses the upstream parser-family signal. If the Commvault pack contains syslog, raw, and network-source application blocks in one file, the cleaner long-term approach is probably to split into conventional files or explicitly document it as a combined app file. Do not let naming purity block useful work, but make the export manifest and catalogue precise about what application topics each file contains.

## 5. Catalogue data model requirements

Each catalogue entry should include:

```json
{
  "id": "cisco_asa",
  "display_name": "Cisco ASA",
  "vendor": "Cisco",
  "product": "ASA",
  "origins": ["sc4s-inbuilt", "sechub-resources-pack"],
  "effective_origin": "sechub-resources-pack",
  "relationship_to_upstream": "extends_upstream",
  "status": "curated",
  "upstream": {
    "repo": "splunk/splunk-connect-for-syslog",
    "commit": "...",
    "sc4s_version": "...",
    "paths": []
  },
  "sc4s_manager": {
    "pack_version": "...",
    "schema_version": "0.1",
    "paths": []
  },
  "capabilities": {
    "parser": true,
    "filters": true,
    "postfilters": true,
    "log_reduction": true,
    "splunk_props_transforms": true,
    "cim_mapping": true,
    "fixtures": true,
    "syntax_validated": true,
    "splunk_ingestion_validated": false
  }
}
```

Relationship values:

- `upstream_only`
- `new_pack`
- `extends_upstream`
- `overrides_upstream`
- `adds_postfilters`
- `adds_reduction_rules`
- `adds_splunk_knowledge`
- `docs_only`
- `deprecated`

## 6. Feature matrix

### 6.1 Catalogue and upstream sync

- Requirement: Catalogue upstream SC4S built-ins by commit/version.
  - Status: Partial spike exists in local cache.
  - Gap: Needs committed script, stable JSON output, tests.

- Requirement: Catalogue SC4S Lite/addon configs separately.
  - Status: Partial spike exists.
  - Gap: Need provenance and dedupe rules.

- Requirement: Merge upstream and SecHub Resources curated packs into one queryable API.
  - Status: Not implemented.
  - Gap: Add data model, API, frontend views.

- Requirement: Detect upstream additions, deletions, and parser changes between SC4S versions.
  - Status: Not implemented.
  - Gap: Need diff job/script and report format.

- Requirement: Support pinning SecHub Resources SC4S pack compatibility to SC4S runtime versions.
  - Status: Partially present through supported runtime spec.
  - Gap: Need per-pack compatibility fields and tests.

- Requirement: Never silently overwrite upstream built-ins.
  - Status: Policy defined here.
  - Gap: Enforce in catalogue merge logic and UI labels.

### 6.2 Pack and artifact packaging

- Requirement: Keep parser/filter/postfilter/rule content as `.conf` files.
  - Status: Policy defined; current Commvault mostly follows it.
  - Gap: Need canonical directories for filters/postfilters/selectors and schema constraints.

- Requirement: Export bundles include all artifacts declared in `pack.json`.
  - Status: Partial via `export_artifacts`.
  - Gap: Current Commvault manifest references a deleted parser path; fix before further work.

- Requirement: Artifacts include checksums in export manifest.
  - Status: Contract says this should exist.
  - Gap: Verify implementation and tests.

- Requirement: Community submissions can be reviewed as file diffs.
  - Status: Not formalized.
  - Gap: Add contribution template and validation command.

### 6.3 Parser quality

- Requirement: Support upstream-equivalent baseline parsing.
  - Status: For built-ins, catalogue only; for Commvault, custom parser exists.
  - Gap: Need capability comparison per pack.

- Requirement: Support richer parsing than upstream when upstream is basic.
  - Status: Goal defined.
  - Gap: Need quality tiers and tests for field extraction completeness.

- Requirement: Classify multiple event families per source.
  - Status: Present in pack contract.
  - Gap: Need runtime parser validation against all families.

- Requirement: Preserve correct sourcetype/source/index mapping.
  - Status: Present in pack metadata and export artifacts.
  - Gap: Need automated post-ingest proof where Splunk is available.

- Requirement: Handle timestamp fields/timezones explicitly.
  - Status: Present in pack fixture metadata.
  - Gap: Need more negative tests and source-version-specific cases.

- Requirement: Validate syslog-ng syntax in the target SC4S runtime.
  - Status: Control-plane validation exists generally.
  - Gap: Need per-pack validation command.

### 6.4 Log reduction, filtering, and routing

- Requirement: Support pre-index log reduction.
  - Status: SC4S supports postfilter + `r_set_dest_splunk_null_queue`; SC4S Manager schema does not yet model it first-class.
  - Gap: Add reduction metadata and `.conf` postfilter artifact convention.

- Requirement: Reduction rules are optional, explicit, and testable.
  - Status: Policy defined here.
  - Gap: Add schema, tests, UI warnings, and counters.

- Requirement: Support filters that route, enrich, or drop without confusing semantics.
  - Status: Some service/source filter generation exists.
  - Gap: Need separate model for selector filters, context filters, postfilters, and drop rules.

- Requirement: Support alternate destinations and SELECT/GLOBAL routing.
  - Status: Some destination support exists.
  - Gap: Need per-pack selectors and safety docs for replacement semantics.

- Requirement: Show estimated/reported ingest reduction impact.
  - Status: Not implemented.
  - Gap: Need before/after counters, sample fixture reduction ratio, and runtime syslog-ng/Splunk metrics.

### 6.5 Splunk knowledge and SOC usability

- Requirement: Include `props.conf` and `transforms.conf` where needed.
  - Status: Present for Commvault.
  - Gap: Need validation/export tests and field-extraction checks.

- Requirement: Include `eventtypes.conf`, `tags.conf`, and CIM-friendly mappings where appropriate.
  - Status: Present for Commvault.
  - Gap: Need CIM mapping metadata and validation checks.

- Requirement: Provide SOC triage fields.
  - Desired fields include actor/user, src/dest, action, outcome, severity, object/resource, policy/rule, signature/event_id, session/request IDs, bytes/counts, device/app version, tenant/site, raw timestamp source.
  - Status: Not formalized.
  - Gap: Add `soc_fields` or `field_contract` metadata and tests.

- Requirement: Provide detection content hooks.
  - Examples: notable event candidates, savedsearches, SPL examples, analytic stories, dashboards.
  - Status: Not implemented.
  - Gap: Decide whether v1 packs include examples only or deployable content.

- Requirement: Provide noise catalogue and recommended reduction presets.
  - Status: Not implemented.
  - Gap: Add optional presets with safety labels and explicit enablement.

- Requirement: Provide validation evidence readable by a SOC engineer.
  - Status: Per-pack evidence prose exists.
  - Gap: Need standardized evidence file with parser results, fixture counts, Splunk proof, and known limitations.

### 6.6 Source documentation and onboarding

- Requirement: Record source configuration steps.
  - Status: Commvault README/runbook exists.
  - Gap: Standardize `docs/source-notes.md` or README sections.

- Requirement: Record source versions and firmware/application log format versions.
  - Status: Present in pack metadata.
  - Gap: Need version compatibility matrix and stale-review policy.

- Requirement: Include sample/test event metadata.
  - Status: Present in pack contract.
  - Gap: Need pcap support and multiline fixture validation expansion.

- Requirement: Include source-side recommended logging settings.
  - Status: Not formalized.
  - Gap: Add section for source verbosity, facility/severity, transport, TLS, timestamps, and timezone.

### 6.7 Safety, validation, and release gates

- Requirement: No secrets in export artifacts.
  - Status: Contract exists.
  - Gap: Need scanner in validation pipeline.

- Requirement: Reject unsafe paths/symlink escapes in exports.
  - Status: Existing hardening work covers this area.
  - Gap: Ensure catalogue/pack additions keep same gates.

- Requirement: Validate pack schema and fixture metadata.
  - Status: Implemented partially.
  - Gap: Current Commvault artifact path mismatch blocks tests.

- Requirement: Validate generated/referenced `.conf` syntax.
  - Status: Not per-pack formalized.
  - Gap: Add runtime validation using pinned SC4S image/version.

- Requirement: Validate Splunk knowledge syntax/behaviour.
  - Status: Not formalized.
  - Gap: Add static checks plus optional Splunk test container/API validation.

- Requirement: Produce release evidence bundles.
  - Status: Acceptance docs exist generally.
  - Gap: Per-pack evidence bundle standard missing.

## 7. SOC-engineer acceptance checklist

A SOC engineer should be able to answer these before trusting a pack:

1. What source/version/log format does this pack support?
2. How do I configure the source to emit compatible logs?
3. What transport/framing/timestamp assumptions exist?
4. What sourcetypes, indexes, and sources will be produced?
5. Which fields are extracted at ingest time and search time?
6. Which fields map to CIM or common SOC semantics?
7. What events are intentionally dropped/reduced, and why?
8. Are reduction rules disabled by default or enabled by default?
9. What is the expected ingestion volume reduction?
10. What important events are guaranteed not to be dropped?
11. What event families are covered, partially covered, or unsupported?
12. What sample events were used for validation?
13. Did syslog-ng syntax validation pass in the target SC4S runtime?
14. Did events actually arrive in Splunk with the expected metadata?
15. What known limitations, vendor-version caveats, or parser edge cases exist?
16. How does this pack differ from upstream SC4S built-in support?
17. If upstream SC4S changes its parser, what happens to this pack?
18. How do I submit improvements or customer samples back?

## 8. Field semantic standards strategy

SC4S Manager should support field semantics in layers rather than betting on one universal schema. Splunk deployments still need CIM-compatible fields; broader/security-data interoperability increasingly points toward OCSF. Elastic ECS is also useful as a reference for cross-SIEM thinking, but it should not be the primary target for a Splunk-first product.

Recommended strategy:

1. **Primary operational target: Splunk CIM/common Splunk field names.**
   - Required because SC4S Manager is currently Splunk/HEC-first.
   - Enables existing Splunk Enterprise Security searches, dashboards, and analyst expectations.
   - Use where applicable; do not force bad CIM mappings for sources that do not fit a CIM data model.

2. **Secondary semantic target: OCSF class/category mapping.**
   - OCSF is an open cybersecurity schema for categories, event classes, data types, and an attribute dictionary.
   - Useful for describing event semantics independently of Splunk implementation.
   - Pack metadata should be able to say, for example, that an event family maps conceptually to OCSF `network_activity`, `http_activity`, `authentication`, or `process_activity`.

3. **Reference/optional target: ECS.**
   - ECS is valuable for cross-platform field concepts and Elastic users.
   - Keep optional unless/until SC4S Manager explicitly expands beyond Splunk.

4. **Input format awareness: CEF/LEEF/vendor schemas.**
   - CEF and LEEF are input/event formats, not complete SOC operating models.
   - Preserve original fields and map them to Splunk/CIM/OCSF concepts where possible.

Proposed pack metadata shape:

```json
{
  "field_contract": {
    "required_fields": ["action", "user", "src", "dest", "severity"],
    "recommended_fields": ["object", "policy", "signature", "session_id"],
    "source_native_fields": ["..."],
    "normalised_fields": ["..."],
    "cim": {
      "data_models": ["Authentication", "Network_Traffic"],
      "tags": ["authentication", "network"]
    },
    "ocsf": {
      "category": "iam",
      "class": "authentication",
      "activity_mapping": {"login": "Logon", "logout": "Logoff"}
    },
    "ecs": {
      "mapping_status": "optional_reference"
    }
  }
}
```

Acceptance rule: a pack does not need perfect CIM/OCSF/ECS mapping to ship, but it must be honest about mapping status: `complete`, `partial`, `not_applicable`, or `unknown`.

## 9. Gaps and likely missed areas

### High priority gaps

1. **Commvault artifact path coherence.**
   - `pack.json` now references `sc4s/app_parsers/syslog/app-commvault_commcell.conf`, matching the committed parser artifact.
   - Keep this validation clean before catalogue merge work proceeds.

2. **No committed upstream catalogue generator.**
   - Local cache proves feasibility, but repo needs script, output contract, tests, and docs.

3. **No merged catalogue API.**
   - Operators cannot yet search upstream built-ins and SecHub Resources curated packs together.

4. **No first-class reduction model.**
   - SC4S supports null-queue postfilters, but SecHub Resources SC4S packs do not yet model optional reduction presets safely.

5. **No quality tier/comparison against upstream.**
   - Need to show why SecHub Resources SC4S pack is better: richer fields, coverage, reductions, Splunk knowledge, tests.

6. **No SOC field contract.**
   - Need explicit expected extracted fields and SOC/CIM mapping expectations.

### Medium priority gaps

1. **No upstream drift monitor.**
   - Need to detect new/changed/deleted upstream parsers and docs on each pinned SC4S release.

2. **No per-pack runtime validation bundle.**
   - Need one command to validate schema, fixtures, syslog-ng syntax, export, and optional Splunk proof.

3. **No community contribution template.**
   - Need a contributor path for `.conf`, fixtures, source docs, and validation evidence.

4. **No known-limitations standard.**
   - SOC users need explicit unsupported event families/source versions.

5. **No volume/reduction estimation workflow.**
   - Need sample-based and runtime-based volume measurements.

6. **No detection/dashboard packaging decision.**
   - Need to decide whether packs ship only parsing/knowledge or also analytic content.

### Lower priority but important later

1. **PCAP replay support.**
2. **Automated Splunk app packaging.**
3. **Semantic versioning and deprecation policy for packs.**
4. **Pack signing/checksums/provenance attestations.**
5. **License/attribution scanner for snippets derived from issues or external sources.**
6. **Mapping to Elastic/OCSF later, if product scope expands beyond Splunk.**

## 10. Proposed implementation sequence

1. Fix current Commvault artifact path mismatch.
2. Add `scripts/catalog_sc4s_upstream.py`.
3. Commit generated catalogue contract under `catalogue/generated/` or produce it at build time.
4. Add `docs/contracts/catalogue-api.md`.
5. Add `GET /api/catalogue` and `GET /api/catalogue/{id}`.
6. Extend `pack.schema.json` with provenance/relationship fields.
7. Add canonical directories for filters/postfilters/selectors/reduction rules.
8. Add optional `reduction_rules` metadata that references `.conf` artifacts rather than embedding config.
9. Add SOC field contract metadata and tests.
10. Add upstream drift report command.
11. Add community contribution template and validation pipeline.

## 11. Release/readiness definition for a “10x better” SecHub Resources SC4S pack

A SecHub Resources SC4S pack can be marketed internally as better than upstream when it has:

- All upstream baseline sourcetype/index/source behaviour preserved or deliberately improved.
- Broader event-family coverage than upstream.
- Explicit timestamp, transport, and source-version assumptions.
- Reviewable `.conf` parser/filter/postfilter/selector artifacts.
- Splunk props/transforms/eventtypes/tags where needed.
- SOC field contract and CIM/common-field mapping where appropriate.
- Optional log-reduction presets with safety notes and tests.
- Fixtures covering every declared event family.
- Runtime syslog-ng validation against the supported SC4S version.
- Export bundle with checksums and no secrets.
- Clear difference report versus upstream SC4S built-in support.
- Known limitations and source-side configuration guidance.
- Evidence that real events arrive in Splunk with expected metadata when a Splunk validation target is available.


## 12. Merged catalogue API/UI, presets, trust, and ratings

SC4S Manager needs a merged catalogue API and UI. This is not optional product polish; it is how operators discover whether a source is upstream-only, SecHub Resources curated, community-submitted, or an enhanced replacement for an upstream baseline.

Minimum API/UI requirements:

- list/search all catalogue entries across `sc4s-inbuilt`, `sc4s-inbuilt-lite`, `sechub-resources-pack`, and later `community-extra`
- filter by vendor, product, source class, artifact type, support status, quality tier, SC4S version compatibility, and trust level
- show upstream versus SC4S Manager comparison on the pack detail page
- show available artifacts: parsers, filters, postfilters, selectors, props/transforms, fixtures, docs, and evidence
- show whether a pack has optional logging presets and reduction rules
- show validation status and last verified date
- show provenance: upstream commit, SecHub Resources SC4S pack version, contributor/reviewer, and source sample provenance

### 12.1 Logging presets

Curated packs may expose recommended logging presets. Presets are optional and only available where SC4S Manager has enough evidence to recommend them safely.

Recommended initial preset names:

- `basic`
  - minimum safe ingestion
  - preserves important security/admin/audit events
  - conservative parsing and minimal optional noise reduction
- `standard`
  - recommended default for SOC operation
  - balances security value, searchability, and ingest volume
  - enables safe normalisation and low-risk reduction where proven
- `enhanced`
  - maximum useful context for investigation/threat hunting
  - broader event families and richer field extraction
  - may cost more Splunk ingest/storage; warnings required

Preset rules:

- Presets are metadata plus referenced `.conf` artifacts, not embedded parser code.
- Presets must be disabled unless explicitly selected during onboarding/export/apply.
- Reduction/drop behaviour must be visible before apply.
- Each preset should document expected ingest/coverage trade-offs.
- If a pack lacks evidence, it should not invent presets for symmetry.

### 12.2 Trust and verification levels

Packs should carry a trust/verification level independent of popularity. Suggested levels:

- `unverified` — parsed/captured but not reviewed enough for production recommendation
- `community_submitted` — external submission, basic checks pass
- `trusted_contributor_verified` — reviewed by a trusted contributor with validation evidence
- `s6_verified` — reviewed/tested by S6 against the pack acceptance gates
- `field_verified` — proven in a real customer/lab deployment with sanitised evidence

Trust metadata should include reviewer, date, evidence path, SC4S version, and Splunk/version context where relevant.

### 12.3 Ratings and likes

Add a lightweight like/rating system for operator feedback, but do not let it replace validation.

Useful feedback signals:

- likes/upvotes
- deployment count if telemetry is ever opt-in
- comments/known issue links
- pack quality score derived from objective checks

The UI must distinguish:

- popularity: users found it useful
- trust: someone qualified verified it
- quality: objective capability/validation completeness

A popular unverified pack is still unverified. Democracy is not a parser test.

### 12.4 Upstream comparison as core product

Every SecHub Resources curated pack that overlaps upstream support should show a comparison panel:

- upstream parser/source docs present: yes/no
- upstream artifact paths and commit
- SC4S Manager relationship: extends/overrides/adds reduction/adds Splunk knowledge
- event-family coverage delta
- field extraction delta
- timestamp/timezone improvements
- Splunk props/transforms/eventtypes/tags added
- reduction/filtering presets added
- validation/evidence delta
- known upstream gaps addressed

This is central to the product. Upstream SC4S often provides a basic logging path and expects customers to do the heavy lifting. SC4S Manager should be turnkey SOC pipeline engineering: the parser, routing, reduction, Splunk knowledge, field semantics, fixtures, and evidence in one curated package.

## 13. Sync and cache refresh requirement

Do not overbuild this initially. SC4S Manager needs a simple, repeatable way to refresh its local view of upstream SC4S and rebuild the catalogue/cache.

Minimum command shape:

```bash
scripts/sync_sc4s_upstream.py --ref <tag-or-commit> --refresh-cache
```

Minimum behaviour:

- clone or update the pinned upstream SC4S repo cache
- record upstream repo URL, ref, resolved commit, and refresh timestamp
- rebuild `sc4s-inbuilt` and `sc4s-inbuilt-lite` catalogue data
- rebuild/search-index docs and selected issue/source material if configured
- report added, removed, and changed upstream parser/config files since the previous refresh
- avoid mutating releaseable `packs/` content automatically
- require explicit import/curation workflow to turn upstream material into SecHub Resources curated packs

This should be cache/catalogue refresh, not an auto-merge bot. The first useful version can be a script plus JSON/TSV outputs. UI refresh buttons, scheduled jobs, and GitHub release watchers can come later.

## 14. Sample provenance and sanitisation

Parser quality depends on source logs, but fixtures can contain customer-sensitive material. Every fixture or sample-derived parser improvement should track provenance and sanitisation status.

Pack metadata or evidence docs should record:

- sample source: vendor docs, lab, customer, synthetic, upstream issue, support case
- redistribution permission: commit-safe, private-only, synthetic-only, unknown
- sanitisation status and fields redacted
- whether the fixture is real, synthetic, or synthetic-equivalent
- source/version/log-format evidence
- reviewer/date

No customer-derived fixture should be committed unless it is explicitly approved as sanitized and redistributable. If not, create a synthetic equivalent and record the original as private validation evidence only.

## 15. Open questions

1. Should SC4S Manager ship generated upstream catalogues in release artifacts, or generate them during build from a pinned upstream commit?
2. Should packs be versioned independently from SC4S Manager application releases?
3. How strict should CIM mapping be for non-security/operational sources?
4. Should reduction presets be disabled by default for every source, even obvious debug noise?
5. Should detection content be part of packs or a separate “SOC content pack” layer?
6. How much upstream issue-derived material can be used directly versus treated only as implementation inspiration?
7. Should community submissions land under `community/` first before promotion to `packs/`?
