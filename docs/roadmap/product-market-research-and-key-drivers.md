# SC4S Manager product-market research and roadmap drivers

Date: 2026-06-05
Status: Active roadmap input
Scope: SC4S Manager / SC4S Manager control-plane product direction

## Executive conclusion

SC4S Manager has a credible product-market wedge because no clear direct competitor was found for a modern, dedicated control plane for Splunk Connect for Syslog (SC4S).

The durable customer problem is not simply "send syslog to Splunk". The durable problem is log-source lifecycle management for Splunk/SIEM teams:

1. Discover the source and actual emitted format.
2. Configure listener, protocol, TLS, port, and device-side settings.
3. Classify vendor/product/parser path.
4. Assign correct Splunk metadata: index, source, sourcetype, host, timestamp.
5. Validate parser output and field extraction.
6. Validate Splunk TA and CIM readiness where relevant.
7. Suppress noisy traffic safely, with counters and rollback.
8. Monitor drift, fallback, drops, parser breakage, and indexed-event proof over time.

Roadmap driver:

> Build SC4S Manager as the local operating plane for SC4S source onboarding, parser visibility, metadata correctness, runtime health, safe deployment, rollback, and evidence. Also close the specific SC4S limitations that make buyers defect to Cribl: scale tuning, resilience, multi-destination routing, transformation/reduction, observability, and pipeline management. Do not position it as a full SIEM replacement.

## Positioning

Recommended positioning:

> A dedicated control plane for Splunk Connect for Syslog: source onboarding, parser visibility, metadata management, health monitoring, safe deployment, multi-destination routing, cost-aware reduction, and ingestion evidence for Splunk syslog pipelines.

Sharper operator-language variant:

> Make SC4S operable by Splunk admins and SOC onboarding teams without requiring deep syslog-ng/SC4S internals.

Cribl-competitive positioning:

> Keep the SC4S parser ecosystem, but add the control-plane capabilities that make modern pipelines attractive: persistent queues, clear observability, visual routing, policy-driven reduction, replay/validation, and evidence. Compete with Cribl for the Splunk-syslog ingestion lane; do not pretend to be a universal telemetry lakehouse.

Avoid positioning as:

- a full SIEM;
- a generic syslog-ng or rsyslog IDE;
- a generic observability pipeline unless the feature is backed by SC4S-specific implementation and evidence;
- an "AI parser magic" product unless every suggestion is sample-tested and evidence-backed.
## Primary ICP

Primary customer segment:

- Splunk-heavy security teams using or considering SC4S.
- Mid-market to enterprise SOCs with many network/security appliance sources.
- MSSPs/MSPs managing multiple Splunk or Splunk ES customers.
- Regulated teams that need evidence of ingestion, parsing, and rollback.
- Splunk/SIEM consultants and onboarding teams who repeat the same painful source-onboarding work.

Pain profile:

- source onboarding depends on tribal SC4S/syslog-ng knowledge;
- logs arrive in fallback/lastchance or wrong sourcetype/index;
- vendor format changes silently break parsers;
- ingestion appears healthy until downstream TA/CIM/ES content fails;
- noisy sources create cost pressure, but drop filters are risky;
- manual config edits lack preview, validation, rollback, and acceptance evidence.

## Competitive landscape

### SC4S itself

Evidence:

- SC4S documentation: <https://splunk.github.io/splunk-connect-for-syslog/main/>
- SC4S source onboarding docs: <https://splunk.github.io/splunk-connect-for-syslog/main/sources/>
- SC4S configuration docs: <https://splunk.github.io/splunk-connect-for-syslog/main/configuration/>
- SC4S configuration tool: <https://splunk.github.io/splunk-connect-for-syslog/main/architecture/configuration-tool/>
- SC4S repository: <https://github.com/splunk/splunk-connect-for-syslog>

Observed strengths:

