# SC4S Manager community candidate lifecycle

Status: Draft workflow and user-facing contract for community candidate catalogue entries

This document defines how SC4S Manager should treat GitHub issue, pull request, discussion, doc, and example material before it becomes a curated SecHub Resources SC4S pack.

For local context, read `../AGENTS.md` and `../../community/AGENTS.md`; candidate/import rules must stay aligned with the Manager/Library product boundary.

The key rule is simple:

- upstream SC4S built-ins are official upstream coverage;
- `sechub-resources-pack` packs are curated SecHub Resources artifacts;
- `community-extra` records are source-corpus candidates until review, tests, runtime validation, and representative Splunk evidence prove otherwise.

A useful snippet is still only a candidate until the product can show where it came from, what validation was performed, and what warnings still apply.

## 1. Lifecycle overview

1. Source discovery
   - SC4S Manager discovers promising material from GitHub issues, pull requests, discussions, upstream docs, examples, tests, and similar source-corpus inputs.
   - Discovery creates or refreshes a catalogue record under `community-extra`; it does not create a releaseable pack automatically.

2. Candidate catalogue record
   - The discovered item is searchable in the merged catalogue as a community candidate.
   - Required defaults:
     - `effective_origin=community-extra`
     - `source_status=candidate`
     - `trust_level=community_submitted`
     - `quality_status=catalogued`
     - `validation.state=unvalidated_source_corpus`
   - The candidate can carry source URLs, snippets, notes, and related artifacts, but it must not claim curated or validated status.

3. Human curation into file-backed artifacts
   - A maintainer or contributor converts the candidate into first-party SC4S Manager files under `community/<pack_id>/`.
   - The result must be reviewable as ordinary `.conf`, `.csv`, fixture, and documentation diffs rather than opaque copied prose.

4. Validation and evidence
   - The staged community pack must pass pack/schema checks, fixture review, parser/runtime validation, and, when claiming production readiness, representative Splunk ingestion proof.
   - Validation evidence must be documented and repeatable.

5. Promotion into curated SecHub Resources content
   - Only after the evidence gates pass may the staged pack move into `packs/<pack_id>/` as `sechub-resources-pack` curated content.
   - Promotion clears the community-candidate-only state: the pack no longer presents itself as `source_status=candidate`, and its trust/quality values come from the curated workflow rather than the source-corpus workflow.

## 2. Source discovery inputs

Allowed source discovery inputs include:

- GitHub issues reporting parser gaps, malformed events, or missing source support
- GitHub pull requests that contain parser/filter/postfilter/Splunk artifact diffs
- GitHub discussions that include source notes or prototype parser snippets
- upstream SC4S docs, examples, tests, and sample configs
- vendor docs and public examples referenced by a contributor

Discovery rules:

- keep issue and PR records distinct; a merged PR is still not curated content by itself;
- rank PR file diffs and maintainer comments higher than popularity signals;
- treat copied prose or snippets as reference-only until converted into first-party SecHub Resources artifacts;
- record enough provenance that a reviewer can re-open the source thread later.

## 3. Provenance contract

Every `community-extra` candidate record should preserve provenance first-class.

Minimum provenance fields:

- source URL for the issue, PR, discussion, doc, or example
- source kind such as `issue`, `pull_request`, `discussion`, `parser_snippet`, `documentation`, or `example`
- relationship to upstream, for example `new_pack` or `extends_upstream`
- artifact-level URLs when the source references a concrete parser file or comment
- upstream requested ref and resolved commit when the candidate was derived from a pinned upstream crawl
- generated timestamp for the candidate snapshot

Recommended catalogue behavior:

- `community-extra` entries keep `source_status` and candidate warnings visible in list and detail views
- provenance remains visible after dedupe or merge; do not hide the original source thread just because SC4S Manager later curated the same vendor/product
- when a curated pack is created, keep a human-readable note or source-notes link back to the originating issue/PR/discussion so reviewers can audit how the curated files were derived

## 4. Status meanings

SC4S Manager uses several related but different state fields.

### 4.1 Origin

- `sc4s-inbuilt` — official upstream SC4S full-package coverage
- `sc4s-inbuilt-lite` — official upstream SC4S Lite/addon coverage
- `sechub-resources-pack` — curated SecHub Resources SC4S pack
- `community-extra` — source-corpus or staged community candidate lane

### 4.2 `source_status`

`source_status` is for community-source records, not for curated packs.

- `candidate`
  - meaning: useful source material has been discovered, but it is still only a candidate
  - required behavior: show community warnings, keep validation state unvalidated, and do not imply deploy-ready support

Important guardrail: community candidate data must be clamped to `candidate` semantics even if the source payload tries to self-assert `validated`, `s6_verified`, or similar stronger claims. Community-source discovery is untrusted input.

### 4.3 Trust level

Trust answers who has verified or vouched for the artifact set.

- `unverified`
- `community_submitted`
- `trusted_contributor_verified`
- `s6_verified`
- `field_verified`

For discovered community candidates, the safe default is `community_submitted`.

### 4.4 Quality status

Quality answers how mature the file-backed pack and validation story are.

- `catalogued` — source is known and tracked, but no curated pack is proven yet
- `draft` — staged pack exists but is incomplete
- `curated` — reviewed SecHub Resources artifact set exists
- `validated` — curated pack passed validation gates with evidence
- `field_validated` — stronger real-lab or real-deployment proof exists
- `deprecated` — retained for history or compatibility only

For raw GitHub issue/PR/discussion candidates, the safe default is `catalogued`.

### 4.5 Validation state

For community discovery records, the canonical default is:

- `unvalidated_source_corpus`

