import json
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = ROOT / "docs" / "acceptance"
VALIDATOR = ROOT / "scripts" / "validate_acceptance_evidence.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("acceptance_evidence_validator_test", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_splunk_indexed_marker_proof_is_not_sso_html_when_present():
    proof = ACCEPTANCE / "splunk-indexed-marker-proof.json"
    if not proof.exists():
        return

    data = json.loads(proof.read_text())
    assert data.get("content_type") != "text/html; charset=utf-8"
    assert "<!DOCTYPE html" not in data.get("body_prefix", "")
    assert data.get("result_count", 0) > 0
    assert data.get("marker")
    assert data.get("search")


def test_splunk_validator_rejects_sso_html_as_marker_proof():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "splunk-indexed-marker-proof.json"
        proof.write_text(json.dumps({
            "content_type": "text/html; charset=utf-8",
            "body_prefix": "<!DOCTYPE html><title>Login</title>",
            "marker": "sc4s-acceptance-test",
            "search": 'index=* "SC4S_ACCEPTANCE_MARKER" "sc4s-acceptance-test"',
            "result_count": 1,
            "results": [{"_raw": "sc4s-acceptance-test"}],
        }))

        findings = validator.validate_splunk_proof(proof)

    assert any(not finding.ok and "login/SSO" in finding.detail for finding in findings)


def test_splunk_validator_accepts_sanitized_indexed_marker_result():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "splunk-indexed-marker-proof.json"
        proof.write_text(json.dumps({
            "captured_at_utc": "2026-05-25T13:30:00Z",
            "marker": "sc4s-acceptance-test",
            "search": 'index=* "SC4S_ACCEPTANCE_MARKER" "sc4s-acceptance-test"',
            "status": 200,
            "result_count": 1,
            "results": [{
                "_time": "2026-05-25T13:29:00Z",
                "index": "main",
                "sourcetype": "cisco:asa",
                "source": "sc4s",
                "host": "dfir-sysmon-test",
                "_raw": "SC4S_ACCEPTANCE_MARKER marker_id=sc4s-acceptance-test",
            }],
        }))

        findings = validator.validate_splunk_proof(proof)

    assert all(finding.ok for finding in findings)


def test_splunk_validator_requires_indexed_event_metadata():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "splunk-indexed-marker-proof.json"
        proof.write_text(json.dumps({
            "captured_at_utc": "2026-05-25T13:30:00Z",
            "marker": "sc4s-acceptance-test",
            "search": 'index=* "SC4S_ACCEPTANCE_MARKER" "sc4s-acceptance-test"',
            "status": 200,
            "result_count": 1,
            "results": [{"_raw": "SC4S_ACCEPTANCE_MARKER marker_id=sc4s-acceptance-test"}],
        }))

        findings = validator.validate_splunk_proof(proof)

    assert any(not finding.ok and "metadata" in finding.detail for finding in findings)


def test_browser_validator_requires_authenticated_ui_and_api_evidence():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "browser-authenticated-route-live.json"
        proof.write_text(json.dumps({
            "public_url": "https://sc4s-manager.s6securitylabs.com/",
            "captured_at_utc": "2026-05-25T13:30:00Z",
            "auth_context_redacted": True,
            "artifact_dir": "docs/acceptance/evidence/browser-routes/20260525T133000Z",
            "route_inventory": [
                {"route": "/", "status": 200, "artifact_path": "artifacts/root.json", "title": "SC4S Manager", "api_path": "/api/stats", "api_summary": {"health": {"ok": True}}},
                {"route": "/library", "status": 200, "artifact_path": "artifacts/library.json", "title": "SC4S Manager", "api_path": "/api/catalogue", "api_summary": {"count": 1}},
                {"route": "/catalogue", "status": 200, "artifact_path": "artifacts/catalogue.json", "title": "SC4S Manager", "api_path": "/api/catalogue", "api_summary": {"count": 1}},
                {"route": "/packs", "status": 200, "artifact_path": "artifacts/packs.json", "title": "SC4S Manager", "api_path": "/api/packs", "api_summary": {"count": 1}},
                {"route": "/exports", "status": 200, "artifact_path": "artifacts/exports.json", "title": "SC4S Manager", "api_path": "/api/packs", "api_summary": {"count": 1}},
            ],
            "checks": {
                "authenticated_ui_load": {"status": 200, "title": "SC4S Manager", "artifact_path": "artifacts/root.json"},
                "authenticated_api_stats": {"status": 200, "artifact_path": "artifacts/api-stats.json", "body": {"status": "healthy"}},
                "unauthenticated_api_stats_redirect": {"status": 302, "redirect_url": "https://login.s6ops.com/application/o/authorize/"},
            },
        }))

        findings = validator.validate_browser_proof(proof)

    assert all(finding.ok for finding in findings)


