# Oracle WebLogic source-shape references — 2026-07-01

Attribution:

- `Azure/Azure-Sentinel`, Oracle WebLogic Server solution sample data and parser, accessed 2026-07-01. Repository licence: MIT. Relevant paths include `Sample Data/Custom/OracleWebLogicServer/server.log.txt`, `Sample Data/Custom/OracleWebLogicServer/access.log.txt`, and `Solutions/OracleWebLogicServer/Parsers/OracleWebLogicServerEvent.yaml`.
- `DataDog/integrations-core`, WebLogic log parsing tests, accessed 2026-07-01. Repository licence: BSD-3-Clause. Relevant path: `weblogic/assets/logs/weblogic_tests.yaml`.
- `elastic/integrations`, package `oracle_weblogic`, accessed 2026-07-01. Repository licence posture: Elastic License 2.0 unless overridden. Relevant test fixtures and ingest pipelines live under `packages/oracle_weblogic/data_stream/{access,domain,admin_server,managed_server}/`.
- Oracle WebLogic documentation for canonical server-log field ordering and access-log behaviour, accessed 2026-07-01. Oracle documentation is copyrighted; use only as factual format reference, not fixture text.

Use in this pack: source-shape reference only. The fixture file in this pack is synthetic-equivalent and rewritten with documentation-range hosts/IPs and `SYNTH_`/marker values; it is not a copy of Azure, Datadog, Elastic, Oracle, or customer logs.

Observed shape summary:

- Server/domain/admin/managed records begin `####<timestamp>` followed by angle-bracket fields including severity, subsystem, server/machine context, thread, user, transaction/diagnostic context, raw epoch milliseconds, metadata attributes, BEA message ID, and message text.
- Access records use a common-log-like HTTP shape with client IP, timestamp, quoted request, status, and byte count. Site-specific WebLogic access format remains configurable and must be confirmed per deployment.

Evidence boundary: Azure MIT and Datadog BSD samples provide stronger redistributable source-shape evidence than Elastic alone, while Elastic provides useful parser-shape cross-checks. This is enough for conservative synthetic-equivalent server/access fixtures and search-time extraction checks. It is not native WebLogic syslog proof, not Security Audit provider proof, and not replay/read-back validation.
