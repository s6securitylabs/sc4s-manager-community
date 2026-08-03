# Microsoft Defender for Cloud

Conservative SecHub Resources pack for Microsoft Defender for Cloud / Azure security posture and alert JSON relays through Event Hub, Cribl, API export, or syslog-style TCP into SC4S/Splunk.

## Scope

Fixture-backed families:

- `microsoft:defender:cloud:security_alert` for records shaped like Microsoft Security alert resources (`Microsoft.Security/alerts`).
- `microsoft:defender:cloud:recommendation` for recommendation/posture records (`Microsoft.Security/recommendations`).
- `microsoft:defender:cloud:assessment` for assessment posture records (`Microsoft.Security/assessments`).
- `microsoft:defender:cloud:secure_score_control` for secure-score-control posture records (`Microsoft.Security/secureScoreControls`).
- `microsoft:defender:cloud:regulatory_compliance` for regulatory-compliance-control posture records (`Microsoft.Security/regulatoryComplianceControls`).

Default index: `epintel`.
Default source: `microsoft_defender_for_cloud`.
Default listener: TCP `20095` with `SOURCE_ALL_SET_APPEND=MICROSOFT_DEFENDER_FOR_CLOUD`.

## Collection and transport notes

Expected relay shape is one JSON object per line. Typical production paths are Azure Event Hub diagnostic/export forwarding, REST/API collector output, Cribl, syslog-ng, or another relay that preserves the JSON payload and adds either the dedicated SC4S source tag or `microsoft_defender_for_cloud` netsource identity. Collector credentials, Event Hub checkpoints, Azure tenant/subscription scoping, and API pagination stay outside this pack.

The ARM/API resource shapes used for secure score and regulatory compliance do not prove a universal native `timeGenerated` field. The fixtures include `timeGenerated` as a relay timestamp so Splunk timestamp parsing is deterministic; operators must map or preserve the local collector/Event Hub timestamp field before validation.

No default filtering, masking, nullQueue routing, or lossy field deletion is included. Optional reduction candidates are documented only in `docs/microsoft_defender_for_cloud_reduction_candidates.csv` and require local replay/read-back and SOC approval before use.

## Source-shape semantics

- Raw format: JSON object per line.
- Envelope: fixture file is headerless JSON; send helper sends one line per event to the dedicated TCP listener.
- Event boundary: newline-delimited one event per record; multiline JSON is not covered.
- Field delimiting: JSON, with nested posture/score/compliance fields preserved by Splunk JSON extraction.
- Timestamp policy: `timeGenerated` in UTC ISO-8601 for fixtures; production collectors must preserve/map an equivalent source or collector timestamp.
- Uniqueness: each synthetic marker appears exactly once and is expected in read-back.

## Provenance and limitations

Fixtures are synthetic-equivalent examples using documentation subscription/resource identifiers and RFC5737 documentation IPs. They are grounded in public Microsoft Defender for Cloud / Microsoft.Security API and schema names where practical (`Microsoft.Security/alerts`, `Microsoft.Security/recommendations`, `Microsoft.Security/assessments`, `Microsoft.Security/secureScoreControls`, `Microsoft.Security/regulatoryComplianceControls`, `severity`, `status`, `resourceId`, `subscriptionId`, `tactics`, `techniques`, `entities`, secure-score `score`/resource counts, and regulatory compliance assessment counters). Microsoft export wrappers vary by connector; compare local Event Hub or API payloads before relying on field completeness.

Attack-path graph internals and Defender for Cloud incident-style records remain out of scope until exact public schema/sample evidence is sufficient. Regulatory-compliance API evidence is from Microsoft's preview REST surface, so local payload comparison is required before operational statements.

Trust remains `unverified`; quality remains `curated`. CI, XML checks, synthetic fixtures, and Splunk dashboard load/oneshot parsing are not SC4S listener replay/read-back validation.

## Splunk fields

The props provide JSON extraction plus aliases for:

- Common: `vendor`, `product`, `vendor_product`, `event_id`, `resource_type`, `subscription_id`, `resource_group`, `resource_id`, `marker`, `action`.
- Alerts: `signature`, `alert_name`, `alert_type`, `severity`, `status`, `affected_resource`, `confidence`, `tactics`, `techniques`, `entities`, `remediation_steps`.
- Recommendations: `recommendation`, `recommendation_type_id`, `category`, `severity`, `status`, `status_code`, `assessment_key`, `compliance_control`, `secure_score_control`, `score_impact`, `policy_definition_id`.
- Assessments: `assessment_key`, `assessment_name`, `status_code`, `status_cause`, `status_description`, `severity`, `category`, `assessment_type`, `policy_definition_id`, `remediation_steps`.
- Secure score controls: `secure_score_control`, `secure_score_current`, `secure_score_max`, `secure_score_percentage`, `healthy_resource_count`, `unhealthy_resource_count`, `not_applicable_resource_count`, `weight`.
- Regulatory compliance controls: `compliance_control`, `compliance_control_description`, `compliance_state`, `passed_assessments`, `failed_assessments`, `skipped_assessments`.

## Dashboard

`splunk/default/data/ui/views/microsoft_defender_for_cloud_overview.xml` includes arrival counts, family distribution, severity/status, affected resources/subscriptions, MITRE tactics/techniques when fixture-backed, recommendations/compliance posture, secure-score-control resource health, regulatory compliance control counters, onboarding metadata, and raw drilldown.

Dashboard panels are tied to fields in the pack fixtures and Splunk props. They do not state Defender for Cloud source validation, complete Microsoft portal parity, attack-path coverage, or incident workflow validation.

## Test replay

```bash
packs/microsoft_defender_for_cloud/scripts/send_tcp_20095.sh 127.0.0.1 20095
```

For a disposable Splunk TEST + SC4S TEST run, use the pack-local Docker/Compose harness:

```bash
packs/microsoft_defender_for_cloud/scripts/e2e_docker_compose.sh plan
packs/microsoft_defender_for_cloud/scripts/e2e_docker_compose.sh run
```

The harness writes an ephemeral compose file under `.tmp/e2e/microsoft_defender_for_cloud/`, starts Splunk with the pack's Splunk knowledge mounted read-only, starts SC4S with the pack parser mounted read-only, sends all five JSON fixture records through TCP `20095`, and queries `index=epintel` for the expected `microsoft:defender:cloud:*` sourcetypes and marker fields. It is an operator-run replay/read-back harness requirements; it is not validation evidence until it is executed in a permitted Docker lab and the Splunk read-back output is retained.

A successful validation requires Splunk read-back of all five marker tokens and expected sourcetypes. Example read-back SPL:

```spl
index=epintel sourcetype=microsoft:defender:cloud:* marker="SC4S_MICROSOFT_DEFENDER_FOR_CLOUD_TEST_*"
| table _time index sourcetype source host vendor product vendor_product marker subscription_id resource_id resource_type action severity status secure_score_control secure_score_current secure_score_max secure_score_percentage healthy_resource_count unhealthy_resource_count not_applicable_resource_count weight compliance_standard compliance_control compliance_state passed_assessments failed_assessments skipped_assessments signature _raw
```

Current validation status is blocked for SC4S listener replay/read-back. See `validation/preflight-2026-06-14.md`.