- mature syslog-ng based collector/parser for Splunk;
- many vendor/product app parsers;
- Splunk metadata assignment before ingestion;
- support for hints, metadata overrides, environment configuration, and app-parser logic.

Observed gap:

- operational model remains file/env/CLI-heavy;
- the configuration tool is an interactive helper, not an ongoing web management/control plane;
- no obvious built-in UI for live source inventory, parser classification preview, metadata override management, safe deploy/rollback, HEC diagnostics, fallback triage, or Splunk indexed proof.

Roadmap implication:

- SC4S Manager should enhance SC4S rather than replace it: a local, safe, evidence-first operating plane over the SC4S runtime and pack/source artifacts.

### Cribl Stream

Evidence:

- Product: <https://cribl.io/products/stream/>
- Docs: <https://docs.cribl.io/stream/>
- Routes: <https://docs.cribl.io/stream/routes/>
- Pipelines: <https://docs.cribl.io/stream/pipelines/>
- Packs: <https://docs.cribl.io/stream/packs/>

Observed strengths:

- polished visual telemetry pipeline;
- sources, destinations, routes, pipelines, packs;
- broad collection, reduction, enrichment, masking, replay, and routing;
- distributed leader/worker architecture.

Gap relative to SC4S Manager:

- broad observability pipeline, not SC4S-native;
- does not directly manage SC4S parser metadata, SC4S env files, app-parser hints, Splunk TA alignment, or SC4S-specific validation/evidence;
- often introduces a replacement/migration conversation rather than improving an existing SC4S estate.

Roadmap implication:

- Compete with Cribl where Cribl is being selected to fix SC4S pain: management UI, scale visibility, resilience, routing, reduction, observability, and operational control.
- Do not copy Cribl's broad universal-pipeline scope first. Win the Splunk-syslog ingestion lane by combining SC4S parser/domain depth with Cribl-like control-plane ergonomics.

### Apto Solutions critique of SC4S limitations

Evidence:

- Apto article: <https://www.aptosolutions.co.uk/blog/splunk-connect-for-syslog-sc4s-why-syslog-ingestion-needs-a-rethink/>

Distilled claims:

- SC4S can work for basic Splunk-only syslog ingestion, but Apto argues it falls short for modern enterprises.
- Scaling/performance: CPU-intensive, difficult to tune at enterprise scale, and Kubernetes/OpenShift adds operational complexity.
- Reliability/resilience: direct HEC forwarding with only basic buffering creates perceived data-loss risk when Splunk is unavailable.
- Flexibility/vendor lock-in: SC4S is Splunk-centric; multi-destination routing to S3, Kafka, Snowflake, Elasticsearch, and similar targets needs custom work.
- Parser flexibility: non-standard log formats still require manual parser development.
- Observability: built-in visibility is thin, with basic received/dropped metrics and deeper troubleshooting pushed into syslog-ng debug logs or custom Splunk searches.
- Cribl is presented as stronger on performance, persistent queues/retry, multi-destination routing, transformation/enrichment/reduction without config-file editing, and pipeline health/cost dashboards.

Product response:

- Treat the critique as a feature backlog, not a reason to abandon SC4S.
- SC4S Manager should explicitly address these limitations while preserving SC4S's Splunk parser ecosystem and local-control advantages.
- The target is not "SC4S plus prettier screens". The target is a Cribl-competitive SC4S pipeline product for syslog-heavy Splunk environments.

Roadmap implications:

- Add resilient buffering/persistent queue visibility and failure-mode evidence as first-class roadmap items.
- Add multi-destination routing abstractions for Splunk HEC plus secondary outputs such as object storage, Kafka, syslog relay, or HTTP where feasible.
- Add policy-driven filtering/reduction with dry-run counters, cost impact estimates, and rollback.
- Add richer control-plane observability: pipeline health, device compliance, parser/fallback status, queue depth, destination backpressure, and cost/volume trends.
- Add Kubernetes/OpenShift deployment guidance only after the single-node/control-daemon path is reliable; do not let orchestration complexity eat the product.

