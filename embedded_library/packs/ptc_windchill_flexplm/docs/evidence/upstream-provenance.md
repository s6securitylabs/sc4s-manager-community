# Upstream provenance for PTC Windchill / FlexPLM exploitation telemetry

Reviewed on 2026-07-14.

## Canonical source references

- PTC advisory
  - URL: https://www.ptc.com/en/about/trust-center/advisory-center/active-advisories/windchill-flexplm-critical-vulnerability
  - advisory scope used here: affected Windchill / FlexPLM families, IOC guidance, and `<WINDCHILL_HOME>/logs` / `<APACHE_HOME>/logs` inspection guidance
- Splunk analytic story
  - URL: https://research.splunk.com/stories/ptc_windchill_exploitation/
  - ID: `3edf40e6-d641-48e1-a6d2-0eed37284dd5`
  - upstream YAML commit: `1305696af6da7aa0b7ef8fec7264db3810711a95`
- Splunk detections
  - GW READY OK Probe: `2f37ab99-5eae-44c4-a6bc-15b6d9787a3d`
  - Gateway Command Execution: `d725b390-fe86-47df-b9a1-57497915403e`
- Splunk data source
  - Windchill Log4j: `f33af1fb-df5c-45c5-b8fd-20b0bbfb5415`
- Splunk macro
  - `windchill_log4j`: `0b89b4b9-f91d-447c-abe9-24d9c5ff3ae2`

## Public fixture provenance

- URL: https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/emerging_threats/windchill/windchill_exploitation.log
- attack_data commit reviewed: `64cb82f9a703a9e5e91aa39c9b0998d838dc632d`
- exact vendored file: `test-events/windchill_exploitation.log`
- SHA256: `1cd94dc05cc73af1ccb4e815a1469e81667ba22a4d675f045265c507bce4b5ba`
- line count: `16`
- classification: public lab replay corpus, `redistribution=commit_safe`, `sanitisation_status=not_required`

## Evidence boundary

This provenance file supports reproducibility and conservative attribution only. It does not constitute replay/read-back validation of the SecHub pack or product bundle.
