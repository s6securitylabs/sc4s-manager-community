# Contributing to SC4S Manager

Thank you for helping improve SC4S Manager.

## Before you start

- Use a GitHub issue for reproducible bugs and focused feature requests.
- Use the pack submission issue form before investing in a new community pack when its scope or licensing is uncertain.
- Do not include customer data, credentials, tokens, private keys, internal hostnames, or unsanitized production events.
- Security vulnerabilities must be reported privately through GitHub's **Report a vulnerability** workflow, not a public issue.

## Community packs

Community packs are staged under `community/<pack_id>/`. Read the [community pack submission guide](docs/contributing/pack-submission-guide.md) before opening a pull request. It defines the required layout, provenance and sanitization rules, evidence requirements, trust states, and validation commands.

A downloaded or submitted pack is not production-ready by default. Promotion and verification remain evidence-driven.

## Code and documentation changes

1. Fork the repository and create a focused branch.
2. Keep unrelated changes out of the pull request.
3. Add or update tests when behavior changes.
4. Run the relevant checks. For the full repository gate:

   ```bash
   ./scripts/test.sh
   ```

5. Complete the pull request checklist and state any validation you could not perform.

## Pull request expectations

A reviewable pull request should include:

- a concise problem statement and the intended outcome;
- the files and behavior changed;
- exact validation commands and outcomes;
- known limitations or deferred evidence;
- sanitized screenshots or evidence where they materially help review.

Maintainers may ask for changes or decline submissions that weaken safety boundaries, blur staged/applied/verified state, expose sensitive data, or cannot be maintained safely.

## Contribution terms

By submitting a contribution, you confirm that you have the right to submit it and grant S6 Security Labs a perpetual, worldwide, non-exclusive, royalty-free, irrevocable licence to use, reproduce, modify, distribute, sublicense, and otherwise incorporate the contribution into SC4S Manager and related S6 Security Labs products and services.

The repository remains governed by its [proprietary licence](LICENSE). Opening a pull request does not grant contributors or users additional rights to the repository's existing software.