### Elastic Fleet / Elastic Agent

Evidence:

- Fleet overview: <https://www.elastic.co/docs/reference/fleet>
- Agent policies: <https://www.elastic.co/docs/reference/fleet/agent-policy>
- Integrations catalogue: <https://www.elastic.co/docs/reference/integrations>

Useful product pattern:

- central policy management;
- integration catalogue;
- deployed/managed agent state;
- prebuilt assets and visible status.

Gap relative to SC4S Manager:

- Elastic-stack-specific;
- not Splunk/SC4S/Splunk TA-specific.

Roadmap implication:

- Borrow the source catalogue + policy + deployment status model, but anchor it to SC4S sites/environments, Splunk metadata, and indexed proof.

### Logstash central pipeline management

Evidence:

- Pipeline structure: <https://www.elastic.co/docs/reference/logstash/configuration-file-structure>
- Centralized pipeline management: <https://www.elastic.co/docs/reference/logstash/logstash-centralized-pipeline-management>

Observed strengths:

- flexible input/filter/output model;
- central editing/control in the Elastic ecosystem.

Gap relative to SC4S Manager:

- generic ETL/log pipeline, not SC4S-native;
- not focused on Splunk sourcetype/index/TA/CIM correctness;
- central management belongs to a broader Elastic subscription/platform story.

Roadmap implication:

- SC4S Manager should offer centralized SC4S control without forcing a broader platform migration.

### Graylog, rsyslog, and syslog-ng tooling

Evidence:

- Graylog docs: <https://go2docs.graylog.org/current/home.htm>
- Graylog repository: <https://github.com/Graylog2/graylog2-server>
- rsyslog docs: <https://docs.rsyslog.com/doc//index.html>
- Adiscon LogAnalyzer: <https://loganalyzer.adiscon.com/>
- syslog-ng open source: <https://www.syslog-ng.com/products/open-source-log-management/>
- syslog-ng Premium Edition: <https://www.syslog-ng.com/products/log-management-software/>
- syslog-ng Store Box: <https://www.syslog-ng.com/products/log-management-appliance/>

Observed strengths:

- mature log-management and syslog ecosystems;
- proven UI concepts around inputs, streams, pipelines, collectors, content packs, search, and dashboards.

Gap relative to SC4S Manager:

- generic log-management/syslog tooling rather than SC4S-specific source onboarding and Splunk evidence;
- does not solve the SC4S app-parser, Splunk metadata, TA/CIM, fallback, and local apply/rollback workflow.

Roadmap implication:

- Use their UX concepts where useful, but keep SC4S Manager narrow and deep rather than generic.

## Customer pain evidence and product wedges

### 1. Unknown or almost-syslog sources require parser work

Evidence:

- SC4S source docs state that app-parsers perform index-time operations such as linebreaking, source/sourcetype setting, and timestamping before Splunk receives the data: <https://splunk.github.io/splunk-connect-for-syslog/main/sources/>
- Custom parser/noisy filtering request: <https://github.com/splunk/splunk-connect-for-syslog/issues/3079>
- Citrix parser broke after vendor version/log format change: <https://github.com/splunk/splunk-connect-for-syslog/issues/2776>
- Guardicore/Akamai parser issue involving non-RFC3164 CEF behaviour and host extraction: <https://github.com/splunk/splunk-connect-for-syslog/issues/2988>

Roadmap driver:

- Build a source onboarding and parser preview workflow:
  - paste/capture sample logs;
  - identify RFC3164/RFC5424/CEF/LEEF/nonstandard shape;
  - show likely parser path and why it matched or failed;
  - recommend metadata overrides, unique port hints, source-side changes, or new parser work;
  - regression-test fixture events before apply.

### 2. Sourcetype/index misclassification breaks downstream value

Evidence:

