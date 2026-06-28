# How SC4S Manager enhances SC4S

Status: Draft explanatory library page

## Summary

Splunk Connect for Syslog (SC4S) is the upstream foundation. It solves the hard baseline problem: reliable syslog collection, syslog-ng parsing/routing, source classification, Splunk HEC delivery, buffering, and broad vendor coverage.

SC4S Manager does not replace that work. It makes SC4S easier to operate, easier to validate, and much more useful for SOC pipeline engineering.

The practical difference:

- SC4S often gives a basic source path and expects the customer to complete the heavy lifting.
- SecHub Resources aims to ship curated packs that are turnkey: parser, filters, optional reduction, Splunk props/transforms, SOC field expectations, fixtures, validation evidence, and operational docs.

## What SC4S Manager adds

### 1. Merged catalogue

SC4S Manager catalogues both:

- upstream SC4S built-ins (`sc4s-inbuilt`, `sc4s-inbuilt-lite`)
- curated SecHub Resources SC4S packs (`sechub-resource`)

The operator sees one searchable catalogue, but provenance is always visible. If upstream provides basic Cisco support and SC4S Manager provides a richer Cisco pack, the UI should show that relationship explicitly.

### 2. Curated packs

A curated pack is more than a parser. It should include:

- SC4S/syslog-ng parser `.conf` files
- filters/postfilters/selectors where needed
- optional log-reduction presets
- Splunk `props.conf`, `transforms.conf`, `eventtypes.conf`, and `tags.conf` where useful
- test events and fixture metadata
- source configuration guidance
- field contract and SOC/CIM/OCSF mapping notes
- validation evidence and known limitations

### 3. Optional logging presets

Curated packs may offer optional presets:

- `basic` — minimum safe ingestion
- `standard` — recommended SOC default
- `enhanced` — richer hunting/investigation context with cost warnings

Presets are only available when there is enough evidence to recommend them. Reduction/drop behaviour must be visible before apply.

### 4. Log reduction and filtering

SC4S supports pre-index reduction using postfilters and `r_set_dest_splunk_null_queue`. SC4S Manager should expose this safely through curated, optional, testable presets that reference `.conf` artifacts.

Reduction is a SOC and licensing feature, not a hidden side effect.

### 5. Splunk knowledge objects

Many upstream parsers stop at getting events into Splunk. SecHub Resources SC4S packs should include Splunk knowledge where it improves searchability:

- props/transforms
- eventtypes/tags
- CIM-friendly fields where applicable
- analyst-oriented SPL examples later if product scope includes SOC content packs

### 6. Field semantics

SC4S Manager should use layered field semantics:

1. Primary: Splunk CIM/common Splunk field names, because the product is Splunk-first.
2. Secondary: OCSF category/class mapping, because it gives an open cybersecurity semantic model.
3. Optional/reference: ECS, useful for cross-platform thinking but not the primary target.
4. Preserve vendor-native fields where useful.

Packs should be honest about mapping status: `complete`, `partial`, `not_applicable`, or `unknown`.

### 7. Quality comparison to upstream

For overlapping sources, SC4S Manager should show a comparison:

- upstream artifact paths and version
- event-family coverage delta
- field extraction delta
- timestamp/timezone improvements
- Splunk knowledge added
- reduction/filtering added
- validation evidence delta
- known upstream gaps addressed

This is the core offering: turnkey SOC pipeline engineering for teams that do not have time to reverse-engineer every source.

### 8. Trust and feedback

Packs should distinguish:

- trust: who verified it and how
- quality: objective completeness/validation
- popularity: likes/deployments/user feedback

A popular unverified pack remains unverified.

## Relationship with upstream SC4S

SC4S Manager should stay in sync with upstream by refreshing a pinned upstream cache/catalogue, detecting parser/source changes, and reporting drift. It should not auto-import upstream snippets into release packs. Promotion from source corpus to releaseable pack must be explicit and reviewed.

## What a SOC engineer should expect

A SOC engineer should be able to answer:

- What source versions and event families are covered?
- What logs do I enable at the source?
- What fields and sourcetypes will I get?
- What mappings exist for CIM/OCSF?
- What is dropped or reduced, if anything?
- What Splunk props/transforms are included?
- What validation evidence exists?
- How is this better than upstream SC4S support?
- What are the known limitations?
