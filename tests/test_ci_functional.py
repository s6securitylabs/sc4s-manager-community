import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.packs import load_packs, pack_by_id
from sc4s_manager.ci_functional import (
    build_basic_spl,
    build_ci_pack_matrix,
    build_run_manifest,
    build_splunk_lxc_plan,
    build_targeted_spl,
    expected_ui_pages,
    field_presence_alias,
    pack_artifact_hashes,
    splunk_field_expr,
    validate_ci_evidence,
)


def all_packs():
    return load_packs(ROOT / "packs")


def commvault_pack():
    return pack_by_id(all_packs(), "commvault_commcell")


def test_splunk_lxc_plan_is_disposable_and_uses_ephemeral_ci_only_credentials():
    plan = build_splunk_lxc_plan(
        ctid=1091,
        hostname="sc4s-manager-ci-splunk",
        splunk_image="splunk/splunk:10.2.3",
        admin_password="changeme-ci-only",
        indexes=["commvault", "sc4s_ci"],
        hec_token_name="sc4s-manager-ci-hec",
    )

    assert plan["disposable"] is True
    assert plan["ctid"] == 1091
    assert plan["hostname"] == "sc4s-manager-ci-splunk"
    assert plan["splunk"]["image"] == "splunk/splunk:10.2.3"
    assert plan["splunk"]["admin_password_policy"] == "ci_only_easy_password"
    assert plan["splunk"]["admin_password"] == "[REDACTED]"
    assert plan["splunk"]["hec_token_name"] == "sc4s-manager-ci-hec"
    assert plan["splunk"]["indexes"] == ["commvault", "sc4s_ci"]
    assert any("docker run" in command and "splunk/splunk:10.2.3" in command for command in plan["commands"])
    assert all("changeme-ci-only" not in json.dumps(command) for command in plan["commands"])
    assert any("SPLUNK_PASSWORD=[REDACTED]" in command for command in plan["commands"])


def test_splunk_lxc_plan_contains_readiness_hec_and_index_steps():
    plan = build_splunk_lxc_plan(
        ctid=1091,
        hostname="sc4s-manager-ci-splunk",
        splunk_image="splunk/splunk:10.2.3",
        admin_password="changeme-ci-only",
        indexes=["commvault"],
    )
    joined = "\n".join(plan["commands"])

    assert "pct create 1091" in joined
    assert "pct start 1091" in joined
    assert "apt-get install -y docker.io curl jq" in joined
    assert "docker run -d --name sc4s-manager-ci-splunk" in joined
    assert "until docker exec sc4s-manager-ci-splunk" in joined
    assert "http-event-collector enable" in joined
    assert "add index commvault" in joined
    assert "http-event-collector create sc4s-manager-ci-hec" in joined
    assert "10.10.100.251" not in joined


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"ctid": 0}, "ctid"),
        ({"hostname": ""}, "hostname"),
        ({"splunk_image": ""}, "splunk_image"),
        ({"indexes": []}, "index"),
    ],
)
def test_splunk_lxc_plan_rejects_unsafe_or_incomplete_inputs(kwargs, match):
    params = {
        "ctid": 1091,
        "hostname": "sc4s-manager-ci-splunk",
        "splunk_image": "splunk/splunk:10.2.3",
        "admin_password": "changeme-ci-only",
        "indexes": ["commvault"],
    }
    params.update(kwargs)
    with pytest.raises(ValueError, match=match):
        build_splunk_lxc_plan(**params)


def test_expected_ui_pages_include_static_pages_and_pack_detail_pages():
    pages = expected_ui_pages([commvault_pack()])
    routes = [page["route"] for page in pages]

    assert routes[:9] == ["/", "/library", "/catalogue", "/packs", "/onboarding-preview", "/sources", "/destinations", "/routes", "/exports"]
    assert "/packs/commvault_commcell" in routes
    assert all(page["screenshot_required"] is True for page in pages)
    assert {page["kind"] for page in pages} >= {"static", "pack_detail"}


def test_expected_ui_pages_match_frontend_nav_routes():
    layout = (ROOT / "frontend/src/components/AppLayout.tsx").read_text()
    nav_routes = re.findall(r"to: '([^']+)'", layout)
    inventory_routes = [page["route"] for page in expected_ui_pages(all_packs()) if page["kind"] == "static"]

    assert nav_routes == inventory_routes


