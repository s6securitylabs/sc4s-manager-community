import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.packs import load_packs, pack_by_id, pack_export_manifest, pack_summary, validate_pack, validate_pack_fixtures


def commvault_pack():
    return pack_by_id(load_packs(ROOT / "packs"), "commvault_commcell")


def panos_pack():
    return pack_by_id(load_packs(ROOT / "packs"), "pan_panos")


def schema_validator():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas/pack.schema.json").read_text())
    return jsonschema.Draft202012Validator(schema)


def test_commvault_pack_has_required_metadata_fields():
    commvault = commvault_pack()
    assert commvault["schema_version"] == "0.1"
    assert commvault["id"] == "commvault_commcell"
    assert commvault["version"]
    assert commvault["url"].startswith("https://")
    assert "Commvault" in commvault["description"]
    assert commvault["display_name"] == "Commvault CommCell"


def test_commvault_pack_defines_family_specific_sourcetypes_and_artifacts():
    commvault = commvault_pack()
    assert commvault["sourcetypes"] == {"audit": "commvault:commcell:audittrail", "event": "commvault:commcell:events", "alert": "commvault:commcell:alerts"}
    families = {family["id"]: family for family in commvault["event_families"]}
    assert families["audit"]["label"] == "AuditTrail"
    assert families["audit"]["match_engine"] == "pcre"
    assert families["audit"]["expected_sourcetype"] == "commvault:commcell:audittrail"
    assert families["event"]["required_fields"] == ["Eventid"]
    assert families["alert"]["timestamp_fields"] == ["Utctimestamp", "Alerttime"]
    manifest = pack_export_manifest(commvault)
    assert "sc4s/app_parsers/syslog/app-commvault_commcell.conf" in manifest["sc4s"]
    assert "splunk/default/props.conf" in manifest["splunk"]
    assert "splunk/default/transforms.conf" in manifest["splunk"]
    assert "sc4s/postfilters/app-postfilter-commvault_commcell-drop-alerts.conf" in manifest["sc4s"]
    assert "test-events/commvault_test_events.txt" in manifest["test_events"]


def test_pack_transport_source_version_and_validation_fields_are_explicit():
    commvault = commvault_pack()
    assert commvault["recommended_transport"] == "tls_rfc5425"
    transports = {transport["id"]: transport for transport in commvault["supported_transports"]}
    assert transports["tls_rfc5425"]["recommended"] is True
    assert transports["tls_rfc5425"]["syslog_protocol"] == "rfc5425"
    assert transports["tls_rfc5425"]["framing"] == "octet_counted"
    assert transports["tls_rfc5425"]["envelope"] == "ietf_rfc5424"
    assert transports["tls_rfc5425"]["payload_format"] == "custom_application"
    assert transports["udp_bsd"]["framing"] == "datagram"
    assert transports["tcp_rfc5424"]["syslog_protocol"] == "rfc5424_over_tcp"
    assert commvault["source_log_version"]["name"] == "Commvault Platform Release"
    assert commvault["source_log_version"]["min"] is None
    assert commvault["source_log_version"]["max"] is None
    assert commvault["validation"]["date_validated"]
    assert commvault["validation"]["source_log_version"]
    assert commvault["validation"]["sc4s_version"] == "3.43.0"


def test_commvault_pack_curated_metadata_fields_are_explicit():
    commvault = commvault_pack()
    assert commvault["provenance"]["origin"] == "sechub-resource"
    assert commvault["provenance"]["source"]["redistribution"] == "commit_safe"
    assert commvault["relationship_to_upstream"] == "new_pack"
    assert commvault["trust_level"] == "s6_verified"
    assert commvault["quality_status"] == "validated"
    assert [preset["id"] for preset in commvault["logging_presets"]] == ["basic", "standard", "enhanced"]
    assert commvault["logging_presets"][0]["artifact_references"][0]["artifact_id"] == "sc4s_parser"
    assert commvault["logging_presets"][2]["artifact_references"][0]["artifact_id"] == "sc4s_drop_alerts_postfilter"
    assert commvault["reduction_rules"][0]["id"] == "drop_alert_family_noise"
    assert commvault["field_contract"]["cim"]["mapping_status"] == "partial"
    assert commvault["field_contract"]["cim"]["primary"] is True
    assert commvault["field_contract"]["ocsf"]["secondary"] is True
    assert commvault["field_contract"]["ecs"]["optional"] is True


