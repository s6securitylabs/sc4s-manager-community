## Summary

<!-- What problem does this solve, and what outcome should reviewers verify? -->

## Changes

- 

## Validation

<!-- List exact commands and outcomes. State clearly what was not tested. -->

```text
command: 
result: 
```

## Evidence and limitations

<!-- Include sanitized evidence where useful. Distinguish saved/staged, applied, runtime-verified, and Splunk-verified state. -->

## Checklist

- [ ] I kept this pull request focused and documented its intended behavior.
- [ ] I added or updated tests where behavior changed.
- [ ] I ran the relevant checks and recorded the actual results above.
- [ ] I removed credentials, customer data, private infrastructure details, and unsanitized events from code, fixtures, logs, and screenshots.
- [ ] I documented known limitations and any validation I could not perform.

### Community pack submissions

<!-- Complete these only when this PR adds or changes a community pack. -->

- [ ] The pack is staged under `community/<pack_id>/` unless maintainers approved promotion.
- [ ] `pack.json` references real file-backed artifacts; parser and lookup logic is not embedded in JSON.
- [ ] `docs/source-notes.md` documents fixture provenance, rights, and sanitization.
- [ ] `docs/validation-evidence.md` records exact commands, outcomes, and gaps.
- [ ] Trust level and quality status do not claim S6 or field verification without the required evidence.

By submitting this pull request, I confirm that I have the right to submit the contribution and agree to the contribution terms in [CONTRIBUTING.md](../CONTRIBUTING.md).
