# SC4S Manager documentation library

Status: Draft library index

This library explains SC4S Manager as an enhancement layer for Splunk Connect for Syslog (SC4S). SC4S is the foundation: it provides the proven syslog-ng-based collection, parsing, routing, and Splunk HEC delivery model. SC4S Manager builds on that work by adding an operator-focused catalogue, curated packs, SOC-ready validation, optional log reduction, Splunk knowledge artifacts, and evidence-first workflows.

## Library goals

- Explain how SC4S Manager improves and extends upstream SC4S without hiding upstream provenance.
- Give SOC engineers a practical way to choose, validate, and deploy packs.
- Make parser/pack contribution reviewable as ordinary `.conf`, `.csv`, fixture, and documentation diffs.
- Document the merged catalogue: upstream built-ins plus SecHub Resources curated extras.
- Keep release docs honest about what is verified, community-submitted, experimental, or upstream-only.

## Core documents

- `../roadmap/sc4s-manager-catalogue-feature-matrix.md` — requirements, feature matrix, upstream-sync model, SOC acceptance checklist, and gaps.
- `../contracts/catalogue-api.md` — merged catalogue API/UI contract for upstream built-ins and SecHub Resources curated packs.
- `sc4s-manager-enhancements-over-sc4s.md` — product explanation: how SC4S Manager enhances SC4S for turnkey SOC pipeline engineering.
- `../contracts/pack-export-contract.md` — pack export bundle contract.
- `../contracts/packs-api.md` — pack API contract.
- `../contributing/pack-submission-guide.md` — community contribution workflow, staging, trust/quality rules, and sample template.
- `../roadmap/community-candidate-lifecycle.md` — discovery-to-promotion lifecycle for community candidates, provenance rules, warning states, and GitHub issue/PR examples.

## Reader paths

### SOC engineer

Start with `sc4s-manager-enhancements-over-sc4s.md`, then review the SOC acceptance checklist in the feature matrix. Focus on source coverage, field contract, presets, reduction rules, Splunk knowledge, validation evidence, and known limitations.

### Parser/pack contributor

Start with the feature matrix artifact layout and naming sections. Functional config belongs in explicit files: parsers, filters, postfilters, selectors, props/transforms, fixtures, and evidence docs. `pack.json` describes and references artifacts; it does not embed parser code.

### Product/engineering maintainer

Start with `../contracts/catalogue-api.md` and the sync/cache section of the feature matrix. The critical path is a merged catalogue with provenance, upstream drift detection, and explicit SC4S Manager quality comparison.

## Documentation principles

1. Upstream SC4S is credited as the foundation.
2. The upstream corpus is source material, not automatic release content.
3. SecHub Resources curated packs must show how they differ from upstream.
4. Trust, popularity, and quality are separate concepts.
5. SOC-ready means usable fields, reduction choices, Splunk knowledge, evidence, and known limitations — not just a sourcetype.