def test_pack_rejects_candidate_only_community_pack_metadata():
    candidate = copy.deepcopy(commvault_pack())
    candidate["provenance"]["origin"] = "community-extra"
    candidate["provenance"]["pack_class"] = "community-extra"
    candidate["provenance"]["source"]["type"] = "upstream_issue"
    candidate["trust_level"] = "community_submitted"
    candidate["quality_status"] = "draft"

    with pytest.raises(ValueError, match="community candidate packs must remain candidate-only"):
        validate_pack(candidate, candidate["pack_dir"])



def test_pack_rejects_promoted_community_pack_without_release_evidence():
    promoted = copy.deepcopy(commvault_pack())
    promoted["provenance"]["source"]["type"] = "mixed"
    promoted["provenance"]["source"]["reference"] = "https://github.com/splunk/splunk-connect-for-syslog/issues/1234"
    promoted["provenance"]["community_promotion"] = True
    promoted["trust_level"] = "trusted_contributor_verified"
    promoted["quality_status"] = "curated"
    promoted["validation"]["date_validated"] = ""
    promoted["validation"]["validated_by"] = ""
    promoted["validation"]["evidence"] = ""
    promoted["ci"]["tested_artifact_hashes"] = {}

    with pytest.raises(ValueError, match="community promotion requires validation.date_validated, validation.validated_by, validation.evidence, ci.tested_artifact_hashes"):
        validate_pack(promoted, promoted["pack_dir"])



def test_pack_accepts_noncommunity_upstream_curated_pack_without_promotion_gate():
    curated = copy.deepcopy(commvault_pack())
    curated["provenance"]["source"]["type"] = "upstream_sc4s"
    curated["provenance"]["source"]["reference"] = "https://splunk.github.io/splunk-connect-for-syslog/main/sources/vendor/Example/"
    curated["validation"]["date_validated"] = ""
    curated["validation"]["validated_by"] = ""
    curated["validation"]["evidence"] = ""
    curated["ci"]["tested_artifact_hashes"] = {}

    validate_pack(curated, curated["pack_dir"])



def test_pack_accepts_promoted_community_pack_with_release_evidence():
    promoted = copy.deepcopy(commvault_pack())
    promoted["provenance"]["source"]["type"] = "mixed"
    promoted["provenance"]["source"]["reference"] = "https://github.com/splunk/splunk-connect-for-syslog/issues/1234"
    promoted["provenance"]["community_promotion"] = True
    promoted["trust_level"] = "trusted_contributor_verified"
    promoted["quality_status"] = "curated"
    promoted["validation"]["date_validated"] = "2026-05-27"
    promoted["validation"]["validated_by"] = "S6 Security Labs release gate"
    promoted["validation"]["evidence"] = "Representative Splunk HEC/index validation captured in release evidence bundle."
    promoted["ci"]["tested_artifact_hashes"] = {"sc4s/app_parsers/syslog/app-commvault_commcell.conf": "sha256:abc123"}

    validate_pack(promoted, promoted["pack_dir"])


def test_pack_summary_includes_curated_metadata_for_api_consumers():
    summary = pack_summary(commvault_pack())
    assert summary["provenance"]["origin"] == "sechub-resource"
    assert summary["relationship_to_upstream"] == "new_pack"
    assert summary["trust_level"] == "s6_verified"
    assert summary["quality_status"] == "validated"
    assert summary["logging_presets"][1]["id"] == "standard"
    assert summary["reduction_rules"][0]["artifact"]["artifact_id"] == "sc4s_drop_alerts_postfilter"
    assert summary["field_contract"]["ecs"]["mapping_status"] == "unknown"


def test_commvault_test_event_set_declares_format_boundaries_and_time_policy():
    fixture = {event_set["id"]: event_set for event_set in commvault_pack()["test_event_sets"]}["commvault_headerless_single_line"]
    assert fixture["path"] == "test-events/commvault_test_events.txt"
    assert fixture["format"] == "custom_application"
    assert fixture["wire_format"] == "headerless_syslog_payload"
    assert fixture["events_per_file"] == "multiple"
    assert fixture["event_boundary"] == "line"
    assert fixture["record_separator"] == "\\n"
    assert fixture["one_event_per_line"] is True
    assert fixture["multiline"] is False
    assert fixture["unique_events"] is True
    assert fixture["event_count"] == 3
    assert fixture["timestamp_policy"]["source_time_mode"] == "field_utc_epoch"
    assert fixture["timestamp_policy"]["primary_field"] == "Utctimestamp"
    assert fixture["timestamp_policy"]["primary_timezone"] == "UTC"
    assert fixture["timestamp_policy"]["fallback_time_mode"] == "source_local_time_requires_timezone"
    assert fixture["timestamp_policy"]["fallback_timezone"] is None
    assert fixture["field_delimiting"]["style"] == "braced_key_value"
    assert fixture["field_delimiting"]["allows_spaces_in_values"] is True


