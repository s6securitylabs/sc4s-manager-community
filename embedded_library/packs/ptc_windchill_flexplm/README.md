# PTC Windchill / FlexPLM exploitation telemetry pack

Conservative SecHub Resources pack for PTC Windchill PDMLink and FlexPLM exploitation-focused MethodServer log4j telemetry tied to CVE-2026-4681. Scope is intentionally narrow: the public Splunk attack_data replay corpus, the two Windchill MethodServer loggers used by Splunk Research, and exploit-driven `GW_READY_OK`, `c=`, and `p=` request indicators documented by PTC.

This pack is research-backed and replay-corpus-backed only. It does not claim native Windchill or FlexPLM collection validation, parser validation against retained product logs, SC4S replay/read-back validation, or production deployment proof.

## Evidence searched

- `docs/research/ptc-windchill-flexplm-exploitation-20260714.md` records the attributed research summary for the PTC advisory, Splunk analytic story, Splunk detections, and the public attack_data corpus.
- `docs/evidence/upstream-provenance.md` pins the advisory, detection/story IDs, raw fixture SHA256, and upstream commit references used for this first implementation.
- `production-logging-playbook.md` documents the conservative collection boundary and explicit no-native-validation posture.

## Scope

- Listener example: dedicated TCP relay on port `20126` with source tag `PTC_WINDCHILL_FLEXPLM`.
- Payload: one MethodServer log4j record per line.
- Routed sourcetype: `log4j`.
- Default index: `infraops`.
- Event families:
  - `gw_ready_ok_probe`
  - `gateway_command_execution`

## Ingestion and collection notes

Typical ingestion is file-tail or relay collection from Windchill MethodServer log4j files under `<WINDCHILL_HOME>/logs/MethodServer-*-log4j.log`. Front-end Apache or IIS telemetry is an additional corroboration source for exploit activity, but this pack's primary evidence-backed source is the MethodServer log4j stream used by Splunk Research.

Use collector or relay controls only for framing, host/source correction, and safe line splitting. Keep the raw payload intact. Do not drop `GW_READY_OK`, `run?c=`, `run?p=`, `.jsp?c=`, `.jsp?p=`, request path, source IP, logger, or status context by default.

## Fixture semantics

- File: `test-events/windchill_exploitation.log`.
- Provenance: exact public Splunk attack_data corpus, SHA256 `1cd94dc05cc73af1ccb4e815a1469e81667ba22a4d675f045265c507bce4b5ba`.
- Format: raw MethodServer log4j lines prefixed by the originating log filename.
- Event splitting: one event per physical line.
- Timestamp: outer log4j timestamp uses `YYYY-MM-DD HH:MM:SS,mmm`; embedded Windchill event timestamp includes explicit timezone offset such as `+0530`.
- Families present in the vendored corpus:
  - `gateway_command_execution` via `c=whoami`
  - `gw_ready_ok_probe` via `c=echo%20GW_READY_OK`
- Redistribution: commit-safe public replay corpus; not proof of native product logging or field validation.

Validation SPL smoke pattern:

```spl
index=infraops sourcetype=log4j vendor=ptc product=windchill_flexplm ("GW_READY_OK" OR "c=whoami") earliest=-2h
| table _time index sourcetype source vendor product logger src_ip uri_path query_string query_param query_value http_method status signature signature_id _raw
```

## Detection content

`packs/ptc_windchill_flexplm/splunk/default/savedsearches.conf` carries conservative saved-search translations of the two public Splunk Research detections:

- PTC Windchill GW READY OK Probe (`2f37ab99-5eae-44c4-a6bc-15b6d9787a3d`)
- PTC Windchill Gateway Command Execution (`d725b390-fe86-47df-b9a1-57497915403e`)

They remain traceable to the referenced story and upstream detection IDs, but this repository does not claim those searches have been replay/read-back validated here.

## Known limitations

- No native validation is claimed.
- No SC4S replay/read-back evidence is captured for this pack yet.
- The corpus is exploit-focused and does not represent routine Windchill or FlexPLM operational logging.
- Front-end IIS path coverage is documented only as a dependency/corroboration source from the advisory, not as a path-validated collection claim.
- File-read (`p=`) and random `dpr_<8 hex>.jsp` rows are included in the upstream detection logic but are not represented in the current public 16-line fixture corpus.

## Promotion gate

Do not promote this pack to `validated`, `s6_verified`, `field_validated`, or `field_verified` from schema success or the existence of the public replay corpus alone. Promotion requires replay/read-back evidence through the intended route plus native or sanctioned-lab Windchill/FlexPLM telemetry showing event count, index, sourcetype, source, timestamps, logger context, URI/query fields, and analyst-useful detection fidelity.
