import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.pack_validation import default_validation_evidence_dir, validate_packs_bundle
from sc4s_manager.packs import (
    load_packs,
    pack_by_id,
    validate_field_contract,
    validate_logging_presets,
)


@pytest.fixture()
def pack_root(tmp_path: Path) -> Path:
    src = ROOT / "packs"
    dst = tmp_path / "packs"
    shutil.copytree(src, dst)
    return dst


def load_commvault(pack_root: Path) -> dict:
    return pack_by_id(load_packs(pack_root), "commvault_commcell")


def raw_commvault(pack_root: Path) -> dict:
    manifest = pack_root / "commvault_commcell" / "pack.json"
    pack = json.loads(manifest.read_text())
    pack["pack_dir"] = str(manifest.parent)
    pack["manifest_path"] = str(manifest)
    return pack


def _artifact_index(pack: dict) -> dict[str, dict]:
    return {artifact["id"]: artifact for artifact in pack["export_artifacts"]}


def write_runtime_helpers(tmp_path: Path) -> tuple[str, str, str]:
    syslog_script = tmp_path / "mock_syslog_validate.py"
    syslog_script.write_text(textwrap.dedent(
        """
        import json
        import sys
        from pathlib import Path

        files = json.loads(Path(sys.argv[1]).read_text())
        print(json.dumps({"checked": files, "pack_id": sys.argv[2]}))
        """
    ).strip() + "\n")

    send_script = tmp_path / "mock_runtime_send.py"
    send_script.write_text(textwrap.dedent(
        """
        import json
        import sys
        from pathlib import Path

        payload_path = Path(sys.argv[1])
        marker = sys.argv[2]
        runtime_root = Path(sys.argv[3])
        search_name = payload_path.stem
        state_path = runtime_root / "mock_runtime_state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {"events": []}
        lines = [line.strip() for line in payload_path.read_text().splitlines() if line.strip()]
        state["events"].append({"event_set_id": search_name, "marker": marker, "line_count": len(lines), "payload_path": str(payload_path)})
        state_path.write_text(json.dumps(state))
        print(json.dumps({"ok": True, "marker": marker, "event_set_id": search_name, "line_count": len(lines)}))
        """
    ).strip() + "\n")

    splunk_script = tmp_path / "mock_splunk_search.py"
    splunk_script.write_text(textwrap.dedent(
        """
        import json
        import re
        import sys
        from pathlib import Path

        search = sys.argv[1]
        marker = sys.argv[2]
        family_id = sys.argv[3]
        search_name = sys.argv[4]
        runtime_root = Path(sys.argv[5])
        state_path = runtime_root / "mock_runtime_state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {"events": []}
        if not state.get("events"):
            print(json.dumps({"result_count": 0, "results": [], "job": {"search_name": search_name}}))
            raise SystemExit(0)
        row = {"_raw": f"SC4S_ACCEPTANCE_MARKER {marker}", "marker": marker, "search_name": search_name, "family_id": family_id}
        if search_name == "required_fields_search":
            for field in re.findall(r"as ([A-Za-z0-9_]+_present)", search):
                row[field] = 1
        if search_name == "sourcetype_search":
            match = re.search(r'sourcetype=\"([^\"]+)\"', search)
            if match:
                row["sourcetype"] = match.group(1)
        print(json.dumps({"result_count": 1, "results": [row], "job": {"search_name": search_name, "events_seen": len(state.get("events", []))}}))
        """
    ).strip() + "\n")

    return str(syslog_script), str(send_script), str(splunk_script)


def test_default_validation_evidence_dir_falls_back_when_base_path_is_unwritable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    stale = tmp_path / "sc4s-manager-validation-evidence"
    stale.mkdir()
    stale.chmod(0o500)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    evidence_dir = default_validation_evidence_dir()

    assert evidence_dir.is_dir()
    assert evidence_dir.parent == tmp_path
    assert evidence_dir != stale
    assert evidence_dir.name.startswith("sc4s-manager-validation-evidence.")


def test_validate_packs_cli_defaults_to_temp_evidence_and_runtime_paths(tmp_path: Path):
    env = os.environ.copy()
    env["TMPDIR"] = str(tmp_path)

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_packs.py"), "--pack-id", "commvault_commcell", "--format", "json"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    bundle = json.loads(proc.stdout)
    report = bundle["packs"][0]
    evidence_json = Path(report["evidence"]["json"])
    evidence_markdown = Path(report["evidence"]["markdown"])
    runtime_details = next(check["details"] for check in report["checks"] if check["stage"] == "runtime_artifact_install")
    runtime_root = Path(runtime_details["runtime_root"])

    assert evidence_json.is_file()
    assert evidence_markdown.is_file()
    assert evidence_json.is_relative_to(tmp_path)
    assert evidence_markdown.is_relative_to(tmp_path)
    assert runtime_root.is_relative_to(tmp_path)
    assert "catalogue/generated/validation" not in str(evidence_json)
    assert "catalogue/generated/validation" not in str(runtime_root)