- SC4S docs emphasize parser-driven Splunk metadata and fallback sourcetype when no parser matches: <https://splunk.github.io/splunk-connect-for-syslog/main/sources/>
- VMware vpxa events misclassified and landed in lastchance due to wrong sourcetype/index mapping: <https://github.com/splunk/splunk-connect-for-syslog/issues/2685>
- Cisco ISE sourcetype mismatch: <https://github.com/splunk/splunk-connect-for-syslog/issues/2513>
- Cisco ACS logs not following expected CIM/TA behaviour: <https://github.com/splunk/splunk-connect-for-syslog/issues/639>

Roadmap driver:

- Build a sourcetype/index requirements checker:
  - expected vs actual index/source/sourcetype/host/timestamp;
  - source-level validation history;
  - Splunk indexed marker proof;
  - alert when a source moves into fallback/lastchance or an unexpected sourcetype.

### 3. CIM and TA readiness is a separate problem after ingestion works

Evidence:

- Splunk CIM dashboards/reporting rely on data normalized to CIM tags and fields: <https://help.splunk.com/en/data-management/common-information-model/6.2/introduction/overview-of-the-splunk-common-information-model>
- InfoBlox NIOS DNS CIM compliance issue: <https://github.com/splunk/splunk-connect-for-syslog/issues/2483>
- InfoBlox SPLUNK_CIM format parsing issue: <https://github.com/splunk/splunk-connect-for-syslog/issues/2636>

Roadmap driver:

- Build TA/CIM readiness evidence:
  - expected TA and sourcetype mapping;
  - required/optional field coverage;
  - missing CIM fields/tags by data model;
  - customer-facing evidence bundle for SOC/ES readiness.

### 4. Fallback and lastchance indexes are operational smoke signals

Evidence:

- SC4S docs describe fallback sourcetype as evidence that events are not sourcetyped correctly, usually due to missing parser or altered message format: <https://splunk.github.io/splunk-connect-for-syslog/main/sources/>
- VMware issue explicitly involved lastchance due to misclassification: <https://github.com/splunk/splunk-connect-for-syslog/issues/2685>
- Citrix issue involved wrong index/sourcetype after a source version change: <https://github.com/splunk/splunk-connect-for-syslog/issues/2776>
- SC4S issue search shows recurring fallback-related issues: <https://github.com/splunk/splunk-connect-for-syslog/issues?q=fallback>

Roadmap driver:

- Build a fallback/lastchance triage dashboard:
  - group unknown traffic by sender, port, protocol, and message pattern;
  - explain likely cause;
  - recommend action: metadata override, unique port, source-side format change, new parser, or ignore with justification;
  - track MTTR from fallback to validated source.

### 5. Listener/protocol/port mismatches cause silent no-data failures

Evidence:

- SC4S docs warn unique listening ports are sometimes required when source data cannot be distinguished from other device types: <https://splunk.github.io/splunk-connect-for-syslog/main/sources/>
- SC4S listening-port validation request: <https://github.com/splunk/splunk-connect-for-syslog/issues/2423>
- Qumulo issue where manual tests succeeded but real device traffic likely mismatched listener/TLS expectations: <https://github.com/splunk/splunk-connect-for-syslog/issues/2951>

Roadmap driver:

- Build source preflight checks:
  - TCP/UDP/TLS expectation;
  - listener bound and reachable;
  - certificate/TLS warnings;
  - actual packet/message shape vs configured parser;
  - manual test vs real device traffic distinction.

### 6. Noise filtering is valuable but dangerous without tests and counters

Evidence:

- SC4S docs include postfilter examples for suppressing noisy Cisco debug events: <https://splunk.github.io/splunk-connect-for-syslog/main/sources/>
- Fortigate east/west drop filter issue showed syslog-ng syntax and parsed-field-path complexity: <https://github.com/splunk/splunk-connect-for-syslog/issues/3079>

Roadmap driver:

- Build noisy-log suppression as a guarded workflow, not a casual toggle:
  - sample-tested postfilter builder;
  - impact estimate;
  - false-drop warning;
  - dry-run/count-only mode before dropping;
  - rollback and evidence.