def test_pack_matrix_flags_packs_whose_artifacts_changed_after_last_test():
    pack = copy.deepcopy(commvault_pack())
    pack["ci"] = {
        "last_updated": "2026-05-27T21:00:00Z",
        "last_tested": "2026-05-27T20:00:00Z",
        "tested_commit": "abc1234",
        "tested_artifact_hashes": {},
    }

    matrix = build_ci_pack_matrix([pack], release_mode=True)

    assert matrix[0]["pack_id"] == "commvault_commcell"
    assert matrix[0]["status"] == "stale"
    assert "last_updated is newer than last_tested" in matrix[0]["reason"]


def test_pack_matrix_flags_malformed_ci_timestamps():
    pack = copy.deepcopy(commvault_pack())
    pack["ci"] = {
        "last_updated": "not-a-date",
        "last_tested": "2026-05-27T20:00:00Z",
        "tested_commit": "abc1234",
        "tested_artifact_hashes": {},
    }

    matrix = build_ci_pack_matrix([pack], release_mode=True)

    assert matrix[0]["status"] == "stale"
    assert "invalid ci timestamp" in matrix[0]["reason"]


def test_pack_matrix_accepts_current_pack_test_metadata():
    pack = copy.deepcopy(commvault_pack())
    pack["ci"] = {
        "last_updated": "2026-05-27T20:00:00Z",
        "last_tested": "2026-05-27T21:00:00Z",
        "tested_commit": "abc1234",
        "tested_artifact_hashes": {"packs/commvault_commcell/pack.json": "sha256:example"},
    }

    matrix = build_ci_pack_matrix([pack], release_mode=True)

    assert matrix[0]["status"] == "selected"
    assert matrix[0]["required_index"] == "commvault"
    assert matrix[0]["event_sets"] == ["commvault_headerless_single_line"]
    assert matrix[0]["event_families"] == ["audit", "event", "alert"]


def test_spl_templates_are_targeted_to_index_marker_sourcetype_and_required_fields():
    pack = commvault_pack()
    marker = "sc4s-ci-20260527-abc"

    basic = build_basic_spl(pack, marker)
    targeted = build_targeted_spl(pack, marker)

    assert basic == 'index=commvault "sc4s-ci-20260527-abc" | stats count as count by index sourcetype source host'
    assert targeted["audit"]["sourcetype_search"] == 'index=commvault "sc4s-ci-20260527-abc" sourcetype="commvault:commcell:audittrail" | stats count as count by sourcetype'
    assert 'isnotnull(Opid)' in targeted["audit"]["required_fields_search"]
    assert 'sourcetype="commvault:commcell:alerts"' in targeted["alert"]["sourcetype_search"]


def test_all_packs_have_targeted_spl_for_every_event_family():
    marker = "sc4s-ci-template-test"
    for pack in all_packs():
        basic = build_basic_spl(pack, marker)
        targeted = build_targeted_spl(pack, marker)
        assert f"index={pack['default_index']}" in basic
        assert marker in basic
        assert set(targeted) == {family["id"] for family in pack["event_families"]}
        for family in pack["event_families"]:
            searches = targeted[family["id"]]
            assert pack["default_index"] in searches["sourcetype_search"]
            assert marker in searches["sourcetype_search"]
            assert family["expected_sourcetype"] in searches["sourcetype_search"]
            for field in family["required_fields"]:
                assert f"isnotnull({splunk_field_expr(field)})" in searches["required_fields_search"]
                assert f"as {field_presence_alias(field)}" in searches["required_fields_search"]


def test_pack_artifact_hashes_cover_manifest_exports_and_test_events():
    for pack in all_packs():
        hashes = pack_artifact_hashes(pack)
        expected_suffixes = {"pack.json"}
        expected_suffixes.update(artifact["source_path"] for artifact in pack["export_artifacts"])
        expected_suffixes.update(event_set["path"] for event_set in pack["test_event_sets"])
        for suffix in expected_suffixes:
            assert any(path.endswith(suffix) for path in hashes), suffix
        assert all(value.startswith("sha256:") for value in hashes.values())


def test_ci_cli_generates_v1_release_manifest(tmp_path):
    output = tmp_path / "ci-functional-manifest.json"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ci_functional_acceptance.py"), "--release-mode", "--output", str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    summary = json.loads(completed.stdout)
    manifest = json.loads(output.read_text())

    assert summary["ok"] is True
    assert manifest["release_mode"] is True
    assert manifest["generated_at_utc"]
    assert manifest["marker"].startswith("sc4s-ci-")
    assert manifest["required_indexes"] == sorted({pack["default_index"] for pack in all_packs()})
    assert manifest["ui_pages"]
    assert manifest["pack_matrix"]
    assert manifest["splunk_plan"]["disposable"] is True
    assert {pack["id"] for pack in all_packs()} <= set(manifest["spl_templates"])