def test_validation_bundle_passes_and_writes_evidence(pack_root: Path, tmp_path: Path):
    packs = load_packs(pack_root)
    evidence_dir = tmp_path / "evidence"

    bundle = validate_packs_bundle(packs, evidence_dir=evidence_dir)

    assert bundle["ok"] is True
    assert bundle["pack_count"] == len(packs)
    report = next(item for item in bundle["packs"] if item["pack_id"] == "commvault_commcell")
    assert report["pack_id"] == "commvault_commcell"
    assert report["ok"] is True
    assert [check["stage"] for check in report["checks"]] == [
        "manifest",
        "fixtures",
        "event_family_counts",
        "export_manifest",
        "splunk_knowledge",
        "sc4s_artifacts",
        "syslog_ng_syntax",
        "runtime_artifact_install",
        "runtime_pack_validation",
        "splunk_readback",
    ]
    assert report["checks"][6]["details"]["status"] == "skipped"
    assert report["checks"][7]["details"]["status"] == "passed"
    assert report["checks"][8]["details"]["status"] == "skipped"
    assert report["checks"][9]["details"]["status"] == "skipped"
    assert Path(report["evidence"]["json"]).is_file()
    assert Path(report["evidence"]["markdown"]).is_file()
    markdown = Path(report["evidence"]["markdown"]).read_text()
    assert "# Validation evidence: commvault_commcell" in markdown
    payload = json.loads(Path(report["evidence"]["json"]).read_text())
    assert payload["pack_id"] == "commvault_commcell"


def test_validation_fails_cleanly_on_fixture_mismatch(pack_root: Path, tmp_path: Path):
    fixture = pack_root / "commvault_commcell" / "test-events" / "commvault_test_events.txt"
    fixture.write_text(fixture.read_text() + "\nAlerts: duplicate marker <MARKER>_ALERT\n")
    pack = raw_commvault(pack_root)

    bundle = validate_packs_bundle([pack], evidence_dir=tmp_path / "evidence")

    report = bundle["packs"][0]
    assert bundle["ok"] is False
    assert report["ok"] is False
    assert report["error"]["stage"] == "fixtures"
    assert "expected 3 events, found 4" in report["error"]["message"]


def test_validation_fails_cleanly_on_missing_props_sourcetype(pack_root: Path, tmp_path: Path):
    props = pack_root / "commvault_commcell" / "splunk" / "default" / "props.conf"
    props.write_text(props.read_text().replace("\n[commvault:commcell:alerts]\nSHOULD_LINEMERGE = false\nKV_MODE = json\nAUTO_KV_JSON = true\nTIME_PREFIX = \"Utctimestamp\":\"\nTIME_FORMAT = %s\nEVAL-cv_event_type = coalesce(cv_event_type, \"alert\")\nEVAL-action = coalesce(action, \"alert\")\n", "\n"))
    packs = load_packs(pack_root)

    bundle = validate_packs_bundle(packs, evidence_dir=tmp_path / "evidence")

    report = bundle["packs"][0]
    assert bundle["ok"] is False
    assert report["error"]["stage"] == "splunk_knowledge"
    assert "props.conf missing required sourcetype stanza(s): commvault:commcell:alerts" == report["error"]["message"]


def test_validation_fails_cleanly_on_parser_sourcetype_mismatch(pack_root: Path, tmp_path: Path):
    parser = pack_root / "commvault_commcell" / "sc4s" / "app_parsers" / "syslog" / "app-commvault_commcell.conf"
    parser.write_text(
        parser.read_text().replace("commvault:commcell:events", "commvault:commcell:event", 1)
    )
    packs = load_packs(pack_root)

    bundle = validate_packs_bundle(packs, evidence_dir=tmp_path / "evidence")

    report = bundle["packs"][0]
    assert bundle["ok"] is False
    assert report["error"]["stage"] == "sc4s_artifacts"
    assert "commvault:commcell:events" in report["error"]["message"]


