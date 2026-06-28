from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SUPPORTED_SCHEMA_VERSIONS = {"0.1"}
REQUIRED_PACK_FIELDS = {
    "schema_version",
    "id",
    "version",
    "url",
    "description",
    "display_name",
    "vendor",
    "product",
    "default_index",
    "default_source",
    "listener",
    "sourcetypes",
    "event_families",
    "artifacts",
    "supported_transports",
    "recommended_transport",
    "source_log_version",
    "validation",
    "test_event_sets",
    "export_artifacts",
    "provenance",
    "relationship_to_upstream",
    "trust_level",
    "quality_status",
    "field_contract",
    "ci",
}
TRANSPORTS = {"udp", "tcp", "tls"}
SYSLOG_PROTOCOLS = {"rfc5425", "rfc5424_over_tcp", "udp_syslog", "tcp_syslog"}
FRAMING = {"octet_counted", "line_delimited", "datagram"}
ENVELOPES = {"ietf_rfc5424", "bsd_rfc3164_or_headerless", "none"}
PAYLOAD_FORMATS = {"custom_application", "json", "cef", "csv", "raw"}
TIME_MODES = {
    "field_utc_epoch",
    "field_with_timezone",
    "field_without_timezone_source_local",
    "source_local_time_requires_timezone",
    "syslog_header_timezone",
    "receiver_time",
    "unknown_requires_validation",
}
SOURCE_CLASSES = {"sc4s-inbuilt", "sc4s-inbuilt-lite", "sechub-resource", "community-extra"}
SOURCE_TYPES = {"vendor_docs", "lab", "customer", "synthetic", "upstream_issue", "support_case", "upstream_sc4s", "mixed"}
REDISTRIBUTION_TYPES = {"commit_safe", "private_only", "synthetic_only", "unknown"}
SANITISATION_STATUSES = {"not_required", "sanitised", "synthetic_equivalent", "pending_review", "unknown"}
RELATIONSHIP_VALUES = {
    "upstream_only",
    "new_pack",
    "extends_upstream",
    "overrides_upstream",
    "adds_postfilters",
    "adds_reduction_rules",
    "adds_splunk_knowledge",
    "docs_only",
    "deprecated",
}
TRUST_LEVELS = {"unverified", "community_submitted", "trusted_contributor_verified", "s6_verified", "field_verified"}
QUALITY_STATUSES = {"catalogued", "draft", "curated", "validated", "field_validated", "deprecated"}
COMMUNITY_CANDIDATE_QUALITY_STATUSES = {"catalogued", "draft"}
MAPPING_STATUSES = {"complete", "partial", "not_applicable", "unknown"}
DROP_BEHAVIORS = {"drops_events", "routes_to_null_queue", "metadata_only", "unknown_requires_review"}
PRESET_IDS = {"basic", "standard", "enhanced"}
ARTIFACT_REFERENCE_SUFFIXES = {".conf", ".csv"}
CRITICAL_COMMON_FIELDS = ("vendor", "product", "vendor_product", "action", "signature_id", "severity")
OPTIONAL_COMMON_FIELDS = ("signature", "user", "src", "dest", "process", "process_id", "app", "message", "rule", "category")
SC4S_EXPORT_KIND_RULES = {
    "syslog_ng_parser": {
        "source_prefixes": ("sc4s/app_parsers/",),
        "target_prefixes": ("local/config/app_parsers/",),
        "suffixes": (".conf",),
    },
    "syslog_ng_filter": {
        "source_prefixes": ("sc4s/filters/",),
        "target_prefixes": ("local/config/filters/",),
        "suffixes": (".conf",),
    },
    "syslog_ng_postfilter": {
        "source_prefixes": ("sc4s/postfilters/",),
        # SC4S 3.x includes local application blocks from local/config/app_parsers/*/*.conf.
        # A postfilter is also a syslog-ng application block, so installing it under
        # local/config/postfilters/ leaves it invisible to the stock include tree.
        "target_prefixes": ("local/config/app_parsers/postfilters/",),
        "suffixes": (".conf",),
    },
    "syslog_ng_selector": {
        "source_prefixes": ("sc4s/selectors/",),
        "target_prefixes": ("local/config/app_parsers/selectors/",),
        "suffixes": (".conf",),
    },
    "syslog_ng_context": {
        "source_prefixes": ("sc4s/context/",),
        "target_prefixes": ("local/context/",),
        "suffixes": (".conf", ".csv"),
    },
    "env_example": {
        "source_prefixes": ("sc4s/",),
        "target_prefixes": ("env_file.d/",),
        "suffixes": (".example",),
    },
}
MESSAGE_PCRE_RE = re.compile(r'message\("((?:[^"\\]|\\.)*)"\s+type\(pcre\)')
MESSAGE_VALUE_PCRE_RE = re.compile(r'match\("((?:[^"\\]|\\.)*)"\s+value\("MESSAGE"\)\s+type\(pcre\)')


