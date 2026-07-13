import importlib.util
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "browser_route_acceptance.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("browser_route_acceptance_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_detect_auth_mode_prefers_manual_token_then_api_then_proxy():
    mod = load_runner_module()
    args = SimpleNamespace(
        manual_token_env="SC4S_MANAGER_MANUAL_LOGIN_TOKEN",
        api_token_env="SC4S_MANAGER_API_TOKEN",
        proxy_secret_env="SC4S_MANAGER_PROXY_SECRET",
        proxy_groups_env="SC4S_MANAGER_ADMIN_GROUPS",
    )
    with mock.patch.dict(os.environ, {
        "SC4S_MANAGER_MANUAL_LOGIN_TOKEN": "manual",
        "SC4S_MANAGER_API_TOKEN": "api",
        "SC4S_MANAGER_PROXY_SECRET": "proxy",
        "SC4S_MANAGER_ADMIN_GROUPS": "admins",
    }, clear=True):
        assert mod.detect_auth_mode(args) == "manual-token"
    with mock.patch.dict(os.environ, {
        "SC4S_MANAGER_API_TOKEN": "api",
        "SC4S_MANAGER_PROXY_SECRET": "proxy",
        "SC4S_MANAGER_ADMIN_GROUPS": "admins",
    }, clear=True):
        assert mod.detect_auth_mode(args) == "api-token"
    with mock.patch.dict(os.environ, {
        "SC4S_MANAGER_PROXY_SECRET": "proxy",
        "SC4S_MANAGER_ADMIN_GROUPS": "admins",
    }, clear=True):
        assert mod.detect_auth_mode(args) == "proxy"


def test_build_route_specs_adds_first_pack_and_catalogue_detail():
    mod = load_runner_module()
    routes = mod.build_route_specs(
        {"packs": [{"id": "fortinet_fortigate", "display_name": "FortiGate"}]},
        {"entries": [{"id": "cisco_asa", "display_name": "Cisco ASA"}]},
    )
    route_paths = [item["route"] for item in routes]
    assert route_paths[:5] == ["/", "/library", "/catalogue", "/packs", "/exports"]
    assert "/packs/fortinet_fortigate" in route_paths
    assert "/catalogue/cisco_asa" in route_paths


def test_sanitize_payload_redacts_tokens_and_session_cookie_values():
    mod = load_runner_module()
    payload = {
        "authorization": "Bearer abc123",
        "auth_mode": "manual-token",
        "nested": {
            "cookie": "sc4s_manual_session=manual-secret; other=1",
            "body_prefix": "Authorization: Bearer abc123...ken: secret-value",
        },
        "ok": True,
    }
    redacted = mod.sanitize_payload(payload)
    assert redacted["authorization"] == mod.REDACTED
    assert redacted["auth_mode"] == "manual-token"
    assert mod.REDACTED in redacted["nested"]["cookie"]
    assert "abc123" not in json.dumps(redacted)
    assert "secret-value" not in json.dumps(redacted)


def test_sanitize_payload_redacts_oauth_authorization_query_material():
    mod = load_runner_module()
    payload = {
        "body_prefix": '<a href="https://login.s6ops.com/application/o/authorize/?client_id=abc&redirect_uri=https%3A%2F%2Fexample.invalid%2Fcallback&response_type=code&scope=openid&state=opaque-state">Found</a>',
        "redirect_url": "https://login.s6ops.com/application/o/authorize/?client_id=abc&state=opaque-state",
    }
    redacted = mod.sanitize_payload(payload)
    rendered = json.dumps(redacted)
    assert "login.s6ops.com/application/o/authorize/" in rendered
    assert "[REDACTED_OAUTH_QUERY]" in rendered
    assert "client_id=abc" not in rendered
    assert "redirect_uri=" not in rendered
    assert "opaque-state" not in rendered