def test_release_mode_fails_when_runtime_checks_are_skipped(pack_root: Path, tmp_path: Path):
    packs = load_packs(pack_root)

    bundle = validate_packs_bundle(packs, evidence_dir=tmp_path / "evidence", release_mode=True)

    report = bundle["packs"][0]
    assert bundle["ok"] is False
    assert report["error"]["stage"] == "syslog_ng_syntax"
    assert "required in release mode" in report["error"]["message"]


def test_validation_bundle_runs_runtime_install_injection_and_splunk_readback(pack_root: Path, tmp_path: Path):
    packs = load_packs(pack_root)
    syslog_script, send_script, splunk_script = write_runtime_helpers(tmp_path)
    evidence_dir = tmp_path / "evidence"
    runtime_root = tmp_path / "runtime"

    bundle = validate_packs_bundle(
        packs,
        evidence_dir=evidence_dir,
        syslog_ng_validate_cmd=f"{sys.executable} {syslog_script} {{files_json}} {{pack_id}}",
        runtime_root=runtime_root,
        runtime_send_cmd=f"{sys.executable} {send_script} {{payload_path}} {{marker}} {{runtime_root}}",
        splunk_search_cmd=f"{sys.executable} {splunk_script} {{search}} {{marker}} {{family_id}} {{search_name}} {{runtime_root}}",
        listener_host="127.0.0.1",
        release_mode=True,
    )

    assert bundle["ok"] is True
    report = bundle["packs"][0]
    checks = {check["stage"]: check["details"] for check in report["checks"]}
    assert checks["syslog_ng_syntax"]["status"] == "passed"
    assert checks["runtime_artifact_install"]["status"] == "passed"
    assert checks["runtime_pack_validation"]["status"] == "passed"
    assert checks["splunk_readback"]["status"] == "passed"
    assert checks["runtime_pack_validation"]["marker"].startswith("sc4s-pack-commvault_commcell-")
    assert len(checks["runtime_pack_validation"]["event_sets"]) == 1
    assert checks["splunk_readback"]["query_count"] == 7
    installed_targets = [item["target_path"] for item in checks["runtime_artifact_install"]["installed_artifacts"]]
    assert any(str(runtime_root / "commvault_commcell" / "local/config/app_parsers/syslog/app-commvault_commcell.conf") == target for target in installed_targets)
    assert Path(report["evidence"]["json"]).is_file()


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (
            lambda pack: pack["field_contract"]["cim"].update({"mapping_status": "unknown"}),
            "field_contract.cim.fields must be empty when mapping_status is unknown",
        ),
        (
            lambda pack: pack["field_contract"]["cim"].update({"mapping_status": "complete"}),
            "field_contract.cim.mapping_status cannot be complete while field mappings remain partial/unknown",
        ),
    ],
)
def test_validate_field_contract_rejects_dishonest_mapping_status(pack_root: Path, mutator, expected: str) -> None:
    pack = raw_commvault(pack_root)
    mutator(pack)

    with pytest.raises(ValueError, match=expected):
        validate_field_contract(pack["field_contract"], pack)


def test_validate_field_contract_rejects_complete_cim_when_required_common_fields_are_missing(pack_root: Path) -> None:
    pack = raw_commvault(pack_root)
    pack["normalized_fields"].pop("severity")
    pack["field_contract"]["cim"]["mapping_status"] = "complete"
    for mapping in pack["field_contract"]["cim"]["fields"].values():
        mapping["status"] = "complete"
        if not mapping["source_fields"]:
            mapping["source_fields"] = ["synthetic_field"]

    with pytest.raises(ValueError, match="field_contract.cim.mapping_status cannot be complete while common SOC fields are still unmapped: severity"):
        validate_field_contract(pack["field_contract"], pack)


def test_validate_field_contract_requires_source_fields_for_partial_or_complete_mappings(pack_root: Path) -> None:
    pack = raw_commvault(pack_root)
    pack["field_contract"]["cim"]["fields"]["action"]["source_fields"] = []

    with pytest.raises(ValueError, match="field_contract.cim.action.source_fields must be non-empty when status is partial"):
        validate_field_contract(pack["field_contract"], pack)


def test_validate_logging_presets_rejects_default_enabled_reduction_preset(pack_root: Path) -> None:
    pack = raw_commvault(pack_root)
    enhanced = next(preset for preset in pack["logging_presets"] if preset["id"] == "enhanced")
    enhanced["enabled_by_default"] = True

    with pytest.raises(ValueError, match="logging preset enhanced cannot be enabled_by_default when it includes reduction_rules"):
        validate_logging_presets(
            pack["logging_presets"],
            _artifact_index(pack),
            {rule["id"] for rule in pack["reduction_rules"]},
        )