### 7. syslog-ng behaviour can fail in ways operators do not see

Evidence:

- Parser silent-drop concern: <https://github.com/syslog-ng/syslog-ng/issues/5643>
- Flow-control/stopped logging issue: <https://github.com/syslog-ng/syslog-ng/issues/4485>
- Cisco parser message-shape mismatch: <https://github.com/syslog-ng/syslog-ng/issues/4125>
- kv-parser field parsing issue: <https://github.com/syslog-ng/syslog-ng/issues/3953>
- csv-parser corruption concern: <https://github.com/syslog-ng/syslog-ng/issues/1104>

Roadmap driver:

- Build end-to-end runtime health around actual evidence:
  - packet/listener counters;
  - parser counters;
  - destination written/dropped/queued counters;
  - Splunk indexed marker proof;
  - warnings/errors surfaced in the UI;
  - source-level canaries where configured.

## Current local product gaps found during repo inspection

Inspection path: `/home/jarvis/work/sc4s-manager`

Current product surface:

- Backend/API exposes health, stats, config, packs, source catalogue, SC4S Library import/apply, destinations, routes, metrics, TLS, validation, backups/diff/restore, audit, reload/restart, pack fixture validation, and exports.
- Control daemon allowlist is intentionally narrow: status, logs, metrics, validate, reload, restart.
- Frontend routes currently include dashboard, SC4S Library, source catalogue/detail, local packs/detail, onboarding preview, sources, destinations, routes, and exports.
- Core product docs correctly state the Manager/Library boundary and no-Docker-socket/narrow-control model.

Roadmap-impacting gaps:

1. UI product surface lags backend/API and operator needs.
   - Missing first-class UI for sources, destinations, metrics, validation, backup/rollback/audit, TLS, SC4S runtime health, and logs/reload/restart workflows.
2. Dashboard can report connectivity while not proving live ingestion health.
   - It should show runtime/listener/HEC/queue/drop/fallback/Splunk proof, not just catalogue/pack availability.
3. Exports UI still presents itself as a stub workflow.
   - Export should become a customer-ready artifact centre with manifests, checksums, SC4S/Splunk bundle breakdown, deployment README, and validation evidence.
4. Catalogue `source_status` appears in the contract/frontend but is not in the backend filter allowlist.
   - Candidate/community filtering risk should be fixed to preserve trust semantics.
5. Readiness docs have stale/conflicting language around Splunk indexed proof and release acceptance.
   - Consolidate current readiness narrative before external pilot/customer use.
6. Live browser E2E avoids dangerous mutation workflows.
   - Add a disposable-environment browser journey for validate/apply/reload/post-check/rollback before stronger enterprise claims.
7. Curated local pack breadth is narrow.
   - Commvault and PAN-OS are useful, but product-market proof needs more common hero sources.
8. Commercial packaging/security artefacts are limited.
   - Need compatibility matrix, hardening guide, threat model summary, support boundary, update channel, install package, and pilot success criteria.
9. RBAC is a deliberate v1 non-goal.
   - Keep it out of the first build wave unless a pilot demands it, but document viewer/operator/admin and approval gates as enterprise roadmap.
10. Cribl-competitive pipeline features are not yet first-class.
   - Current Manager direction covers SC4S control and evidence, but the Apto critique highlights missing enterprise-pipeline expectations: persistent buffering, retry/failure visibility, multi-destination routing, visual transformation/reduction, cost/volume analytics, and richer pipeline observability.

## Prioritised roadmap drivers

Scoring used 1-5 for customer pain, observed market gap, defensibility, build feasibility, and sales/pilot value.

1. Source onboarding + parser preview — 4.70/5
   - Highest strategic wedge.
   - Deeply SC4S/Splunk-specific.
   - Turns tribal parser work into guided, sample-tested workflow.