def test_browser_validator_rejects_redirect_only_authenticated_claim():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "browser-authenticated-route-live.json"
        proof.write_text(json.dumps({
            "public_url": "https://sc4s-manager.s6securitylabs.com/",
            "captured_at_utc": "2026-05-25T13:30:00Z",
            "auth_context_redacted": True,
            "artifact_dir": "docs/acceptance/evidence/browser-routes/20260525T133000Z",
            "route_inventory": [
                {"route": "/", "status": 302, "artifact_path": "artifacts/root.json", "redirect_url": "https://login.s6ops.com/application/o/authorize/"},
                {"route": "/library", "status": 200, "artifact_path": "artifacts/library.json"},
                {"route": "/catalogue", "status": 200, "artifact_path": "artifacts/catalogue.json"},
                {"route": "/packs", "status": 200, "artifact_path": "artifacts/packs.json"},
                {"route": "/exports", "status": 200, "artifact_path": "artifacts/exports.json"},
            ],
            "checks": {
                "authenticated_ui_load": {"status": 302, "redirect_url": "https://login.s6ops.com/application/o/authorize/", "artifact_path": "artifacts/root.json"},
                "authenticated_api_stats": {"status": 302, "redirect_url": "https://login.s6ops.com/application/o/authorize/", "artifact_path": "artifacts/api-stats.json"},
                "unauthenticated_api_stats_redirect": {"status": 302, "redirect_url": "https://login.s6ops.com/application/o/authorize/"},
            },
        }))

        findings = validator.validate_browser_proof(proof)

    assert any(not finding.ok and "authenticated_ui_load" in finding.detail for finding in findings)
    assert any(not finding.ok and "route / appears to contain login redirect" in finding.detail for finding in findings)


def test_browser_validator_rejects_shell_only_route_without_api_readback():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "browser-authenticated-route-live.json"
        proof.write_text(json.dumps({
            "public_url": "https://sc4s-manager.s6securitylabs.com/",
            "captured_at_utc": "2026-05-25T13:30:00Z",
            "auth_context_redacted": True,
            "artifact_dir": "docs/acceptance/evidence/browser-routes/20260525T133000Z",
            "route_inventory": [
                {"route": "/", "status": 200, "artifact_path": "artifacts/root.json", "title": "SC4S Manager"},
                {"route": "/library", "status": 200, "artifact_path": "artifacts/library.json", "api_path": "/api/catalogue", "api_summary": {"count": 1}},
                {"route": "/catalogue", "status": 200, "artifact_path": "artifacts/catalogue.json", "api_path": "/api/catalogue", "api_summary": {"count": 1}},
                {"route": "/packs", "status": 200, "artifact_path": "artifacts/packs.json", "api_path": "/api/packs", "api_summary": {"count": 1}},
                {"route": "/exports", "status": 200, "artifact_path": "artifacts/exports.json", "api_path": "/api/packs", "api_summary": {"count": 1}},
            ],
            "checks": {
                "authenticated_ui_load": {"status": 200, "title": "SC4S Manager", "artifact_path": "artifacts/root.json"},
                "authenticated_api_stats": {"status": 200, "artifact_path": "artifacts/api-stats.json", "health": {"ok": True}},
                "unauthenticated_api_stats_redirect": {"status": 302, "redirect_url": "https://login.s6ops.com/application/o/authorize/"},
            },
        }))

        findings = validator.validate_browser_proof(proof)

    assert any(not finding.ok and "shell-only" in finding.detail for finding in findings)


