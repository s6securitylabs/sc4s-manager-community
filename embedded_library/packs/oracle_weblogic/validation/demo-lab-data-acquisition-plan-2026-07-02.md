# Oracle WebLogic demo-lab data acquisition plan — 2026-07-02

## Purpose

Identify practical ways to obtain **real Oracle WebLogic demo lab logs** for the `oracle_weblogic` pack, especially server/domain `####<...>` logs and HTTP access logs, without inventing product output or copying restricted examples.

This is an acquisition plan, not validation evidence. It does not promote `quality_status`, `trust_level`, `validated`, `s6_verified`, `field_validated`, or `field_verified`.

## Best available data routes

| Route | Source | Cost / openness | Licence / redistribution posture | Evidence value |
|---|---|---:|---|---|
| Oracle WebLogic Server container image | `https://container-registry.oracle.com/ords/f?p=113:4:100::::P4_REPOSITORY,AI_REPOSITORY_NAME,P4_REPOSITORY_NAME:3,Oracle%20WebLogic%20Server,weblogic` | Oracle-provided image; may require terms acceptance/login; not open source | Oracle image/product terms apply. Do not redistribute binaries. Sanitised lab-generated logs can be retained if they contain no secrets or copied documentation samples. | Strongest route for source-generated server/domain/access logs. |
| Oracle official WebLogic Dockerfiles and samples | `https://github.com/oracle/docker-images/tree/main/OracleWebLogic` | Public Docker build/context material; WebLogic binaries remain Oracle-licensed | Check per-file licence; do not vendor installers/binaries. | Strong fallback when prebuilt image cannot be used. |
| Public MIT WebLogic samples | `https://github.com/Azure/Azure-Sentinel/blob/master/Sample%20Data/Custom/OracleWebLogicServer/server.log.txt`, `https://github.com/Azure/Azure-Sentinel/blob/master/Sample%20Data/Custom/OracleWebLogicServer/access.log.txt` | Public, MIT-licensed repository | Suitable for direct or synthetic fixture source with attribution if project policy accepts; still prefer curated minimal excerpts/synthetic equivalents. | Strong fixture/reference data, but not our own lab validation. |
| Public BSD parser tests | `https://github.com/DataDog/integrations-core/blob/master/weblogic/assets/logs/weblogic_tests.yaml` | Public, BSD-3-Clause repository | Suitable for parser-shape/reference data with attribution; direct reuse requires preserving licence conditions. | Strong field-mapping evidence. |
| Elastic WebLogic integration | `https://github.com/elastic/integrations/tree/main/packages/oracle_weblogic` | Source-available under Elastic License 2.0 | Use as parser-shape cross-check; avoid wholesale copying unless licence review approves. | Strong parser-shape evidence, not preferred as direct fixture source. |
| Oracle docs | `https://docs.oracle.com/en/middleware/fusion-middleware/weblogic-server/14.1.2/wllog/logging_services.html` | Public docs, copyrighted | Cite and summarise only; do not copy sample records/prose into fixtures. | Authoritative format description. |

## Open-source reality check

There is no fully open-source WebLogic-compatible runtime that can emit authoritative WebLogic `####<...>` server logs. For true product-generated logs, use Oracle WebLogic itself under its free/developer/container terms. Open-source Oracle-side tooling can help run or collect the lab, but not replace the product as evidence.

## Recommended first lab target

Use an Oracle WebLogic container/domain in the disposable validation lab and capture one narrow variant first:

1. `oracle_weblogic_server`
   - Start AdminServer or a single managed server.
   - Capture startup, normal operational, warning/error, and optional multiline examples from the server/domain log.
   - Preserve exact `####<...>` field order, optional empty fields, raw time, diagnostic context, metadata blocks, and message text boundaries.
2. `oracle_weblogic_access`
   - Enable or confirm HTTP access logging.
   - Generate one successful console/app request, one 404/client error, and one harmless query/path case.
   - Capture exact access-log pattern and timezone behavior.

Defer Security Audit provider, Node Manager, and broader Fusion Middleware until exact emitted examples are captured from the relevant configured component.

## Sanitisation rules

- Replace domain names, server names, machine names, users, thread identifiers if sensitive, IPs, paths, application names, query values, correlation IDs, filesystem paths, and host/container identifiers with `LAB_` or documentation-range values.
- Preserve delimiters, angle-bracket field count/order, empty-field rendering, timestamp format/timezone, message IDs, severity/subsystem tokens, multiline behavior, and HTTP access-log quoting.
- Keep original raw lab captures outside public/export paths until sanitised.
- Retain a private capture note with exact WebLogic version, image/source, domain creation method, logging configuration, request generator, and sanitisation map.

## Minimum evidence to promote beyond alpha

Before raising WebLogic above alpha/unverified, capture and commit:

- Sanitised lab-generated fixtures for server/access only.
- Source/version/logging configuration note.
- Parser/SC4S/Splunk artifacts matching the exact envelope sent to SecHub/SC4S.
- Replay/read-back evidence showing event count, index, sourcetype, source, host, timestamps, required extracted fields, marker fields, and raw preservation.

## Current conclusion

A free/developer demo lab path is feasible for WebLogic using Oracle's container image or official Docker build materials, but it is not an open-source product. Public MIT/BSD samples are strong enough to maintain current alpha source-shape fixtures; product-generated lab capture is still required for any validation or trust promotion.