def test_pack_fixture_validator_counts_markers_and_family_matches():
    commvault = commvault_pack()
    assert validate_pack_fixtures(commvault, commvault["pack_dir"]) == [{"id": "commvault_headerless_single_line", "event_count": 3, "families": {"audit": 1, "event": 1, "alert": 1}, "markers": 3, "reduction_rules": {"drop_alert_family_noise": {"dropped": 1, "retained": 2}}}]


def test_pack_rejects_missing_schema_version():
    commvault = copy.deepcopy(commvault_pack())
    commvault.pop("schema_version")
    with pytest.raises(ValueError, match="schema_version"):
        validate_pack(commvault, commvault["pack_dir"])


def test_pack_rejects_invalid_curated_metadata_values():
    commvault = copy.deepcopy(commvault_pack())
    commvault["trust_level"] = "popular"
    with pytest.raises(ValueError, match="trust_level"):
        validate_pack(commvault, commvault["pack_dir"])

    commvault = copy.deepcopy(commvault_pack())
    commvault["field_contract"]["cim"]["mapping_status"] = "done"
    with pytest.raises(ValueError, match="mapping_status"):
        validate_pack(commvault, commvault["pack_dir"])


def test_pack_export_artifacts_define_targets_and_secret_policy():
    artifacts = {artifact["id"]: artifact for artifact in commvault_pack()["export_artifacts"]}
    assert artifacts["sc4s_parser"]["target_path"] == "local/config/app_parsers/syslog/app-commvault_commcell.conf"
    assert artifacts["sc4s_parser"]["kind"] == "syslog_ng_parser"
    assert artifacts["sc4s_parser"]["contains_secrets"] is False
    assert artifacts["sc4s_parser"]["required"] is True
    assert artifacts["sc4s_drop_alerts_postfilter"]["target_path"] == "local/config/app_parsers/postfilters/app-postfilter-commvault_commcell-drop-alerts.conf"
    assert artifacts["sc4s_drop_alerts_postfilter"]["kind"] == "syslog_ng_postfilter"



def test_pack_ci_metadata_declares_last_updated_and_last_tested_for_release_gates():
    commvault = commvault_pack()
    assert commvault["ci"]["last_updated"]
    assert commvault["ci"]["last_tested"]
    assert commvault["ci"]["tested_commit"]
    assert isinstance(commvault["ci"]["tested_artifact_hashes"], dict)


def test_pack_json_schema_accepts_bundled_packs():
    validator = schema_validator()
    for manifest in sorted((ROOT / "packs").glob("*/pack.json")):
        assert sorted(validator.iter_errors(json.loads(manifest.read_text())), key=lambda e: list(e.path)) == []


def test_pack_json_schema_allows_runtime_only_community_promotion_gate():
    validator = schema_validator()

    promoted = copy.deepcopy(commvault_pack())
    promoted["provenance"]["source"]["type"] = "mixed"
    promoted["provenance"]["community_promotion"] = True
    promoted["trust_level"] = "trusted_contributor_verified"
    promoted["quality_status"] = "curated"
    promoted["validation"]["date_validated"] = ""
    promoted["validation"]["validated_by"] = ""
    promoted["validation"]["evidence"] = ""
    promoted["ci"]["tested_artifact_hashes"] = {}

    assert sorted(validator.iter_errors(promoted), key=lambda e: list(e.path)) == []
    with pytest.raises(ValueError, match="community promotion requires validation.date_validated, validation.validated_by, validation.evidence, ci.tested_artifact_hashes"):
        validate_pack(promoted, promoted["pack_dir"])


def test_pack_json_schema_rejects_invalid_curated_metadata():
    validator = schema_validator()

    commvault = copy.deepcopy(commvault_pack())
    commvault["logging_presets"][0]["artifact_references"][0]["path"] = "source { udp(); }"
    errors = sorted(validator.iter_errors(commvault), key=lambda e: list(e.path))
    assert any(list(error.path)[:4] == ["logging_presets", 0, "artifact_references", 0] for error in errors)

    commvault = copy.deepcopy(commvault_pack())
    commvault["field_contract"]["ocsf"]["mapping_status"] = "finished"
    errors = sorted(validator.iter_errors(commvault), key=lambda e: list(e.path))
    assert any(list(error.path) == ["field_contract", "ocsf", "mapping_status"] for error in errors)