def load_packs(root: str | Path) -> list[dict[str, Any]]:
    base = Path(root)
    if not base.exists():
        return []
    packs: list[dict[str, Any]] = []
    for manifest in sorted(base.glob("*/pack.json")):
        pack = json.loads(manifest.read_text())
        pack["pack_dir"] = str(manifest.parent)
        pack["manifest_path"] = str(manifest)
        validate_pack(pack, manifest.parent)
        validate_pack_fixtures(pack, manifest.parent)
        packs.append(pack)
    return packs


def pack_by_id(packs: list[dict[str, Any]], pack_id: str) -> dict[str, Any]:
    for pack in packs:
        if pack.get("id") == pack_id:
            return pack
    raise KeyError(f"pack not found: {pack_id}")


def validate_pack(pack: dict[str, Any], pack_dir: str | Path | None = None) -> None:
    missing = sorted(REQUIRED_PACK_FIELDS - set(pack))
    if missing:
        raise ValueError(f"pack {pack.get('id', '<unknown>')} missing required fields: {', '.join(missing)}")
    if pack["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"pack {pack.get('id', '<unknown>')} has unsupported schema_version: {pack['schema_version']}")
    if not str(pack["version"]).strip():
        raise ValueError("pack version is required")
    if not str(pack["url"]).startswith(("https://", "http://")):
        raise ValueError("pack url must be http(s)")
    if not str(pack["description"]).strip():
        raise ValueError("pack description is required")
    if not isinstance(pack["event_families"], list) or not pack["event_families"]:
        raise ValueError("pack event_families must be a non-empty list")
    family_ids: set[str] = set()
    for family in pack["event_families"]:
        validate_event_family(pack, family)
        family_ids.add(family["id"])
    missing_sourcetypes = sorted(fid for fid in family_ids if fid not in pack["sourcetypes"])
    if missing_sourcetypes:
        raise ValueError(f"pack sourcetypes missing families: {', '.join(missing_sourcetypes)}")
    transport_ids = set()
    recommended_count = 0
    for transport in pack.get("supported_transports", []):
        validate_supported_transport(transport)
        transport_ids.add(transport["id"])
        recommended_count += 1 if transport.get("recommended") else 0
    if pack["recommended_transport"] not in transport_ids:
        raise ValueError("recommended_transport must reference supported_transports.id")
    if recommended_count != 1:
        raise ValueError("exactly one supported transport must be recommended")
    test_event_sets = pack.get("test_event_sets", [])
    if not isinstance(test_event_sets, list) or not test_event_sets:
        raise ValueError("pack test_event_sets must be a non-empty list")
    for event_set in test_event_sets:
        validate_test_event_set(pack, event_set)
    if not isinstance(pack.get("export_artifacts"), list) or not pack["export_artifacts"]:
        raise ValueError("pack export_artifacts must be a non-empty list")
    for artifact in pack["export_artifacts"]:
        validate_export_artifact(artifact)
    artifact_index = {artifact["id"]: artifact for artifact in pack["export_artifacts"]}
    validate_provenance(pack["provenance"])
    if pack["relationship_to_upstream"] not in RELATIONSHIP_VALUES:
        raise ValueError(f"relationship_to_upstream must be one of: {', '.join(sorted(RELATIONSHIP_VALUES))}")
    if pack["trust_level"] not in TRUST_LEVELS:
        raise ValueError(f"trust_level must be one of: {', '.join(sorted(TRUST_LEVELS))}")
    if pack["quality_status"] not in QUALITY_STATUSES:
        raise ValueError(f"quality_status must be one of: {', '.join(sorted(QUALITY_STATUSES))}")
    validate_community_release_gate(pack)
    validate_reduction_rules(pack.get("reduction_rules", []), artifact_index)
    validate_logging_presets(pack.get("logging_presets", []), artifact_index, {rule["id"] for rule in pack.get("reduction_rules", [])})
    validate_field_contract(pack["field_contract"], pack)
    validate_ci_metadata(pack["ci"])
    if pack_dir is not None:
        base = Path(pack_dir)
        for group, files in pack.get("artifacts", {}).items():
            if not isinstance(files, list):
                raise ValueError(f"artifact group {group} must be a list")
            for rel in files:
                _validate_pack_relative_path(base, rel, f"pack artifact missing: {rel}")
        for artifact in pack["export_artifacts"]:
            _validate_pack_relative_path(base, artifact["source_path"], f"export artifact missing: {artifact['source_path']}")
        for event_set in test_event_sets:
            _validate_pack_relative_path(base, event_set["path"], f"test event set file missing: {event_set['path']}")
        for rule in pack.get("reduction_rules", []):
            _validate_pack_relative_path(base, rule["artifact"]["path"], f"reduction rule artifact missing: {rule['artifact']['path']}")
        for preset in pack.get("logging_presets", []):
            for reference in preset.get("artifact_references", []):
                _validate_pack_relative_path(base, reference["path"], f"logging preset artifact missing: {reference['path']}")
        validate_reduction_rule_files(pack.get("reduction_rules", []), artifact_index, base)


def validate_ci_metadata(ci: dict[str, Any]) -> None:
    required = {"last_updated", "last_tested", "tested_commit", "tested_artifact_hashes"}
    missing = sorted(required - set(ci))
    if missing:
        raise ValueError(f"ci metadata missing required fields: {', '.join(missing)}")
    for key in ["last_updated", "last_tested", "tested_commit"]:
        if not str(ci.get(key, "")).strip():
            raise ValueError(f"ci.{key} is required")
    if not isinstance(ci.get("tested_artifact_hashes"), dict):
        raise ValueError("ci.tested_artifact_hashes must be an object")


def validate_event_family(pack: dict[str, Any], family: dict[str, Any]) -> None:
    required = {"id", "label", "match_engine", "match", "expected_sourcetype", "primary_id_field", "required_fields", "timestamp_fields"}
    missing = sorted(required - set(family))
    if missing:
        raise ValueError(f"event family {family.get('id', '<unknown>')} missing required fields: {', '.join(missing)}")
    if family["match_engine"] != "pcre":
        raise ValueError(f"event family {family['id']} match_engine must be pcre")
    if family["expected_sourcetype"] != pack.get("sourcetypes", {}).get(family["id"]):
        raise ValueError(f"event family {family['id']} expected_sourcetype must match sourcetypes map")
    if not isinstance(family["required_fields"], list):
        raise ValueError(f"event family {family['id']} required_fields must be a list")
    if not isinstance(family["timestamp_fields"], list) or not family["timestamp_fields"]:
        raise ValueError(f"event family {family['id']} timestamp_fields must be a non-empty list")


def validate_supported_transport(transport: dict[str, Any]) -> None:
    required = {"id", "label", "transport", "syslog_protocol", "framing", "envelope", "payload_format", "recommended", "default_port"}
    missing = sorted(required - set(transport))
    if missing:
        raise ValueError(f"supported transport {transport.get('id', '<unknown>')} missing required fields: {', '.join(missing)}")
    if transport["transport"] not in TRANSPORTS or transport["syslog_protocol"] not in SYSLOG_PROTOCOLS or transport["framing"] not in FRAMING or transport["envelope"] not in ENVELOPES or transport["payload_format"] not in PAYLOAD_FORMATS:
        raise ValueError(f"supported transport {transport['id']} contains unsupported enum")
    if not isinstance(transport["default_port"], int) or not 0 < transport["default_port"] < 65536:
        raise ValueError(f"supported transport {transport['id']} default_port must be 1-65535")


def validate_community_release_gate(pack: dict[str, Any]) -> None:
    provenance = pack.get("provenance", {})
    origin = provenance.get("origin")
    pack_class = provenance.get("pack_class")
    trust_level = pack.get("trust_level")
    quality_status = pack.get("quality_status")
    community_promotion = provenance.get("community_promotion", False)

    if (
        origin == "community-extra"
        or pack_class == "community-extra"
        or trust_level == "community_submitted"
        or (community_promotion and quality_status in COMMUNITY_CANDIDATE_QUALITY_STATUSES)
    ):
        raise ValueError(
            "community candidate packs must remain candidate-only in catalogue/generated/community until promotion evidence is captured"
        )

    if not community_promotion:
        return

    validation = pack.get("validation", {})
    ci = pack.get("ci", {})
    missing: list[str] = []
    for field in ("date_validated", "validated_by", "evidence"):
        if not str(validation.get(field, "")).strip():
            missing.append(f"validation.{field}")
    tested_artifact_hashes = ci.get("tested_artifact_hashes")
    if not isinstance(tested_artifact_hashes, dict) or not tested_artifact_hashes:
        missing.append("ci.tested_artifact_hashes")
    if missing:
        raise ValueError("community promotion requires " + ", ".join(missing))


def validate_provenance(provenance: dict[str, Any]) -> None:
    required = {"origin", "pack_class", "source", "curation"}
    missing = sorted(required - set(provenance))
    if missing:
        raise ValueError(f"provenance missing required fields: {', '.join(missing)}")
    if provenance["origin"] not in SOURCE_CLASSES:
        raise ValueError("provenance.origin has unsupported value")
    if provenance["pack_class"] not in SOURCE_CLASSES:
        raise ValueError("provenance.pack_class has unsupported value")
    community_promotion = provenance.get("community_promotion", False)
    if not isinstance(community_promotion, bool):
        raise ValueError("provenance.community_promotion must be a boolean")
    source = provenance["source"]
    source_required = {"type", "reference", "redistribution"}
    missing = sorted(source_required - set(source))
    if missing:
        raise ValueError(f"provenance.source missing required fields: {', '.join(missing)}")
    if source["type"] not in SOURCE_TYPES:
        raise ValueError("provenance.source.type has unsupported value")
    if source["redistribution"] not in REDISTRIBUTION_TYPES:
        raise ValueError("provenance.source.redistribution has unsupported value")
    sanitisation_status = source.get("sanitisation_status")
    if sanitisation_status is not None and sanitisation_status not in SANITISATION_STATUSES:
        raise ValueError("provenance.source.sanitisation_status has unsupported value")
    curation = provenance["curation"]
    curation_required = {"reviewed_by", "reviewed_at", "notes"}
    missing = sorted(curation_required - set(curation))
    if missing:
        raise ValueError(f"provenance.curation missing required fields: {', '.join(missing)}")
    if not str(curation["reviewed_by"]).strip() or not str(curation["reviewed_at"]).strip():
        raise ValueError("provenance.curation reviewed_by/reviewed_at are required")


def validate_reduction_rules(rules: list[dict[str, Any]], artifact_index: dict[str, dict[str, Any]]) -> None:
    if not isinstance(rules, list):
        raise ValueError("reduction_rules must be a list")
    seen: set[str] = set()
    for rule in rules:
        required = {"id", "label", "description", "artifact"}
        missing = sorted(required - set(rule))
        if missing:
            raise ValueError(f"reduction rule {rule.get('id', '<unknown>')} missing required fields: {', '.join(missing)}")
        if rule["id"] in seen:
            raise ValueError(f"reduction rule ids must be unique: {rule['id']}")
        seen.add(rule["id"])
        drop_behavior = rule.get("drop_behavior")
        if drop_behavior is not None and drop_behavior not in DROP_BEHAVIORS:
            raise ValueError(f"reduction rule {rule['id']} drop_behavior has unsupported value")
        validate_artifact_reference(rule["artifact"], artifact_index, f"reduction rule {rule['id']}")


def validate_reduction_rule_files(rules: list[dict[str, Any]], artifact_index: dict[str, dict[str, Any]], base: Path) -> None:
    for rule in rules:
        artifact = artifact_index[rule["artifact"]["artifact_id"]]
        if artifact.get("kind") != "syslog_ng_postfilter":
            raise ValueError(f"reduction rule {rule['id']} must reference a syslog_ng_postfilter export artifact")
        text = _load_pack_artifact_text(base, artifact["source_path"])
        if "r_set_dest_splunk_null_queue" not in text:
            raise ValueError(f"reduction rule {rule['id']} postfilter must call r_set_dest_splunk_null_queue")
        if not _extract_reduction_patterns(text):
            raise ValueError(f"reduction rule {rule['id']} postfilter must include at least one MESSAGE PCRE matcher")


def validate_logging_presets(presets: list[dict[str, Any]], artifact_index: dict[str, dict[str, Any]], reduction_rule_ids: set[str]) -> None:
    if not isinstance(presets, list):
        raise ValueError("logging_presets must be a list")
    seen: set[str] = set()
    enabled_by_default = 0
    for preset in presets:
        required = {"id", "label", "description", "enabled_by_default", "artifact_references", "reduction_rules"}
        missing = sorted(required - set(preset))
        if missing:
            raise ValueError(f"logging preset {preset.get('id', '<unknown>')} missing required fields: {', '.join(missing)}")
        if preset["id"] not in PRESET_IDS:
            raise ValueError(f"logging preset {preset['id']} has unsupported id")
        if preset["id"] in seen:
            raise ValueError(f"logging preset ids must be unique: {preset['id']}")
        seen.add(preset["id"])
        enabled_by_default += 1 if preset.get("enabled_by_default") else 0
        if not isinstance(preset["artifact_references"], list):
            raise ValueError(f"logging preset {preset['id']} artifact_references must be a list")
        for reference in preset["artifact_references"]:
            validate_artifact_reference(reference, artifact_index, f"logging preset {preset['id']}")
        if not isinstance(preset["reduction_rules"], list):
            raise ValueError(f"logging preset {preset['id']} reduction_rules must be a list")
        for rule_id in preset["reduction_rules"]:
            if rule_id not in reduction_rule_ids:
                raise ValueError(f"logging preset {preset['id']} references unknown reduction rule: {rule_id}")
        if preset["reduction_rules"] and preset.get("enabled_by_default"):
            raise ValueError(f"logging preset {preset['id']} cannot be enabled_by_default when it includes reduction_rules")
    if enabled_by_default > 1:
        raise ValueError("at most one logging preset may be enabled_by_default")


def validate_artifact_reference(reference: dict[str, Any], artifact_index: dict[str, dict[str, Any]], owner: str) -> None:
    required = {"artifact_id", "path"}
    missing = sorted(required - set(reference))
    if missing:
        raise ValueError(f"{owner} artifact reference missing required fields: {', '.join(missing)}")
    artifact_id = reference["artifact_id"]
    if artifact_id not in artifact_index:
        raise ValueError(f"{owner} references unknown export artifact: {artifact_id}")
    path = _normalize_relative_path(str(reference["path"]))
    _validate_reference_path(path, f"{owner} artifact reference")
    if path != _normalize_relative_path(str(artifact_index[artifact_id]["source_path"])):
        raise ValueError(f"{owner} artifact reference path must match export artifact {artifact_id}")


def validate_field_contract(field_contract: dict[str, Any], pack: dict[str, Any] | None = None) -> None:
    required_sections = {
        "cim": ("primary", True),
        "ocsf": ("secondary", True),
        "ecs": ("optional", True),
    }
    missing = sorted(set(required_sections) - set(field_contract))
    if missing:
        raise ValueError(f"field_contract missing required sections: {', '.join(missing)}")
    for section, (bool_key, expected) in required_sections.items():
        payload = field_contract[section]
        required = {"mapping_status", bool_key, "fields"}
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"field_contract.{section} missing required fields: {', '.join(missing)}")
        if payload["mapping_status"] not in MAPPING_STATUSES:
            raise ValueError(f"field_contract.{section}.mapping_status has unsupported value")
        if payload[bool_key] is not expected:
            raise ValueError(f"field_contract.{section}.{bool_key} must be {expected}")
        if not isinstance(payload["fields"], dict):
            raise ValueError(f"field_contract.{section}.fields must be an object")
        if payload["mapping_status"] == "unknown" and payload["fields"]:
            raise ValueError(f"field_contract.{section}.fields must be empty when mapping_status is unknown")
        for field_name, mapping in payload["fields"].items():
            validate_field_mapping(section, field_name, mapping)
        if payload["mapping_status"] == "complete":
            incomplete = sorted(field_name for field_name, mapping in payload["fields"].items() if mapping["status"] != "complete")
            if incomplete:
                raise ValueError(
                    f"field_contract.{section}.mapping_status cannot be complete while field mappings remain partial/unknown: {', '.join(incomplete)}"
                )
    if pack is not None:
        assessment = summarize_field_contract(pack)
        if field_contract["cim"]["mapping_status"] == "complete" and assessment["cim"]["coverage_gap_count"]:
            raise ValueError(
                "field_contract.cim.mapping_status cannot be complete while common SOC fields are still unmapped: "
                + ", ".join(assessment["common"]["missing_required_fields"])
            )