def test_ci_functional_validator_accepts_complete_release_evidence():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "ci-functional-evidence.json"
        proof.write_text(json.dumps({
            "secrets_redacted": True,
            "expected_ui_pages": [{"route": "/"}],
            "ui_pages": [{"route": "/", "screenshot_path": "artifacts/ui/dashboard.png", "console_errors": [], "critical_api_failures": [], "status": 200}],
            "pack_matrix": [{"pack_id": "commvault_commcell", "status": "tested"}],
            "spl_results": [{"pack_id": "commvault_commcell", "marker": "sc4s-ci-abc", "result_count": 1, "results": [{"_raw": "sc4s-ci-abc"}]}],
        }))

        findings = validator.validate_ci_functional_proof(proof)

    assert all(finding.ok for finding in findings)


def test_ci_functional_validator_rejects_stale_profile_or_missing_screenshot():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "ci-functional-evidence.json"
        proof.write_text(json.dumps({
            "secrets_redacted": True,
            "expected_ui_pages": [{"route": "/"}, {"route": "/packs"}],
            "ui_pages": [{"route": "/", "screenshot_path": None, "console_errors": [], "critical_api_failures": [], "status": 200}],
            "pack_matrix": [{"pack_id": "commvault_commcell", "status": "stale", "reason": "last_updated is newer than last_tested"}],
            "spl_results": [{"pack_id": "commvault_commcell", "marker": "sc4s-ci-abc", "result_count": 0, "results": []}],
        }))

        findings = validator.validate_ci_functional_proof(proof)

    assert any(not finding.ok and "missing screenshot" in finding.detail for finding in findings)
    assert any(not finding.ok and "stale" in finding.detail for finding in findings)
    assert any(not finding.ok and "result_count" in finding.detail for finding in findings)