def test_login_url_requires_exact_https_authentik_boundary():
    mod = load_runner_module()
    assert mod.is_login_url("https://login.s6ops.com/application/o/authorize/")
    assert not mod.is_login_url("https://login.s6ops.com.attacker.invalid/application/o/authorize/")
    assert not mod.is_login_url("https://login.s6ops.com@attacker.invalid/application/o/authorize/")
    assert not mod.is_login_url("http://login.s6ops.com/application/o/authorize/")
    assert not mod.is_login_url("https://login.s6ops.com/other")


def test_error_url_removes_credentials_query_and_fragment():
    mod = load_runner_module()
    safe = mod.safe_url_for_error("https://user:password@example.invalid/path?login_token=secret#fragment")
    assert safe == "https://example.invalid/path"
    assert "password" not in safe
    assert "secret" not in safe


def test_validate_acceptance_evidence_rejects_oauth_authorization_query_leak():
    validator_spec = importlib.util.spec_from_file_location("acceptance_validator_test", ROOT / "scripts" / "validate_acceptance_evidence.py")
    assert validator_spec is not None and validator_spec.loader is not None
    validator = importlib.util.module_from_spec(validator_spec)
    sys.modules[validator_spec.name] = validator
    validator_spec.loader.exec_module(validator)
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "browser-public-route-live.json"
        proof.write_text(json.dumps({
            "results": [
                {
                    "status": 302,
                    "body_prefix": "https://login.s6ops.com/application/o/authorize/?client_id=abc&state=opaque",
                }
            ]
        }))
        finding = validator.text_has_secret_shape(proof)
    assert finding is not None
    assert "unredacted secret" in finding


def test_summarize_api_payload_reports_counts_and_safe_first_items():
    mod = load_runner_module()
    summary = mod.summarize_api_payload(
        {
            "count": 2,
            "packs": [
                {"id": "fortinet_fortigate", "display_name": "FortiGate", "vendor": "Fortinet", "product": "FortiGate"},
                {"id": "cisco_asa", "display_name": "Cisco ASA", "vendor": "Cisco", "product": "ASA"},
            ],
        },
        kind="packs_list",
    )
    assert summary["count"] == 2
    assert summary["first_pack"]["id"] == "fortinet_fortigate"
    assert summary["first_pack"]["display_name"] == "FortiGate"


def test_validate_browser_proof_accepts_runner_shaped_artifact():
    mod = load_runner_module()
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "browser-authenticated-route-live.json"
        proof.write_text(json.dumps({
            "public_url": "https://sc4s-manager.s6securitylabs.com/",
            "captured_at_utc": "2026-06-01T12:00:00Z",
            "auth_context_redacted": True,
            "artifact_dir": "docs/acceptance/evidence/browser-routes/20260601T120000Z",
            "route_inventory": [
                {"route": "/", "status": 200, "artifact_path": "artifacts/root.json", "title": "SC4S Manager", "api_path": "/api/stats", "api_summary": {"health": {"ok": True}}},
                {"route": "/library", "status": 200, "artifact_path": "artifacts/library.json", "title": "SC4S Manager", "api_path": "/api/catalogue", "api_summary": {"count": 1}},
                {"route": "/catalogue", "status": 200, "artifact_path": "artifacts/catalogue.json", "title": "SC4S Manager", "api_path": "/api/catalogue", "api_summary": {"count": 1}},
                {"route": "/packs", "status": 200, "artifact_path": "artifacts/packs.json", "title": "SC4S Manager", "api_path": "/api/packs", "api_summary": {"count": 1}},
                {"route": "/exports", "status": 200, "artifact_path": "artifacts/exports.json", "title": "SC4S Manager", "api_path": "/api/packs", "api_summary": {"count": 1}},
            ],
            "checks": {
                "authenticated_ui_load": {
                    "status": 200,
                    "artifact_path": "artifacts/root.json",
                    "title": "SC4S Manager",
                },
                "authenticated_api_stats": {
                    "status": 200,
                    "artifact_path": "artifacts/api-stats.json",
                    "health": {"ok": True},
                },
                "unauthenticated_api_stats_redirect": {
                    "status": 403,
                    "body_prefix": "Access denied by edge before login.s6ops.com redirect",
                    "redirect_url": "https://login.s6ops.com/application/o/authorize/",
                },
            },
        }))
        validator_spec = importlib.util.spec_from_file_location("acceptance_validator_test", ROOT / "scripts" / "validate_acceptance_evidence.py")
        assert validator_spec is not None and validator_spec.loader is not None
        validator = importlib.util.module_from_spec(validator_spec)
        sys.modules[validator_spec.name] = validator
        validator_spec.loader.exec_module(validator)
        findings = validator.validate_browser_proof(proof)
    assert all(item.ok for item in findings)