For promoted curated packs, the validation state should match the actual evidence path rather than the source-corpus default.

## 5. Validation requirements before promotion

A community candidate does not become a curated SecHub Resources SC4S pack because the snippet looks correct. Promotion requires evidence.

Minimum promotion gates:

1. File-backed artifact conversion
   - parser/filter/postfilter/selector/Splunk artifacts live as reviewable files
   - no parser logic hidden inside JSON metadata or copied issue prose

2. Manifest and path validation
   - `pack.json` validates against the current pack contract
   - artifact paths resolve inside the pack tree only
   - fixture metadata is explicit about format, boundaries, counts, and timestamp policy

3. Provenance and sanitization review
   - `docs/source-notes.md` explains where every fixture came from
   - sensitive values are redacted or replaced with deterministic placeholders
   - licensing/usage notes are recorded when vendor or customer material informed the parser

4. Parser/runtime validation
   - parser syntax and runtime behavior are checked in the real SC4S/SC4S Manager validation path
   - known limitations and blockers are documented honestly

5. Splunk evidence for production-ready claims
   - representative Splunk ingestion evidence exists before claiming `validated`, `s6_verified`, or stronger states
   - exact commands, markers, and proof references are recorded in `docs/validation-evidence.md`

6. Human review
   - a reviewer confirms the relationship to upstream is honest
   - the promoted pack does not hide that it originated from community/source-corpus material

## 6. Promotion path to `sechub-resources-pack`

Promotion should follow this path:

1. Discovery creates `community-extra` catalogue entry.
2. Contributor or maintainer stages a file-backed pack under `community/<pack_id>/`.
3. Review and validation close structural and evidence gaps.
4. Curated promotion moves or recreates the pack under `packs/<pack_id>/`.
5. Catalogue origin changes from `community-extra` to `sechub-resources-pack`.
6. Community-candidate-only fields stop driving the user-facing state; the curated pack now uses its real trust, quality, and validation metadata.

Do not present a promoted pack as if the GitHub snippet itself was the shipped artifact. The shipped artifact is the curated SecHub Resources SC4S pack created from that source material.

## 7. User-facing warning rules

The UI and API should make candidate risk obvious.

Required warning behavior for `community-extra` candidates:

- show labels such as `Community candidate`, `Catalogued only`, and `Unvalidated source corpus`
- explain that issue comments, PR diffs, discussion snippets, likes, and merged status are not proof of deploy-ready support
- keep provenance URLs visible so operators can inspect the original thread
- separate popularity/feedback from trust and quality indicators
- avoid deploy, verified, or production-ready language unless the pack has been promoted and validated

Recommended warning text patterns:

- `Derived from a GitHub issue or PR. Review before use.`
- `Not yet validated in the SecHub Resources promotion workflow.`
- `Popularity and merged status do not count as validation.`
- `Representative Splunk evidence is required before production-ready claims.`

## 8. GitHub-derived examples

### 8.1 GitHub issue-derived parser candidate

A GitHub issue reports that pfSense filterlog events are misparsed and includes sample events plus an illustrative syslog-ng snippet.

Candidate catalogue record:

```json
{
  "id": "community_pfsense_filterlog_issue",
  "effective_origin": "community-extra",
  "relationship_to_upstream": "new_pack",
  "source_kind": "issue",
  "source_status": "candidate",
  "trust_level": "community_submitted",
  "quality_status": "catalogued",
  "validation": {
    "state": "unvalidated_source_corpus"
  },
  "provenance_url": "https://github.com/splunk/splunk-connect-for-syslog/issues/1234",
  "candidate_warnings": [
    "Derived from a GitHub issue; not yet curated.",
    "Do not treat sample snippet text as production-ready parser code."
  ]
}
```

Promotion expectation:

- create `community/pfsense_filterlog/` with real parser files and fixtures
- document fixture provenance and redactions
- validate parser/runtime behavior
- collect Splunk evidence if claiming validated support
- only then promote to `packs/pfsense_filterlog/`

### 8.2 GitHub pull-request-derived parser candidate

A merged GitHub PR adds SonicWall parser changes and includes a concrete `app-*.conf` diff.

Candidate catalogue record:

```json
{
  "id": "community_sonicwall_pr_candidate",
  "effective_origin": "community-extra",
  "relationship_to_upstream": "extends_upstream",
  "source_kind": "pull_request",
  "source_status": "candidate",
  "trust_level": "community_submitted",
  "quality_status": "catalogued",
  "validation": {
    "state": "unvalidated_source_corpus"
  },
  "provenance_url": "https://github.com/splunk/splunk-connect-for-syslog/pull/5678",
  "artifacts": [
    {
      "type": "github_pull_request",
      "kind": "pull_request_file",
      "path": "pulls/5678/files/app-sonicwall_firewall.conf"
    }
  ]
}
```

Important warning:

- merged PR status is a useful ranking signal, not a substitute for SC4S Manager curation and evidence

Promotion expectation:

- recreate the parser changes as first-party SC4S Manager files
- prove compatibility with the target runtime/version
- attach validation evidence and known limitations
- promote only after the curated pack stands on its own

## 9. Review checklist

Before calling a community-derived source `curated` or `validated`, confirm:

- [ ] origin, relationship, and provenance are explicit
- [ ] raw source-corpus records still render as `source_status=candidate`
- [ ] copied issue/PR snippets have been converted into file-backed SecHub Resources artifacts
- [ ] fixture provenance and sanitization are documented
- [ ] validation commands and outcomes are recorded
- [ ] representative Splunk evidence exists for production-ready claims
- [ ] user-facing warnings do not overstate trust or readiness
- [ ] likes, comments, or merged status are not being treated as verification