2. Runtime-health dashboard — 4.65/5
   - Required for operator trust.
   - Converts Manager from catalogue/pack browser into control plane.
   - Must prove live state, not just API reachability.

3. Fallback/lastchance triage — 4.65/5
   - Strong Splunk-specific operational pain.
   - Clear measurable value: reduce unknown/misclassified sources and time-to-fix.

4. Resilience + multi-destination routing — 4.60/5
   - Directly addresses the Cribl defection story: Splunk outage risk, pipeline lock-in, retry/queue visibility, and secondary destinations.
   - Should start with SC4S/syslog-heavy routes, not universal telemetry sprawl.

5. Commercial packaging/security docs — 4.55/5
   - High feasibility and essential for pilots.
   - Prevents "interesting internal tool" perception.

6. CIM/TA readiness evidence — 4.45/5
   - Valuable for SOC/Enterprise Security teams.
   - Strong differentiator beyond raw ingestion.

7. Policy-driven reduction and cost visibility — 4.20/5
   - Cribl wins when buyers want license-cost control.
   - Needs dry-run/count-only mode, impact estimates, and rollback before destructive drops.

8. Pack breadth expansion — 4.05/5
   - Needed for demos and adoption.
   - Should be driven by high-frequency enterprise sources and evidence quality, not catalogue volume theatre.

9. Noise suppression builder — 3.85/5
   - Useful and cost-relevant, but must be guarded by dry-run, counters, rollback, and sample tests.

10. RBAC/enterprise approvals — 3.40/5
   - Important later; not the first differentiator unless a pilot blocks on it.

## Roadmap translation

### Phase A — Make Manager obviously operational

Goal: an operator can open Manager and know whether SC4S ingestion is healthy.

Build/finish:

- truth-oriented dashboard;
- SC4S runtime/control daemon status;
- listener status and source traffic recency;
- HEC destination health and queue/drop/write counters;
- recent parser/config warnings;
- fallback/lastchance summary;
- metrics explorer;
- destinations UI;
- validation workspace;
- backup/rollback/audit UI;
- export centre cleanup;
- `source_status` API/frontend/contract alignment;
- stale readiness narrative cleanup.

### Phase B — Close the Cribl-defection gaps

Goal: SC4S/Manager becomes credible against Cribl for Splunk-syslog ingestion, especially where buyers complain about scale, resilience, flexibility, and observability.

Build/finish:

- persistent buffering/queue visibility and failure-mode reporting;
- retry/backpressure state for Splunk HEC and other destinations;
- multi-destination routing model starting with Splunk HEC plus secondary archive/forward routes;
- visual route/policy preview before apply;
- cost/volume analytics and license-impact estimates;
- policy-driven reduction with dry-run/count-only rollout;
- enrichment/transformation previews where supported by SC4S/syslog-ng artifacts;
- pipeline health dashboard modelled around device compliance, route health, queue depth, drops, and destination lag.

### Phase C — Own source onboarding

Goal: an operator can onboard a source without becoming a syslog-ng specialist.

Build/finish:

- source onboarding wizard;
- device-side configuration checklist;
- protocol/listener preflight;
- sample log paste/capture;
- parser classification preview;
- expected metadata preview;
- generated config diff;
- validate/apply/reload/rollback workflow;
- source validation history.

### Phase D — Detect broken parsing and drift

Goal: Manager catches parser/source breakage before the SOC or auditor discovers it.

Build/finish:

- unknown/fallback source queue;
- clustering by sender/port/protocol/message pattern;
- reason/explanation for failed match;
- drift detection after SC4S or vendor upgrades;
- parser regression fixtures per source;
- alerting/reporting around moved-to-fallback events.

### Phase E — Prove Splunk/SOC readiness

Goal: "configured" becomes "indexed, parsed, normalized, and defensible".

Build/finish:

- index existence check;
- expected sourcetype/source/index validation;
- marker event indexed proof;
- TA compatibility checklist;
- CIM readiness score;
- evidence bundle export.