def test_prepare_authenticated_session_auto_falls_back_to_direct_mode():
    mod = load_runner_module()
    args = mod.parse_args(["--auth-mode", "auto", "--internal-base-url", "http://127.0.0.1:18090"])
    runner = mod.BrowserRouteRunner(args)
    with mock.patch.object(mod, "detect_auth_mode", side_effect=mod.AcceptanceError("no env")):
        with mock.patch.object(runner, "internal_base_supports_direct_access", return_value=True):
            identity = runner.prepare_authenticated_session()
    assert runner.auth_mode == "direct"
    assert runner.auth_source == "internal-base-direct"
    assert identity["mode"] == "direct"
    assert identity["base_url"] == "http://127.0.0.1:18090/"


def test_fetch_route_api_falls_back_from_missing_library_endpoint():
    mod = load_runner_module()
    args = mod.parse_args(["--auth-mode", "direct", "--internal-base-url", "http://127.0.0.1:18090"])
    runner = mod.BrowserRouteRunner(args)
    spec = next(item for item in mod.STATIC_ROUTE_SPECS if item["route"] == "/library")
    missing = mod.FetchResult(
        url="http://127.0.0.1:18090/api/library/catalogue?source_id=official",
        status=404,
        final_url="http://127.0.0.1:18090/api/library/catalogue?source_id=official",
        headers={},
        body_text='{"error": "not found"}',
        content_type="application/json; charset=utf-8",
    )
    fallback_payload = {"count": 1, "entries": [{"id": "a10", "display_name": "a10 a10", "vendor": "a10", "product": "a10"}]}
    fallback = mod.FetchResult(
        url="http://127.0.0.1:18090/api/catalogue",
        status=200,
        final_url="http://127.0.0.1:18090/api/catalogue",
        headers={},
        body_text=json.dumps(fallback_payload),
        content_type="application/json; charset=utf-8",
    )
    with mock.patch.object(runner, "fetch_absolute", side_effect=[missing, fallback]):
        result, payload, path, kind, reason = runner.fetch_route_api(spec)
    assert result.status == 200
    assert payload == fallback_payload
    assert path == "/api/catalogue"
    assert kind == "catalogue_list"
    assert "falling back to catalogue read-back" in reason


def test_build_journey_matrix_maps_user_journeys_to_route_and_api_evidence():
    mod = load_runner_module()
    public_payload = {
        "public_url": "https://sc4s-manager.s6securitylabs.com/",
        "results": [
            {"name": "public_root", "status": 302},
            {"name": "public_health", "status": 403},
            {"name": "public_api_stats", "status": 302},
        ],
    }
    routes = []
    for route, api_kind in [
        ("/", "stats"),
        ("/library", "library_catalogue"),
        ("/catalogue", "catalogue_list"),
        ("/catalogue/cisco_asa", "catalogue_detail"),
        ("/packs", "packs_list"),
        ("/packs/fortinet_fortigate", "pack_detail"),
        ("/exports", "packs_list"),
    ]:
        routes.append({
            "route": route,
            "status": 200,
            "api_status": 200,
            "api_path": f"/api/{api_kind}",
            "api_kind": api_kind,
            "api_summary": {"kind": api_kind},
            "artifact_path": f"docs/acceptance/evidence/browser-routes/run/{mod.route_slug(route)}.json",
        })
    auth_payload = {
        "authenticated_base_url": "http://127.0.0.1:18090/",
        "artifact_dir": "docs/acceptance/evidence/browser-routes/run",
        "auth_mode": "direct",
        "auth_source": "internal-base-direct",
        "route_inventory": routes,
        "checks": {"unauthenticated_api_stats_redirect": {"status": 302}},
    }
    matrix = mod.build_journey_matrix(public_payload, auth_payload, "2026-06-03T12:00:00Z")
    ids = {journey["id"] for journey in matrix["journeys"]}
    assert "J05-library-import-validate-apply-separation" in ids
    assert "J07-negative-auth-and-mutation-safety" in ids
    assert all(journey["artifact_paths"] for journey in matrix["journeys"])
    assert next(j for j in matrix["journeys"] if j["id"] == "J05-library-import-validate-apply-separation")["ui_routes"] == ["/library"]
    markdown = mod.render_journey_markdown(matrix)
    assert "protected-route split" in markdown
    assert "J03-source-catalogue-browse-detail" in markdown