def validate_field_mapping(section: str, field_name: str, mapping: dict[str, Any]) -> None:
    required = {"source_fields", "status", "notes"}
    missing = sorted(required - set(mapping))
    if missing:
        raise ValueError(f"field_contract.{section}.{field_name} missing required fields: {', '.join(missing)}")
    if not isinstance(mapping["source_fields"], list):
        raise ValueError(f"field_contract.{section}.{field_name}.source_fields must be a list")
    if mapping["status"] not in MAPPING_STATUSES:
        raise ValueError(f"field_contract.{section}.{field_name}.status has unsupported value")
    if mapping["status"] in {"complete", "partial"} and not mapping["source_fields"]:
        raise ValueError(f"field_contract.{section}.{field_name}.source_fields must be non-empty when status is {mapping['status']}")


def summarize_field_contract(pack: dict[str, Any]) -> dict[str, Any]:
    field_contract = pack.get("field_contract", {}) or {}
    normalized_fields = pack.get("normalized_fields", {}) or {}
    common_present = {key for key in normalized_fields if normalized_fields.get(key)}
    required_common = [field for field in CRITICAL_COMMON_FIELDS]
    optional_common = [field for field in OPTIONAL_COMMON_FIELDS if field not in CRITICAL_COMMON_FIELDS]
    missing_required = [field for field in required_common if field not in common_present]
    cim_payload = field_contract.get("cim", {}) or {}
    cim_fields = cim_payload.get("fields", {}) if isinstance(cim_payload.get("fields"), dict) else {}
    mapped_cim_fields = sorted(field_name for field_name, mapping in cim_fields.items() if mapping.get("status") in {"partial", "complete"})
    incomplete_cim_fields = sorted(field_name for field_name, mapping in cim_fields.items() if mapping.get("status") != "complete")
    return {
        "common": {
            "required_fields": required_common,
            "optional_fields": optional_common,
            "present_fields": sorted(common_present),
            "missing_required_fields": missing_required,
            "status": "complete" if not missing_required else "partial",
        },
        "cim": {
            "declared_status": cim_payload.get("mapping_status", "unknown"),
            "mapped_fields": mapped_cim_fields,
            "incomplete_fields": incomplete_cim_fields,
            "coverage_gap_count": len(missing_required),
            "honesty_warnings": [f"Missing required common field mapping: {field}" for field in missing_required]
            + [f"CIM field not complete: {field}" for field in incomplete_cim_fields],
        },
    }