### Phase F — Pilot/commercial packaging

Goal: give a customer or partner enough trust to run a controlled pilot.

Build/finish:

- customer-facing install package;
- compatibility matrix;
- hardening guide;
- threat model summary;
- support boundary;
- update channel story;
- pilot success criteria;
- ROI story around onboarding time, fallback reduction, ingestion waste reduction, parser drift reduction, and audit-ready evidence.

## Hero source priorities

Pack breadth should serve product-market proof, not raw count inflation. Prioritise sources that are common, painful, or evidence-rich in Splunk/SOC environments:

1. Fortinet FortiGate
2. Cisco ASA
3. Cisco ISE
4. VMware/vCenter/vpxa family
5. Infoblox
6. Citrix/NetScaler
7. F5 BIG-IP
8. Linux/syslog baseline
9. Windows/Sysmon via syslog relay where relevant
10. Palo Alto PAN-OS as an existing proof source

Each hero source should include:

- self-describing test events;
- supported raw/structured format and wire/envelope assumptions;
- parser path expectations;
- Splunk metadata contract;
- known TA/CIM expectations;
- fixture replay evidence;
- indexed proof where configured;
- known limitations and version drift notes.

## Commercial model hypotheses

Most plausible packaging path:

1. Community/free layer:
   - catalogue/pack browser;
   - basic validation;
   - basic export.
2. Paid/pro layer:
   - runtime health dashboard;
   - source onboarding wizard;
   - fallback/lastchance triage;
   - Splunk indexed validation;
   - evidence bundles;
   - parser/source drift alerts;
   - enterprise hardening and support.
3. Consulting-led productisation:
   - use SC4S Manager to reduce repeated SIEM onboarding labour;
   - convert repeated workflows into product features;
   - avoid building speculative SaaS surface before real pilots.
4. MSSP/partner edition later:
   - multi-environment visibility;
   - customer evidence reports;
   - standardised onboarding packs.

## Risks and mitigations

### Splunk or SC4S absorbs simple management features

Mitigation:

- focus on operational workflows, evidence, drift, parser lifecycle, and customer-ready packaging;
- build source/pack validation quality and repeatable evidence;
- own the workflow, not only config generation.

### Cribl replaces SC4S in some accounts

Mitigation:

- compete with Cribl in the Splunk-syslog lane by addressing the concrete defection drivers: management UI, persistent queue/retry visibility, multi-destination routing, cost-aware filtering, transformation preview, and pipeline health;
- avoid universal telemetry-pipeline sprawl until SC4S/syslog-specific value is proven;
- emphasize Splunk sourcetype, TA, CIM, indexed proof, SC4S parser compatibility, and safe local config/apply semantics.

### Product surface expands too early

Mitigation:

- sequence health, onboarding, fallback, and evidence before RBAC/multitenancy;
- pick hero sources deliberately;
- avoid generic syslog management scope creep.

### Parser assistant overpromises

Mitigation:

- use terms like classification, preview, recommendation, and fixture-tested suggestion;
- require sample-driven validation and indexed proof before production confidence claims;
- make generated parser/config output reviewable files, not hidden magic.

## Decisions to preserve in roadmap discussions

- The core wedge is SC4S-native log-source lifecycle management, expanded enough to compete with Cribl for Splunk-syslog ingestion without pretending to be a universal telemetry platform.
- Runtime health must be evidence-based: desired/staged/applied/verified states stay separate.
- Source onboarding is the highest-value differentiator.
- Fallback/lastchance triage is a high-signal buyer pain and should become first-class UX.
- TA/CIM/indexed proof is what turns ingestion into SOC-ready evidence.
- Noise reduction is useful only with dry-run counters, sample tests, and rollback.
- Pack breadth should prioritise common painful hero sources with strong evidence, not raw catalogue volume.
- Commercial readiness needs buyer trust artefacts, not only internal acceptance tests.