def test_validate_e2e_journey_proof_requires_all_key_journeys():
    validator_spec = importlib.util.spec_from_file_location("acceptance_validator_test", ROOT / "scripts" / "validate_acceptance_evidence.py")
    assert validator_spec is not None and validator_spec.loader is not None
    validator = importlib.util.module_from_spec(validator_spec)
    sys.modules[validator_spec.name] = validator
    validator_spec.loader.exec_module(validator)
    required = [
        "J01-public-protection",
        "J02-dashboard-operator-landing",
        "J03-source-catalogue-browse-detail",
        "J04-pack-detail-inspection",
        "J05-library-import-validate-apply-separation",
        "J06-export-validation-evidence",
        "J07-negative-auth-and-mutation-safety",
    ]
    with TemporaryDirectory() as tmp:
        proof = Path(tmp) / "e2e-ui-user-journeys-live.json"
        proof.write_text(json.dumps({
            "captured_at_utc": "2026-06-03T12:00:00Z",
            "scope": "SC4S Manager protected-route split: public denial plus internal proof",
            "journeys": [
                {
                    "id": journey_id,
                    "persona": "tester",
                    "goal": "prove route",
                    "ui_routes": ["/library" if journey_id == "J05-library-import-validate-apply-separation" else "/"],
                    "api_readback": ["/api/stats"],
                    "expected_evidence": "unauthenticated_api_stats_redirect observed; mutation/apply/restart endpoints are not invoked",
                    "status": "covered",
                    "artifact_paths": ["docs/acceptance/evidence/browser-routes/run/root.json"],
                    "test_names": ["frontend/src/routes/UserJourneyCoverage.test.tsx"],
                }
                for journey_id in required
            ],
        }))
        browser = Path(tmp) / "browser-authenticated-route-live.json"
        browser.write_text(json.dumps({
            "public_url": "https://sc4s-manager.s6securitylabs.com/",
            "captured_at_utc": "2026-06-03T12:00:00Z",
            "auth_context_redacted": True,
            "artifact_dir": "docs/acceptance/evidence/browser-routes/run",
            "route_inventory": [
                {"route": "/", "status": 200, "artifact_path": "root.json", "api_path": "/api/stats", "api_summary": {"health": {"ok": True}}},
                {"route": "/library", "status": 200, "artifact_path": "library.json", "api_path": "/api/catalogue", "api_summary": {"count": 1}},
                {"route": "/catalogue", "status": 200, "artifact_path": "catalogue.json", "api_path": "/api/catalogue", "api_summary": {"count": 1}},
                {"route": "/catalogue/a10", "status": 200, "artifact_path": "catalogue-a10.json", "api_path": "/api/catalogue/a10", "api_summary": {"validation_state": "catalogued_only"}},
                {"route": "/packs", "status": 200, "artifact_path": "packs.json", "api_path": "/api/packs", "api_summary": {"count": 1}},
                {"route": "/packs/commvault_commcell", "status": 200, "artifact_path": "pack-detail.json", "api_path": "/api/packs/commvault_commcell", "api_summary": {"test_event_set_count": 1}},
                {"route": "/exports", "status": 200, "artifact_path": "exports.json", "api_path": "/api/packs", "api_summary": {"count": 1}},
            ],
        }))
        findings = validator.validate_e2e_journey_proof(proof, browser)
    assert all(item.ok for item in findings)