def test_pack_accepts_canonical_sc4s_filter_selector_and_context_artifacts():
    commvault = copy.deepcopy(commvault_pack())
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pack = Path(tmpdir) / commvault["id"]
        shutil.copytree(Path(commvault["pack_dir"]), tmp_pack)
        extras = [
            ("sc4s_filter_allow_audit", "sc4s/filters/f-commvault_commcell-audit.conf", "local/config/filters/f-commvault_commcell-audit.conf", "syslog_ng_filter", 'filter f_commvault_commcell_audit { message("^AuditTrail:" type(pcre)); };\n'),
            ("sc4s_selector_archive", "sc4s/selectors/sc4s-lp-commvault_commcell-archive.conf", "local/config/app_parsers/selectors/sc4s-lp-commvault_commcell-archive.conf", "syslog_ng_selector", 'log { filter { message("^AuditTrail:" type(pcre)); }; destination { network("127.0.0.1" port(514)); }; };\n'),
            ("sc4s_context_vendor_product", "sc4s/context/vendor_product_by_source.csv", "local/context/vendor_product_by_source.csv", "syslog_ng_context", 'f_commvault_commcell,sc4s_vendor_product,commvault_commcell\n'),
        ]
        for artifact_id, source_path, target_path, kind, contents in extras:
            full_path = tmp_pack / source_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(contents)
            commvault["artifacts"]["sc4s"].append(source_path)
            commvault["export_artifacts"].append({
                "id": artifact_id,
                "group": "sc4s",
                "source_path": source_path,
                "target_path": target_path,
                "kind": kind,
                "rendered": False,
                "contains_secrets": False,
                "required": False,
            })
        validate_pack(commvault, tmp_pack)


def test_pack_rejects_noncanonical_sc4s_artifact_paths():
    commvault = copy.deepcopy(commvault_pack())
    for artifact in commvault["export_artifacts"]:
        if artifact["id"] == "sc4s_drop_alerts_postfilter":
            artifact["source_path"] = "sc4s/filters/app-postfilter-commvault_commcell-drop-alerts.conf"
            break
    with pytest.raises(ValueError, match="canonical directory"):
        validate_pack(commvault, commvault["pack_dir"])


def test_panos_pack_declares_csv_transport_timezone_and_honest_validation_metadata():
    panos = panos_pack()
    assert panos["id"] == "pan_panos"
    assert panos["default_index"] == "netfw"
    assert panos["recommended_transport"] == "tls_rfc5425"
    transports = {transport["id"]: transport for transport in panos["supported_transports"]}
    assert transports["tls_rfc5425"]["syslog_protocol"] == "rfc5425"
    assert transports["tls_rfc5425"]["payload_format"] == "csv"
    assert transports["tcp_rfc5424"]["envelope"] == "ietf_rfc5424"
    assert transports["udp_bsd"]["notes"].lower().startswith("legacy/lab")
    assert panos["trust_level"] == "unverified"
    assert panos["quality_status"] == "curated"
    assert "Live downstream read-back from a real PAN-OS/Panorama source is still required" in panos["validation"]["evidence"]

    fixture = {event_set["id"]: event_set for event_set in panos["test_event_sets"]}["panos_csv_single_line"]
    assert fixture["format"] == "csv"
    assert fixture["wire_format"] == "headerless_syslog_payload"
    assert fixture["events_per_file"] == "multiple"
    assert fixture["event_boundary"] == "line"
    assert fixture["record_separator"] == "\\n"
    assert fixture["one_event_per_line"] is True
    assert fixture["multiline"] is False
    assert fixture["unique_events"] is True
    assert fixture["event_count"] == 15
    assert fixture["timestamp_policy"]["source_time_mode"] == "field_without_timezone_source_local"
    assert fixture["timestamp_policy"]["primary_field"] == "Generated Time"
    assert fixture["timestamp_policy"]["primary_timezone"] is None
    assert fixture["timestamp_policy"]["fallback_time_mode"] == "source_local_time_requires_timezone"
    assert fixture["field_delimiting"]["style"] == "positional_csv"
    assert fixture["field_delimiting"]["allows_empty_fields"] is True


def test_panos_pack_fixture_validator_counts_all_families_and_markers():
    panos = panos_pack()
    result = validate_pack_fixtures(panos, panos["pack_dir"])
    assert result == [{
        "id": "panos_csv_single_line",
        "event_count": 15,
        "families": {
            "traffic": 1,
            "threat": 1,
            "wildfire": 1,
            "system": 1,
            "config": 1,
            "hipmatch": 1,
            "userid": 1,
            "globalprotect": 1,
            "auth": 1,
            "decryption": 1,
            "tunnel": 1,
            "correlation": 1,
            "iptag": 1,
            "gtp": 1,
            "sctp": 1,
        },
        "markers": 15,
    }]
