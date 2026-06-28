import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("SC4S_MANAGER_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.app import pack_detail, pack_export_bundle, pack_fixture_validation, pack_inventory


def test_packs_api_inventory_contract_does_not_leak_pack_root():
    response = pack_inventory()
    assert set(response) == {"packs", "count"}
    assert response["count"] == len(response["packs"])
    assert response["packs"]
    assert "pack_root" not in response


def test_packs_api_detail_contract_contains_schema_and_curated_metadata():
    detail = pack_detail("commvault_commcell")
    assert detail["schema_version"] == "0.1"
    assert detail["id"] == "commvault_commcell"
    assert detail["export_artifacts"]
    assert detail["test_event_sets"]
    assert detail["provenance"]["origin"] == "sechub-resource"
    assert detail["relationship_to_upstream"] == "new_pack"
    assert detail["trust_level"] == "s6_verified"
    assert detail["quality_status"] == "validated"
    assert detail["logging_presets"]
    assert detail["reduction_rules"][0]["artifact"]["artifact_id"] == "sc4s_drop_alerts_postfilter"
    assert detail["field_contract"]["cim"]["mapping_status"] == "partial"


def test_packs_api_contract_includes_manifest_artifacts_for_frontend_schema():
    inventory_pack = pack_inventory()["packs"][0]
    detail = pack_detail(inventory_pack["id"])

    assert inventory_pack["artifacts"]
    assert detail["artifacts"] == inventory_pack["artifacts"]
    assert set(inventory_pack["artifacts"]) >= {"sc4s", "splunk", "test_events"}


def test_packs_api_fixture_validation_helper_returns_validator_results():
    response = pack_fixture_validation("commvault_commcell")
    assert response == {"pack_id": "commvault_commcell", "results": [{"id": "commvault_headerless_single_line", "event_count": 3, "families": {"audit": 1, "event": 1, "alert": 1}, "markers": 3, "reduction_rules": {"drop_alert_family_noise": {"dropped": 1, "retained": 2}}}]}


def test_packs_api_export_helper_returns_zip_filename_and_bytes():
    filename, data = pack_export_bundle("commvault_commcell")
    assert filename.endswith(".zip")
    assert data.startswith(b"PK")


def test_packs_api_unknown_pack_raises_keyerror_for_handler_404_mapping():
    for helper in [pack_detail, pack_fixture_validation, pack_export_bundle]:
        try:
            helper("missing")
        except KeyError as exc:
            assert "missing" in str(exc)
        else:
            raise AssertionError(f"{helper.__name__} should raise KeyError for missing pack")