def test_ci_evidence_validator_rejects_missing_screenshots_stale_packs_and_empty_spl():
    evidence = {
        "expected_ui_pages": [{"route": "/"}, {"route": "/packs"}],
        "ui_pages": [
            {"route": "/", "screenshot_path": "artifacts/ui/dashboard.png", "console_errors": [], "critical_api_failures": []},
            {"route": "/packs", "screenshot_path": None, "console_errors": [], "critical_api_failures": []},
        ],
        "pack_matrix": [
            {"pack_id": "commvault_commcell", "status": "stale", "reason": "last_updated is newer than last_tested"}
        ],
        "spl_results": [
            {"pack_id": "commvault_commcell", "marker": "sc4s-ci-abc", "result_count": 0, "results": []}
        ],
        "secrets_redacted": True,
    }

    findings = validate_ci_evidence(evidence, release_mode=True)

    assert any("missing screenshot" in finding["detail"] for finding in findings)
    assert any("stale" in finding["detail"] for finding in findings)
    assert any("result_count" in finding["detail"] for finding in findings)
    assert not all(finding["ok"] for finding in findings)


def test_ci_evidence_validator_rejects_skipped_pack_runtime_proof_in_release_mode():
    evidence = {
        "expected_ui_pages": [{"route": "/"}],
        "ui_pages": [{"route": "/", "screenshot_path": "artifacts/ui/dashboard.png", "console_errors": [], "critical_api_failures": [], "status": 200}],
        "pack_matrix": [{"pack_id": "commvault_commcell", "status": "skipped", "reason": "runtime validation not executed"}],
        "spl_results": [{"pack_id": "commvault_commcell", "marker": "sc4s-ci-abc", "result_count": 1, "results": [{"_raw": "sc4s-ci-abc"}]}],
        "secrets_redacted": True,
    }

    findings = validate_ci_evidence(evidence, release_mode=True)

    assert any("is skipped" in finding["detail"] for finding in findings)


def test_ci_evidence_validator_rejects_unredacted_secret_shapes():
    evidence = {
        "ui_pages": [{"route": "/", "screenshot_path": "a.png", "console_errors": [], "critical_api_failures": []}],
        "pack_matrix": [{"pack_id": "commvault_commcell", "status": "tested"}],
        "spl_results": [{"pack_id": "commvault_commcell", "marker": "sc4s-ci-abc", "result_count": 1, "results": [{"_raw": "sc4s-ci-abc"}]}],
        "secrets_redacted": True,
        "debug": "".join(["Author", "ization", ": Bearer ", "abc123"]),
    }

    findings = validate_ci_evidence(evidence, release_mode=True)

    assert any("unredacted secret" in finding["detail"] for finding in findings)


def test_ci_evidence_validator_rejects_missing_expected_routes_and_auth_redirects():
    evidence = {
        "expected_ui_pages": [{"route": "/"}, {"route": "/packs"}],
        "ui_pages": [
            {
                "route": "/",
                "screenshot_path": "artifacts/ui/dashboard.png",
                "console_errors": [],
                "critical_api_failures": [],
                "status": 302,
                "redirect_url": "https://login.s6ops.com/application/o/authorize/",
            }
        ],
        "pack_matrix": [{"pack_id": "commvault_commcell", "status": "tested"}],
        "spl_results": [{"pack_id": "commvault_commcell", "marker": "sc4s-ci-abc", "result_count": 1, "results": [{"_raw": "sc4s-ci-abc"}]}],
        "secrets_redacted": True,
    }

    findings = validate_ci_evidence(evidence, release_mode=True)

    assert any("missing UI evidence for expected route /packs" in finding["detail"] for finding in findings)
    assert any("authenticated page appears to be a login redirect" in finding["detail"] for finding in findings)


def test_ci_evidence_validator_accepts_complete_release_evidence():
    evidence = {
        "expected_ui_pages": [{"route": "/"}, {"route": "/packs"}],
        "ui_pages": [
            {"route": "/", "screenshot_path": "artifacts/ui/dashboard.png", "console_errors": [], "critical_api_failures": [], "status": 200},
            {"route": "/packs", "screenshot_path": "artifacts/ui/packs.png", "console_errors": [], "critical_api_failures": [], "status": 200},
        ],
        "pack_matrix": [
            {"pack_id": "commvault_commcell", "status": "tested", "reason": "targeted SPL passed"}
        ],
        "spl_results": [
            {"pack_id": "commvault_commcell", "marker": "sc4s-ci-abc", "result_count": 3, "results": [{"_raw": "sc4s-ci-abc"}]}
        ],
        "secrets_redacted": True,
    }

    findings = validate_ci_evidence(evidence, release_mode=True)

    assert findings == [{"ok": True, "detail": "CI functional evidence is valid"}]