def complete_crud_journey_payload():
    return {
        "captured_at_utc": "2026-06-08T06:10:00Z",
        "scope": "V1 CRUD operator journeys: source, destination, route, live proof, delete, rollback, and UI coverage",
        "secrets_redacted": True,
        "journeys": [
            {
                "id": "J08-syslog-source-crud-lifecycle",
                "status": "covered",
                "persona": "SC4S operator",
                "goal": "Add, edit, validate, apply, and delete a syslog source.",
                "steps": ["baseline_absent", "add", "validate", "apply", "edit", "delete", "cleanup_verified"],
                "evidence": {
                    "baseline_absent": True,
                    "add": {"ok": True, "source_id": "v1_crud_asa_source"},
                    "edit": {"ok": True, "backup": "backups/source.bak"},
                    "delete": {"ok": True, "removed_paths": ["local/config/filters/v1_crud_asa_source.conf"]},
                    "cleanup": {"ok": True, "stale_rows_remaining": 0},
                    "audit_actions": ["add_source", "edit_source", "delete_source"],
                },
            },
            {
                "id": "J09-hec-destination-crud-lifecycle",
                "status": "covered",
                "persona": "Platform engineer",
                "goal": "Add, edit, validate, apply, and delete a Splunk HEC destination with token redaction.",
                "steps": ["baseline_absent", "add", "inventory_redacted", "edit", "delete", "cleanup_verified"],
                "evidence": {
                    "baseline_absent": True,
                    "add": {"ok": True, "destination_id": "V1CRUDHEC"},
                    "inventory": {"token": "[REDACTED]", "url": "https://splunk.example:8088"},
                    "edit": {"ok": True, "backup": "backups/hec.bak"},
                    "delete": {"ok": True, "removed_env_keys": ["SC4S_DEST_SPLUNK_HEC_V1CRUDHEC_TOKEN"]},
                    "cleanup": {"ok": True, "secret_leak_found": False},
                    "audit_actions": ["add_destination", "edit_destination", "delete_destination"],
                },
            },
            {
                "id": "J10-syslog-bsd-destination-crud-lifecycle",
                "status": "covered",
                "persona": "SC4S operator",
                "goal": "Add, edit, validate, apply, and delete a selected syslog/BSD destination.",
                "steps": ["baseline_absent", "add", "edit_select_mode", "selector_created", "delete", "cleanup_verified"],
                "evidence": {
                    "baseline_absent": True,
                    "add": {"ok": True, "destination_id": "V1CRUDSIEM"},
                    "edit": {"ok": True, "mode": "SELECT"},
                    "selector": {"ok": True, "path": "local/config/app_parsers/selectors/sc4s-lp-cisco_asa_d_syslog_v1crudsiem.conf"},
                    "delete": {"ok": True},
                    "cleanup": {"ok": True},
                },
            },
            {
                "id": "J11-source-pack-destination-route-lifecycle",
                "status": "covered",
                "persona": "SOC engineer",
                "goal": "Connect a source/pack/parser to a selected destination and prove live routing.",
                "steps": ["baseline_absent", "add_source", "add_destination", "create_route", "validate", "apply", "send_marker", "splunk_readback", "delete_route", "post_delete_nonmatch"],
                "evidence": {
                    "baseline_absent": True,
                    "route": {"ok": True, "source_id": "v1_crud_asa_source", "pack_id": "cisco_asa", "destination_id": "V1CRUDHEC"},
                    "validation": {"ok": True},
                    "control": {"ok": True},
                    "splunk_readback": {"ok": True, "marker": "sc4s-crud-journey-test", "result_count": 1, "index": "main", "sourcetype": "cisco:asa", "destination_id": "V1CRUDHEC"},
                    "delete": {"ok": True},
                    "post_delete": {"ok": True, "route_applied": False},
                },
            },
            {
                "id": "J12-pack-import-source-route-apply",
                "status": "covered",
                "persona": "SC4S operator",
                "goal": "Import a curated Library pack and deploy it through source/destination routing.",
                "steps": ["sync", "download", "validate_import", "stage", "preview", "apply", "splunk_readback", "rollback"],
                "evidence": {"import": {"ok": True}, "preview": {"ok": True}, "apply": {"ok": True}, "splunk_readback": {"ok": True, "result_count": 1}, "rollback": {"ok": True}},
            },
            {
                "id": "J13-failed-apply-rollback",
                "status": "covered",
                "persona": "Operator recovering from failed config",
                "goal": "Reject or roll back failed source/destination/route changes.",
                "steps": ["baseline", "invalid_change", "validation_failed", "rollback", "post_restore_health"],
                "evidence": {"baseline": {"ok": True}, "validation_failed": True, "rollback": {"ok": True}, "post_restore_health": {"ok": True}},
            },
            {
                "id": "J14-negative-security-validation",
                "status": "covered",
                "persona": "Security reviewer",
                "goal": "Prove CRUD mutations enforce auth, validation, redaction, and path safety.",
                "steps": ["unauth_denied", "invalid_inputs_rejected", "secret_redaction", "delete_path_traversal_rejected"],
                "evidence": {"unauthenticated_mutation_denied": True, "invalid_inputs_rejected": True, "secret_leak_found": False, "path_traversal_rejected": True},
            },
            {
                "id": "J15-ui-crud-journey-coverage",
                "status": "covered",
                "persona": "Browser operator",
                "goal": "Use UI forms for source, destination, route, validation, apply, evidence, and rollback workflows.",
                "steps": ["source_form", "destination_form", "route_form", "preview", "apply_result", "rollback_handle"],
                "evidence": {"ui_routes": ["/sources", "/destinations", "/routes"], "api_calls": ["POST /api/sources/onboard", "POST /api/destinations", "POST /api/routes"], "screenshots": ["artifacts/sources.png"]},
            },
        ],
    }


def test_crud_journey_validator_accepts_complete_v1_operator_evidence():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "crud-user-journeys-live.json"
        proof.write_text(json.dumps(complete_crud_journey_payload()))

        findings = validator.validate_crud_journey_proof(proof)

    assert all(finding.ok for finding in findings)


