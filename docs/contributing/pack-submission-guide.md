# Community pack submission guide

Status: Draft contributor workflow for SC4S Manager Phase 6

This guide explains how to submit a community pack without lowering the quality bar for curated SecHub Resources content.

SecHub Resources accepts contributions as reviewable files:

- SC4S/syslog-ng artifacts as `.conf`
- lookup/context artifacts as `.csv` or `.conf`
- Splunk knowledge objects as `.conf`
- fixtures as `.log`, `.json`, `.pcap`, or other declared sample files
- evidence as Markdown/JSON with sanitized outputs

Do not embed parser logic, postfilter logic, or lookup tables directly inside `pack.json`. The manifest references file-backed artifacts; it does not replace them.

## 1. Where community submissions live

Unpromoted submissions belong under `community/<pack_id>/` until they pass review and promotion.

`community/` is a staging area for `community-extra` content:

- it is catalogued as community material, not core curated content;
- it must not be presented as `s6_verified` or `field_validated` on arrival;
- it can carry draft documentation, fixtures, and evidence while review is in progress;
- promotion into `packs/` happens only after the gates in this guide are satisfied.

See `../../community/README.md` for staging rules.

## 2. Required submission layout

A community pack should follow this shape:

```text
community/<pack_id>/
  pack.json
  README.md
  docs/
    source-notes.md
    validation-evidence.md
  sc4s/
    app_parsers/
      syslog/
        app-<pack_id>.conf
    filters/
      *.conf
    postfilters/
      *.conf
    selectors/
      *.conf
    context/
      *.csv
      *.conf
  splunk/
    default/
      props.conf
      transforms.conf
      eventtypes.conf
      tags.conf
  test-events/
    *.log
    *.json
    *.pcap
  scripts/
    optional helper scripts
```

Not every directory is mandatory for every source, but every referenced artifact must exist and remain file-backed.

## 3. Minimum manifest expectations

Every submission must provide a `pack.json` that:

- uses a stable `id`, `display_name`, `vendor`, and `product`;
- declares `schema_version` and pack `version`;
- declares supported transports and fixture metadata explicitly;
- references every shipped artifact through relative paths;
- keeps trust/quality metadata separate from likes/ratings;
- explains the relationship to upstream SC4S where one exists.

Recommended contribution metadata for community submissions:

- `effective_origin`: `community-extra`
- `relationship_to_upstream`: one of `new_pack`, `extends_upstream`, `adds_postfilters`, `adds_reduction_rules`, `adds_splunk_knowledge`, or another value from `docs/contracts/catalogue-api.md`
- `trust_level`: `community_submitted`
- `quality_status`: `draft` or `catalogued`

These values describe lifecycle state. They are not a claim that the submission is ready for production.

## 4. Required files and evidence

Every submission should make it easy for a reviewer to answer five questions:

1. What source/vendor/product is this for?
2. Where did the samples come from?
3. Are the fixtures safe to keep in git?
4. What parser/filter/postfilter/Splunk files does it ship?
5. What validation has actually been performed?

Required evidence bundle:

- `README.md`
  - source overview
  - supported event families
  - transport notes
  - known limitations
  - reviewer quick-start commands
- `docs/source-notes.md`
  - vendor/product version or document source
  - provenance of each fixture
  - sanitization method
  - fields or values intentionally redacted
  - licensing/usage notes if sample material came from vendor docs or customer exports
- `docs/validation-evidence.md`
  - schema/path validation status
  - parser/runtime validation status
  - Splunk validation status if available
  - known gaps or blockers
  - exact commands used for repeatable verification
- `test-events/*`
  - representative and uniquely attributable fixtures
  - markers or identifiers preserved where safe
  - timestamps/timezone policy described in `pack.json`

## 5. Fixture provenance and sanitization rules

Fixtures must be useful for parser validation without leaking secrets, credentials, or customer-sensitive data.

Before submitting fixtures:

