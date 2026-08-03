# PTC Windchill / FlexPLM production logging playbook

Status: research-backed guidance only. No native validation is claimed.

## Primary evidence-backed source

Collect PTC Windchill MethodServer log4j files from:

- `<WINDCHILL_HOME>/logs/MethodServer-*-log4j.log`

This is the defensible primary source for the current SecHub bundle because:

- the PTC advisory explicitly directs operators to inspect `<WINDCHILL_HOME>/logs` for exploit indicators;
- Splunk Research's story and detections are built around Windchill MethodServer log4j telemetry;
- the public replay corpus is exactly that MethodServer log4j data.

## Secondary corroboration sources

Document and retain, but do not over-claim from current evidence:

- Apache HTTP Server logs under `<APACHE_HOME>/logs`
- additional `<WINDCHILL_HOME>/logs` web-tier/error logs named by the advisory
- IIS-hosted deployments as a dependency/corroboration surface only until exact path evidence is reviewed locally
- workaround-related config file checks such as `<WT_HOME>\web.config` in IIS environments

## Disabled-by-default collection stance

Use `splunk/default/inputs.conf.example` as documentation-only examples. Keep all stanzas disabled until reviewed and assigned to a dedicated product deployment class. Do not infer that packaging these examples proves collection safety, parser correctness, or indexed read-back.

## IOC and detection focus

Current bundle scope is limited to exploit telemetry around CVE-2026-4681, especially:

- `run?c=`
- `run?p=`
- `.jsp?c=`
- `.jsp?p=`
- `GW_READY_OK`
- `c=echo%20GW_READY_OK`
- `c=whoami`
- Windchill gateway paths such as `/Windchill/servlet/WindchillGW/GW/run` and `/GW/run`

## Acceptance boundary for a future promotion

Before any trust or quality promotion above curated/unverified:

1. Capture sanctioned native or lab-generated Windchill/FlexPLM logs from supported versions.
2. Prove exact collection paths for MethodServer and any approved front-end web logs per deployment mode.
3. Replay through the intended route and verify indexed read-back for count, index, sourcetype, source, timestamps, logger, URI/query, and status fields.
4. Separate exploit guidance from validation claims in all operator-facing docs.
5. Confirm whether the public Splunk SPL works unchanged on retained native logs or requires additional parsing or sourcetype-specific knowledge.

Until then this product bundle should be treated as conservative detection-support coverage only.
