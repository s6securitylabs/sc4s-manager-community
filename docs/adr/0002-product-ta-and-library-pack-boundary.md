# ADR 0002: Keep product Splunk TA releases outside the SC4S Library import path

Date: 2026-07-13

## Status

Accepted

## Context

SecHub Resources now publishes complete product logging bundles and immutable Splunk TA TGZ releases alongside the SC4S Library pack ZIPs that Manager already consumes. These artifacts solve different jobs:

- a product TA is installed into Splunk according to a product deployment runbook;
- an SC4S Library pack is downloaded, checksum-verified, schema/fixture-validated, previewed, and selectively applied to SC4S by Manager.

Importing a TGZ through the pack workflow would bypass the pack contract and imply Manager owns arbitrary Splunk app installation. Hiding the related product release entirely would also be unhelpful when an operator is onboarding the same product.

## Decision

1. Manager continues to import only SC4S Library pack ZIPs that satisfy the existing manifest and pack contracts.
2. Canonical catalogue entries may include `product_releases` metadata from SecHub Resources.
   - Each relationship is explicit; Manager never infers it from product, pack, app, URL, or filename text.
   - A Library entry may relate to zero, one, or several product releases, and the UI must preserve every declared relationship.
3. Manager may show a product release as an advisory external deployment/download link, but must label it as a separate **Product TA** artifact.
4. A product release record must declare:
   - `kind: splunk_ta_product_release`;
   - `install_scope: product_deployment`;
   - `manager_importable: false`.
5. Manager must never pass a product release URL or TGZ into download, validate, preview, apply, rollback, or local-verification pack operations.
6. Remote product release metadata and checksums remain advisory until the operator verifies and installs the release through the product runbook. They cannot set Manager-local validation or live state.
7. Product release URLs rendered by the UI must pass the same safe HTTP(S) URL boundary used for other remote links.

## Consequences

- The Library UI can point operators to every explicitly related product TA without confusing any of them with the selected pack.
- Pack import/apply code and its narrow runtime-control boundary remain unchanged.
- The catalogue API contract gains an optional `product_releases` list on remote entries.
- Tests must prove that the UI says Manager imports only the Library pack and that product releases remain `manager_importable: false`.

## Non-goals

- Installing Splunk apps from Manager.
- Managing Splunk deployment server, SHC, or indexer-cluster app distribution.
- Treating a product TA checksum or remote Review status as local runtime proof.

## Related decisions

- [`0001-review-status-and-community-ratings.md`](0001-review-status-and-community-ratings.md)
- SecHub ADR `0005-product-releases-and-library-packs.md`
- SecHub Resources ADR `2026-07-13-product-logging-bundle-boundary.md`