- replace customer names, usernames, hostnames, domains, IPs, tokens, certs, serials, and internal URLs unless they are already public test identifiers;
- keep enough structure for parser and field extraction validation;
- preserve event-family differences so routing and sourcetype assertions remain meaningful;
- document every important redaction in `docs/source-notes.md`;
- prefer deterministic placeholders such as `example-host-01`, `198.51.100.10`, `SC4S_MANAGER_MARKER_<id>`;
- never commit live Splunk HEC tokens, session cookies, passwords, or private keys.

If a fixture is too sensitive to sanitize, do not commit it. Describe the missing evidence and blocker instead.

## 6. Trust, quality, and feedback are separate

SC4S Manager tracks three different dimensions.

### Trust level

Trust answers: who has verified or vouched for this pack?

- `unverified`
- `community_submitted`
- `trusted_contributor_verified`
- `s6_verified`
- `field_verified`

### Quality status

Quality answers: how mature is the artifact set and validation story?

- `catalogued`
- `draft`
- `curated`
- `validated`
- `field_validated`
- `deprecated`

### Feedback

Feedback answers: do operators find this useful?

- likes/upvotes
- rating average/count
- qualitative comments or issue links

Important rule: feedback cannot change trust level or quality state by itself. A pack with many likes is still only `community_submitted` until a reviewer validates it.

## 7. Promotion workflow

Promotion is explicit and evidence-driven.

1. Community submission lands under `community/<pack_id>/`.
   - Expected defaults: `effective_origin=community-extra`, `trust_level=community_submitted`, `quality_status=draft`.
2. Initial review checks structure, naming, provenance, sanitization, and artifact paths.
3. Validation review checks fixture metadata, parser/runtime syntax, and Splunk/static artifact sanity.
4. Curated promotion moves or recreates the pack under `packs/<pack_id>/` and updates origin/relationship metadata as needed.
   - Typical state after successful curation: `quality_status=curated` or `validated`.
5. S6 verification requires maintained evidence from an S6-reviewed validation path.
   - Only then can `trust_level=s6_verified` be assigned.
6. Field verification is stronger still: sanitized proof from a real lab or customer deployment with enough evidence for reproducible review.

Suggested reviewer gate for `packs/` promotion:

- file-backed SC4S and Splunk artifacts present
- pack manifest validates
- fixtures are attributable and sanitized
- source notes explain provenance and redaction
- validation evidence lists exact commands and outcomes
- relationship to upstream SC4S is honest
- known limitations are documented

## 8. Reviewer quick-start commands

Run commands from the repo root on the service host using either the bootstrap defaults or explicit writable overrides:

```bash
./scripts/test.sh tests/test_packs.py tests/test_catalogue.py tests/test_catalogue_api.py

SC4S_MANAGER_TEST_VENV=${TMPDIR:-/tmp}/sc4s-manager-test-venv.community \
SC4S_MANAGER_COVERAGE_FILE=${TMPDIR:-/tmp}/sc4s-manager.coverage.community \
SC4S_MANAGER_PYTEST_CACHE=${TMPDIR:-/tmp}/sc4s-manager-pytest-cache.community \
./scripts/test.sh tests/test_packs.py tests/test_catalogue.py tests/test_catalogue_api.py

python3 scripts/validate_packs.py --format text
python3 scripts/validate_packs.py --pack-id <pack_id> --format text
```

If runtime syntax or Splunk validation is unavailable, say so explicitly in `docs/validation-evidence.md`. Do not mark the pack `validated` or `s6_verified` from static review alone.

## 9. Pull request checklist

Before opening or approving a PR, confirm:

- [ ] `pack.json` references real `.conf`/`.csv`/fixture files only.
- [ ] Parser/filter/postfilter/selector logic is not embedded in JSON.
- [ ] `docs/source-notes.md` documents sample provenance and sanitization.
- [ ] `docs/validation-evidence.md` records commands, outcomes, and known limits.
- [ ] Trust level, quality status, and feedback are described separately.
- [ ] Submission is staged under `community/` unless it already cleared curation.
- [ ] Promotion criteria to `packs/` and `s6_verified` are explained honestly.