def test_crud_journey_validator_rejects_missing_delete_and_live_route_proof():
    validator = load_validator()
    payload = complete_crud_journey_payload()
    by_id = {journey["id"]: journey for journey in payload["journeys"]}
    by_id["J08-syslog-source-crud-lifecycle"]["evidence"].pop("delete")
    by_id["J11-source-pack-destination-route-lifecycle"]["evidence"].pop("splunk_readback")
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "crud-user-journeys-live.json"
        proof.write_text(json.dumps(payload))

        findings = validator.validate_crud_journey_proof(proof)

    assert any(not finding.ok and "J08" in finding.detail and "delete" in finding.detail for finding in findings)
    assert any(not finding.ok and "J11" in finding.detail and "splunk_readback" in finding.detail for finding in findings)


def complete_package_drill_payload():
    return {
        "ok": True,
        "version": "0.9.0",
        "artifact_sha256": "a" * 64,
        "install": {
            "started_at": "2026-06-14T10:00:00Z",
            "finished_at": "2026-06-14T10:05:00Z",
            "ok": True,
            "notes": "clean install on disposable LXC",
        },
        "upgrade": {"ok": True},
        "rollback": {"ok": True},
        "service_state": {
            "manager": "active",
            "control_daemon": "active",
        },
        "state_preservation": {
            "imports": True,
            "backups": True,
            "audit": True,
        },
        "redaction": {
            "findings": [],
        },
        "commands": [
            {"argv": ["bash", "deploy/install/install.sh", "--execute"], "ok": True, "mode": "live", "stdout_summary": "", "stderr_summary": ""},
        ],
    }


def test_package_drill_validator_accepts_complete_evidence():
    validator = load_validator()
    findings = validator.validate_package_drill_proof(None)
    assert not all(finding.ok for finding in findings), "validator must fail when no drill evidence is on disk"
    assert any("missing package drill evidence" in finding.detail for finding in findings)


def test_package_drill_validator_accepts_valid_payload():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "package-install-20260614T100000Z.json"
        proof.write_text(json.dumps(complete_package_drill_payload()))
        findings = validator.validate_package_drill_proof(proof)
    assert all(finding.ok for finding in findings), [f.detail for f in findings if not f.ok]


def test_package_drill_validator_rejects_missing_required_fields():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "package-install-20260614T100000Z.json"
        payload = complete_package_drill_payload()
        payload.pop("service_state")
        proof.write_text(json.dumps(payload))
        findings = validator.validate_package_drill_proof(proof)
    assert any(not finding.ok and "service_state" in finding.detail for finding in findings)


def test_require_package_drill_flag_fails_without_evidence():
    """--require-package-drill must fail with a clear missing-evidence message."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--require-package-drill"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "package" in output.lower() or "drill" in output.lower()


def test_next_release_evidence_validator_accepts_required_shape():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "library-health-live.json"
        proof.write_text(json.dumps({
            "ok": True,
            "captured_at": "2026-06-14T10:00:00Z",
            "source_health": {"overall_ok": True},
            "curated_import_apply": {"ok": True},
            "broken_source": {"ok": False, "error_code": "http_not_found"},
            "trust_semantics": {"remote_metadata_can_set_local_is_verified": False},
            "redaction": {"findings": []},
        }))
        findings = validator.validate_next_release_evidence(
            proof,
            "library health",
            ("ok", "captured_at", "source_health", "curated_import_apply", "broken_source", "trust_semantics", "redaction"),
        )
    assert all(finding.ok for finding in findings), [f.detail for f in findings if not f.ok]


def test_next_release_evidence_validator_rejects_missing_fields():
    validator = load_validator()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "source-preview-live.json"
        proof.write_text(json.dumps({"ok": True, "captured_at": "2026-06-14T10:00:00Z", "good_path": {}}))
        findings = validator.validate_next_release_evidence(
            proof,
            "source preview",
            ("ok", "captured_at", "good_path", "fallback_path", "redaction"),
        )
    assert any(not finding.ok and "fallback_path" in finding.detail for finding in findings)
    assert any(not finding.ok and "redaction" in finding.detail for finding in findings)


def test_require_next_release_flags_fail_without_evidence():
    import subprocess, sys
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--require-runtime-dashboard",
            "--require-source-preview",
            "--require-library-health",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "runtime dashboard" in output
    assert "source preview" in output
    assert "library health" in output