def summarize_preset_previews(pack: dict[str, Any], fixture_results: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    fixtures = fixture_results or []
    rule_index = {rule["id"]: rule for rule in pack.get("reduction_rules", [])}
    previews: list[dict[str, Any]] = []
    for preset in pack.get("logging_presets", []):
        rule_summaries: list[dict[str, Any]] = []
        dropped_total = 0
        retained_total = 0
        for rule_id in preset.get("reduction_rules", []):
            fixture_impacts = []
            for fixture in fixtures:
                counts = ((fixture.get("reduction_rules") or {}).get(rule_id) or {})
                dropped = int(counts.get("dropped") or 0)
                retained = int(counts.get("retained") or 0)
                if dropped or retained:
                    fixture_impacts.append({"fixture_id": fixture.get("id"), "dropped": dropped, "retained": retained})
                    dropped_total += dropped
                    retained_total += retained
            rule = rule_index.get(rule_id, {})
            rule_summaries.append(
                {
                    "id": rule_id,
                    "drop_behavior": rule.get("drop_behavior"),
                    "safety_notes": rule.get("safety_notes"),
                    "fixture_impacts": fixture_impacts,
                }
            )
        previews.append(
            {
                "id": preset.get("id"),
                "label": preset.get("label"),
                "enabled_by_default": bool(preset.get("enabled_by_default")),
                "artifact_count": len(preset.get("artifact_references", [])),
                "contains_reduction": bool(preset.get("reduction_rules")),
                "requires_opt_in": bool(preset.get("reduction_rules")),
                "apply_safety": "preview_required" if preset.get("reduction_rules") else "safe_default",
                "fixture_impact": {"dropped_events": dropped_total, "retained_events": retained_total},
                "reduction_rules": rule_summaries,
                "notes": preset.get("notes"),
            }
        )
    return previews


def _validate_pack_relative_path(base: Path, rel: str, missing_message: str) -> None:
    path = (base / rel).resolve()
    try:
        path.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes pack directory: {rel}") from exc
    if not path.exists():
        raise ValueError(missing_message)


def _validate_reference_path(path: str, label: str) -> None:
    rel_path = Path(_normalize_relative_path(path))
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise ValueError(f"{label} must be a relative safe path")
    if rel_path.suffix not in ARTIFACT_REFERENCE_SUFFIXES:
        raise ValueError(f"{label} must reference a .conf or .csv artifact")


def _normalize_relative_path(path: str) -> str:
    return path.replace("\\", "/")


def _load_pack_artifact_text(base: Path, rel: str) -> str:
    return (base / _normalize_relative_path(rel)).resolve().read_text()


def _extract_reduction_patterns(text: str) -> list[re.Pattern[str]]:
    patterns = [match.group(1) for match in MESSAGE_PCRE_RE.finditer(text)]
    patterns.extend(match.group(1) for match in MESSAGE_VALUE_PCRE_RE.finditer(text))
    return [_compile_manifest_regex(pattern.replace(r'\"', '"')) for pattern in patterns]


def validate_test_event_set(pack: dict[str, Any], event_set: dict[str, Any]) -> None:
    required = {"id", "path", "format", "wire_format", "event_count", "events_per_file", "event_boundary", "record_separator", "one_event_per_line", "multiline", "unique_events", "marker_tokens", "timestamp_policy", "field_delimiting", "expected_families"}
    missing = sorted(required - set(event_set))
    if missing:
        raise ValueError(f"test event set {event_set.get('id', '<unknown>')} missing required fields: {', '.join(missing)}")
    if event_set["format"] not in {"bsd", "ietf", "cef", "csv", "hybrid", "raw", "custom_application"}:
        raise ValueError(f"test event set {event_set['id']} has unsupported format: {event_set['format']}")
    if event_set["events_per_file"] not in {"single", "multiple"}:
        raise ValueError(f"test event set {event_set['id']} events_per_file must be single or multiple")
    if event_set["event_boundary"] not in {"line", "rfc5424_octet_counting", "delimiter", "multiline_pattern", "payload_defined"}:
        raise ValueError(f"test event set {event_set['id']} event_boundary is unsupported")
    if not isinstance(event_set["event_count"], int) or event_set["event_count"] < 1:
        raise ValueError(f"test event set {event_set['id']} event_count must be a positive integer")
    if event_set["event_boundary"] == "delimiter" and not event_set.get("delimiter"):
        raise ValueError(f"test event set {event_set['id']} delimiter is required")
    if event_set["multiline"] and not (event_set.get("start_pattern") or event_set["event_boundary"] == "multiline_pattern"):
        raise ValueError(f"test event set {event_set['id']} multiline fixtures require start_pattern or multiline_pattern boundary")
    timestamp_policy = event_set["timestamp_policy"]
    if not isinstance(timestamp_policy, dict):
        raise ValueError(f"test event set {event_set['id']} timestamp_policy must be an object")
    for key in ["source_time_mode", "primary_field", "primary_timezone", "fallback_time_mode", "fallback_timezone", "requires_source_timezone_when_fields_missing"]:
        if key not in timestamp_policy:
            raise ValueError(f"test event set {event_set['id']} timestamp_policy.{key} is required")
    if timestamp_policy["source_time_mode"] not in TIME_MODES or timestamp_policy["fallback_time_mode"] not in TIME_MODES:
        raise ValueError(f"test event set {event_set['id']} timestamp mode is unsupported")
    if timestamp_policy["fallback_time_mode"] == "source_local_time_requires_timezone" and timestamp_policy.get("fallback_timezone"):
        raise ValueError(f"test event set {event_set['id']} fallback_timezone must stay null until source timezone is known")
    known_families = {family.get("id") for family in pack.get("event_families", [])}
    for family in event_set.get("expected_families", []):
        if family not in known_families:
            raise ValueError(f"test event set {event_set['id']} references unknown family: {family}")


def validate_export_artifact(artifact: dict[str, Any]) -> None:
    required = {"id", "group", "source_path", "target_path", "kind", "rendered", "contains_secrets", "required"}
    missing = sorted(required - set(artifact))
    if missing:
        raise ValueError(f"export artifact {artifact.get('id', '<unknown>')} missing required fields: {', '.join(missing)}")
    if artifact["group"] not in {"sc4s", "splunk", "test_events", "scripts", "docs"}:
        raise ValueError(f"export artifact {artifact['id']} has unsupported group")
    for key in ["rendered", "contains_secrets", "required"]:
        if not isinstance(artifact[key], bool):
            raise ValueError(f"export artifact {artifact['id']} {key} must be boolean")
    for key in ["source_path", "target_path"]:
        rel_path = Path(_normalize_relative_path(str(artifact[key])))
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise ValueError(f"export artifact {artifact['id']} {key} must be a relative safe path")
    if artifact["group"] == "sc4s":
        rule = SC4S_EXPORT_KIND_RULES.get(str(artifact.get("kind", "")))
        if rule is None:
            raise ValueError(f"export artifact {artifact['id']} has unsupported sc4s kind: {artifact.get('kind')}")
        source_path = _normalize_relative_path(str(artifact["source_path"]))
        target_path = _normalize_relative_path(str(artifact["target_path"]))
        if not any(source_path.startswith(prefix) for prefix in rule["source_prefixes"]):
            raise ValueError(f"export artifact {artifact['id']} source_path must use the canonical directory for kind {artifact['kind']}")
        if not any(target_path.startswith(prefix) for prefix in rule["target_prefixes"]):
            raise ValueError(f"export artifact {artifact['id']} target_path must use the canonical runtime directory for kind {artifact['kind']}")
        if not source_path.endswith(rule["suffixes"]):
            allowed = ", ".join(rule["suffixes"])
            raise ValueError(f"export artifact {artifact['id']} source_path must end with one of: {allowed}")


def _compile_manifest_regex(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern.replace("[[:space:]]", r"\s"))


def validate_pack_fixtures(pack: dict[str, Any], pack_dir: str | Path) -> list[dict[str, Any]]:
    base = Path(pack_dir)
    family_patterns = {family["id"]: _compile_manifest_regex(family["match"]) for family in pack["event_families"]}
    artifact_index = {artifact["id"]: artifact for artifact in pack.get("export_artifacts", [])}
    reduction_patterns = {
        rule["id"]: _extract_reduction_patterns(_load_pack_artifact_text(base, artifact_index[rule["artifact"]["artifact_id"]]["source_path"]))
        for rule in pack.get("reduction_rules", [])
    }
    results: list[dict[str, Any]] = []
    for event_set in pack.get("test_event_sets", []):
        fixture = (base / event_set["path"]).resolve()
        _validate_pack_relative_path(base, event_set["path"], f"test event set file missing: {event_set['path']}")
        text = fixture.read_text()
        if event_set["event_boundary"] == "line":
            events = [line for line in text.splitlines() if line.strip()]
        else:
            raise ValueError(f"test event set {event_set['id']} fixture validation for boundary {event_set['event_boundary']} is not implemented yet")
        if len(events) != event_set["event_count"]:
            raise ValueError(f"test event set {event_set['id']} expected {event_set['event_count']} events, found {len(events)}")
        if event_set.get("unique_events") and len(set(events)) != len(events):
            raise ValueError(f"test event set {event_set['id']} contains duplicate events")
        for marker in event_set.get("marker_tokens", []):
            count = text.count(marker)
            if count != 1:
                raise ValueError(f"test event set {event_set['id']} marker {marker} expected once, found {count}")
        matched: dict[str, int] = {family: 0 for family in event_set.get("expected_families", [])}
        for line in events:
            line_matches = [fid for fid, regex in family_patterns.items() if regex.search(line)]
            if not line_matches:
                raise ValueError(f"test event set {event_set['id']} has event that matches no family: {line[:120]}")
            for fid in line_matches:
                if fid in matched:
                    matched[fid] += 1
        missing = sorted(fid for fid, count in matched.items() if count == 0)
        if missing:
            raise ValueError(f"test event set {event_set['id']} missing expected families: {', '.join(missing)}")
        reduction_results = {
            rule_id: {
                "dropped": sum(1 for line in events if any(regex.search(line) for regex in patterns)),
                "retained": sum(1 for line in events if not any(regex.search(line) for regex in patterns)),
            }
            for rule_id, patterns in reduction_patterns.items()
        }
        result = {"id": event_set["id"], "event_count": len(events), "families": matched, "markers": len(event_set.get("marker_tokens", []))}
        if reduction_results:
            result["reduction_rules"] = reduction_results
        results.append(result)
    return results


def pack_export_manifest(pack: dict[str, Any]) -> dict[str, list[str]]:
    artifacts = pack.get("artifacts", {})
    return {
        "sc4s": list(artifacts.get("sc4s", [])),
        "splunk": list(artifacts.get("splunk", [])),
        "test_events": list(artifacts.get("test_events", [])),
        "scripts": list(artifacts.get("scripts", [])),
        "docs": list(artifacts.get("docs", [])),
    }


def pack_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": pack["schema_version"],
        "id": pack["id"],
        "version": pack["version"],
        "url": pack["url"],
        "description": pack["description"],
        "display_name": pack["display_name"],
        "vendor": pack["vendor"],
        "product": pack["product"],
        "default_index": pack["default_index"],
        "default_source": pack["default_source"],
        "listener": pack["listener"],
        "sourcetypes": pack["sourcetypes"],
        "event_families": pack["event_families"],
        "artifacts": pack.get("artifacts", {}),
        "supported_transports": pack.get("supported_transports", []),
        "recommended_transport": pack.get("recommended_transport"),
        "source_log_version": pack.get("source_log_version", {}),
        "validation": pack.get("validation", {}),
        "test_event_sets": pack.get("test_event_sets", []),
        "exports": pack_export_manifest(pack),
        "export_artifacts": pack.get("export_artifacts", []),
        "provenance": pack.get("provenance", {}),
        "relationship_to_upstream": pack.get("relationship_to_upstream"),
        "trust_level": pack.get("trust_level"),
        "quality_status": pack.get("quality_status"),
        "logging_presets": pack.get("logging_presets", []),
        "reduction_rules": pack.get("reduction_rules", []),
        "field_contract": pack.get("field_contract", {}),
    }
