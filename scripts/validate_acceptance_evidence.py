#!/usr/bin/env python3
"""Validate final release acceptance evidence.

The validator intentionally checks only sanitized proof artifacts. It must not
read Splunk credentials, browser cookies, session exports, or manager tokens.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = ROOT / "docs" / "acceptance"
SPLUNK_PROOF = ACCEPTANCE / "splunk-indexed-marker-proof.json"
BROWSER_PROOF = ACCEPTANCE / "browser-authenticated-route-live.json"
E2E_JOURNEY_PROOF = ACCEPTANCE / "e2e-ui-user-journeys-live.json"
CI_FUNCTIONAL_PROOF = ACCEPTANCE / "ci-functional-evidence.json"
CRUD_JOURNEY_PROOF = ACCEPTANCE / "crud-user-journeys-live.json"
PACKAGE_DRILL_GLOB = "package-install-*.json"
PACKAGE_DRILL_TEMPLATE = ACCEPTANCE / "package-install-template.json"
RUNTIME_DASHBOARD_PROOF = ACCEPTANCE / "runtime-dashboard-live.json"
SOURCE_PREVIEW_PROOF = ACCEPTANCE / "source-preview-live.json"
LIBRARY_HEALTH_PROOF = ACCEPTANCE / "library-health-live.json"

SECRET_PATTERNS = [
    re.compile(r"(?i)\b(authorization|cookie|set-cookie|x-sc4s-manager-token)\b\s*[:=]\s*(?!\[REDACTED\])\S+"),
    re.compile(r"(?i)\b(password|passwd|secret|token|session|hec[_-]?token)\b\s*[:=]\s*(?!\[REDACTED\])\S+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"(?i)(application/o/authorize/\?[^\"'\s<>]*(?:client_id|redirect_uri|scope|state|code)=)"),
]


@dataclass
class Finding:
    path: str
    ok: bool
    detail: str


def load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "missing"
    except json.JSONDecodeError as exc:
        return None, f"invalid json: {exc}"


def text_has_secret_shape(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for pattern in SECRET_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"possible unredacted secret/header near {match.group(1)!r}"
    return None


def is_login_html(data: dict[str, Any]) -> bool:
    body = f"{data.get('body_prefix', '')} {data.get('body', '')}".lower()
    content_type = str(data.get("content_type", "")).lower()
    redirect_url = str(data.get("redirect_url", "")).lower()
    return (
        "<!doctype html" in body
        or "login.s6ops.com" in body
        or "application/o/authorize" in body
        or "text/html" in content_type
        or "application/o/authorize" in redirect_url
    )


def validate_splunk_proof(path: Path = SPLUNK_PROOF) -> list[Finding]:
    data, error = load_json(path)
    if error:
        return [Finding(str(path), False, error)]
    if not isinstance(data, dict):
        return [Finding(str(path), False, "top-level JSON value must be an object")]

    findings: list[Finding] = []
    if secret := text_has_secret_shape(path):
        findings.append(Finding(str(path), False, secret))
    if is_login_html(data):
        findings.append(Finding(str(path), False, "proof appears to be login/SSO HTML or redirect, not Splunk search results"))

    marker = data.get("marker")
    search = data.get("search")
    result_count = data.get("result_count")
    results = data.get("results")

    if not isinstance(marker, str) or not marker.startswith("sc4s-acceptance-"):
        findings.append(Finding(str(path), False, "marker must be the exact sc4s-acceptance marker id"))
    if not isinstance(search, str) or "SC4S_ACCEPTANCE_MARKER" not in search or str(marker) not in search:
        findings.append(Finding(str(path), False, "search must include SC4S_ACCEPTANCE_MARKER and the marker id"))
    if not isinstance(result_count, int) or result_count <= 0:
        findings.append(Finding(str(path), False, "result_count must be an integer greater than zero"))
    if not isinstance(results, list) or not results:
        findings.append(Finding(str(path), False, "results must contain at least one sanitized Splunk event/result"))
    elif marker:
        marker_results = [item for item in results if marker in json.dumps(item, sort_keys=True)]
        if not marker_results:
            findings.append(Finding(str(path), False, "at least one result must contain the marker id"))
        else:
            required_metadata = ("_time", "index", "sourcetype", "source", "host", "_raw")
            if not any(
                isinstance(item, dict)
                and all(isinstance(item.get(field), str) and item.get(field) for field in required_metadata)
                for item in marker_results
            ):
                findings.append(
                    Finding(
                        str(path),
                        False,
                        "at least one marker result must include indexed event metadata: _time, index, sourcetype, source, host, and _raw",
                    )
                )

    status = data.get("status")
    if status is not None and status != 200:
        findings.append(Finding(str(path), False, "status must be 200 when present"))

    return findings or [Finding(str(path), True, "Splunk indexed marker proof is valid")]


def validate_browser_proof(path: Path = BROWSER_PROOF) -> list[Finding]:
    data, error = load_json(path)
    if error:
        return [Finding(str(path), False, error)]
    if not isinstance(data, dict):
        return [Finding(str(path), False, "top-level JSON value must be an object")]

    findings: list[Finding] = []
    if secret := text_has_secret_shape(path):
        findings.append(Finding(str(path), False, secret))

    public_url = data.get("public_url")
    if public_url != "https://sc4s-manager.s6securitylabs.com/":
        findings.append(Finding(str(path), False, "public_url must be https://sc4s-manager.s6securitylabs.com/"))
    if not data.get("captured_at_utc"):
        findings.append(Finding(str(path), False, "captured_at_utc is required"))
    if not data.get("auth_context_redacted"):
        findings.append(Finding(str(path), False, "auth_context_redacted must be true"))
    if not isinstance(data.get("artifact_dir"), str) or not data.get("artifact_dir"):
        findings.append(Finding(str(path), False, "artifact_dir is required"))

    route_inventory = data.get("route_inventory")
    if not isinstance(route_inventory, list) or not route_inventory:
        findings.append(Finding(str(path), False, "route_inventory is required"))
    else:
        required_routes = {"/", "/library", "/catalogue", "/packs", "/exports"}
        seen_routes = {entry.get("route") for entry in route_inventory if isinstance(entry, dict)}
        for route in sorted(required_routes - seen_routes):
            findings.append(Finding(str(path), False, f"route_inventory missing required route {route}"))
        for entry in route_inventory:
            if not isinstance(entry, dict):
                findings.append(Finding(str(path), False, "route_inventory entries must be objects"))
                continue
            route = entry.get("route", "<unknown>")
            if entry.get("status") != 200:
                findings.append(Finding(str(path), False, f"route {route} has unexpected status {entry.get('status')!r}"))
            if not entry.get("artifact_path"):
                findings.append(Finding(str(path), False, f"route {route} missing artifact_path"))
            if route in required_routes:
                if not entry.get("api_path"):
                    findings.append(Finding(str(path), False, f"route {route} missing api_path readback linkage"))
                if not entry.get("api_summary"):
                    findings.append(Finding(str(path), False, f"route {route} is shell-only; api_summary/readback evidence is required"))
            rendered = json.dumps(entry, sort_keys=True)
            if "login.s6ops.com" in rendered or "application/o/authorize" in rendered:
                findings.append(Finding(str(path), False, f"route {route} appears to contain login redirect evidence instead of authenticated app output"))

    checks = data.get("checks")
    if not isinstance(checks, dict):
        findings.append(Finding(str(path), False, "checks object is required"))
        return findings

    required_checks = {
        "authenticated_ui_load": "SC4S Manager",
        "authenticated_api_stats": "health",
        "unauthenticated_api_stats_redirect": "login.s6ops.com",
    }
    for name, expected_text in required_checks.items():
        check = checks.get(name)
        if not isinstance(check, dict):
            findings.append(Finding(str(path), False, f"{name} check is required"))
            continue
        status = check.get("status")
        if name == "unauthenticated_api_stats_redirect":
            ok_status = status in {302, 303, 403}
            haystack = f"{check.get('redirect_url', '')} {check.get('body_prefix', '')}"
        else:
            ok_status = status == 200
            haystack = json.dumps(check, sort_keys=True)
            if not check.get("artifact_path"):
                findings.append(Finding(str(path), False, f"{name} must include artifact_path"))
        if not ok_status:
            findings.append(Finding(str(path), False, f"{name} has unexpected status {status!r}"))
        if expected_text not in haystack:
            findings.append(Finding(str(path), False, f"{name} must include sanitized evidence containing {expected_text!r}"))

    return findings or [Finding(str(path), True, "Authenticated browser route proof is valid")]


def validate_e2e_journey_proof(path: Path = E2E_JOURNEY_PROOF, browser_proof_path: Path = BROWSER_PROOF) -> list[Finding]:
    data, error = load_json(path)
    if error:
        return [Finding(str(path), False, error)]
    if not isinstance(data, dict):
        return [Finding(str(path), False, "top-level JSON value must be an object")]

    findings: list[Finding] = []
    if secret := text_has_secret_shape(path):
        findings.append(Finding(str(path), False, secret))
    if not data.get("captured_at_utc"):
        findings.append(Finding(str(path), False, "captured_at_utc is required"))
    if "protected-route split" not in str(data.get("scope", "")):
        findings.append(Finding(str(path), False, "scope must state protected-route split semantics"))

    browser_data, browser_error = load_json(browser_proof_path)
    if browser_error:
        findings.append(Finding(str(path), False, f"browser proof dependency invalid: {browser_error}"))
        return findings
    if not isinstance(browser_data, dict):
        findings.append(Finding(str(path), False, "browser proof dependency must be a JSON object"))
        return findings

    required_ids = {
        "J01-public-protection",
        "J02-dashboard-operator-landing",
        "J03-source-catalogue-browse-detail",
        "J04-pack-detail-inspection",
        "J05-library-import-validate-apply-separation",
        "J06-export-validation-evidence",
        "J07-negative-auth-and-mutation-safety",
    }
    journeys = data.get("journeys")
    if not isinstance(journeys, list) or not journeys:
        findings.append(Finding(str(path), False, "journeys list is required"))
        return findings

    route_inventory = browser_data.get("route_inventory") if isinstance(browser_data.get("route_inventory"), list) else []
    route_map = {item.get("route"): item for item in route_inventory if isinstance(item, dict)}

    by_id = {item.get("id"): item for item in journeys if isinstance(item, dict)}
    for journey_id in sorted(required_ids - set(by_id)):
        findings.append(Finding(str(path), False, f"missing required journey {journey_id}"))

    for journey_id, journey in by_id.items():
        if not isinstance(journey, dict):
            continue
        if journey.get("status") not in {"covered", "partial", "failed", "missing"}:
            findings.append(Finding(str(path), False, f"{journey_id} status must be covered, partial, failed, or missing, not {journey.get('status')!r}"))
        if not journey.get("persona") or not journey.get("goal"):
            findings.append(Finding(str(path), False, f"{journey_id} missing persona/goal"))
        if not isinstance(journey.get("ui_routes"), list) or not journey.get("ui_routes"):
            findings.append(Finding(str(path), False, f"{journey_id} missing UI routes"))
        if not isinstance(journey.get("api_readback"), list) or not journey.get("api_readback"):
            findings.append(Finding(str(path), False, f"{journey_id} missing API/readback mapping"))
        if not isinstance(journey.get("artifact_paths"), list) or not journey.get("artifact_paths"):
            findings.append(Finding(str(path), False, f"{journey_id} missing artifact paths"))
        if not isinstance(journey.get("test_names"), list) or not journey.get("test_names"):
            findings.append(Finding(str(path), False, f"{journey_id} missing test_names linkage"))

        if journey_id == "J02-dashboard-operator-landing":
            root = route_map.get("/")
            if not isinstance(root, dict) or not root.get("api_summary"):
                findings.append(Finding(str(path), False, "J02 requires dashboard route api_summary evidence"))
        if journey_id == "J03-source-catalogue-browse-detail" and not any(str(route).startswith("/catalogue/") for route in route_map):
            findings.append(Finding(str(path), False, "J03 requires at least one catalogue detail route artifact"))
        if journey_id == "J04-pack-detail-inspection" and not any(str(route).startswith("/packs/") for route in route_map):
            findings.append(Finding(str(path), False, "J04 requires at least one pack detail route artifact"))

    library = by_id.get("J05-library-import-validate-apply-separation", {})
    library_dict = library if isinstance(library, dict) else {}
    library_routes = library_dict.get("ui_routes") if isinstance(library_dict.get("ui_routes"), list) else []
    if "/library" not in library_routes:
        findings.append(Finding(str(path), False, "Library journey must include /library UI route"))
    negative = by_id.get("J07-negative-auth-and-mutation-safety", {})
    negative_text = json.dumps(negative, sort_keys=True)
    if "unauthenticated_api_stats_redirect" not in negative_text or "not invoked" not in negative_text:
        findings.append(Finding(str(path), False, "negative journey must prove unauthenticated redirect/denial and no mutation invocation"))

    return findings or [Finding(str(path), True, "E2E UI user-journey proof is valid")]


def _ok_mapping(value: Any) -> bool:
    return isinstance(value, dict) and value.get("ok") is True


def _validate_required_evidence(path: Path, journey_id: str, evidence: dict[str, Any], required_keys: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    for key in required_keys:
        if key not in evidence:
            findings.append(Finding(str(path), False, f"{journey_id} evidence missing required key {key}"))
    return findings


def validate_crud_journey_proof(path: Path = CRUD_JOURNEY_PROOF) -> list[Finding]:
    data, error = load_json(path)
    if error:
        return [Finding(str(path), False, error)]
    if not isinstance(data, dict):
        return [Finding(str(path), False, "top-level JSON value must be an object")]

    findings: list[Finding] = []
    if secret := text_has_secret_shape(path):
        findings.append(Finding(str(path), False, secret))
    if not data.get("captured_at_utc"):
        findings.append(Finding(str(path), False, "captured_at_utc is required"))
    if "CRUD" not in str(data.get("scope", "")):
        findings.append(Finding(str(path), False, "scope must describe V1 CRUD operator journeys"))
    if data.get("secrets_redacted") is not True:
        findings.append(Finding(str(path), False, "secrets_redacted must be true"))

    required_ids = {
        "J08-syslog-source-crud-lifecycle",
        "J09-hec-destination-crud-lifecycle",
        "J10-syslog-bsd-destination-crud-lifecycle",
        "J11-source-pack-destination-route-lifecycle",
        "J12-pack-import-source-route-apply",
        "J13-failed-apply-rollback",
        "J14-negative-security-validation",
        "J15-ui-crud-journey-coverage",
    }
    journeys = data.get("journeys")
    if not isinstance(journeys, list) or not journeys:
        findings.append(Finding(str(path), False, "journeys list is required"))
        return findings

    by_id = {item.get("id"): item for item in journeys if isinstance(item, dict)}
    for journey_id in sorted(required_ids - set(by_id)):
        findings.append(Finding(str(path), False, f"missing required CRUD journey {journey_id}"))

    required_evidence = {
        "J08-syslog-source-crud-lifecycle": ("baseline_absent", "add", "edit", "delete", "cleanup", "audit_actions"),
        "J09-hec-destination-crud-lifecycle": ("baseline_absent", "add", "inventory", "edit", "delete", "cleanup", "audit_actions"),
        "J10-syslog-bsd-destination-crud-lifecycle": ("baseline_absent", "add", "edit", "selector", "delete", "cleanup"),
        "J11-source-pack-destination-route-lifecycle": ("baseline_absent", "route", "validation", "control", "splunk_readback", "delete", "post_delete"),
        "J12-pack-import-source-route-apply": ("import", "preview", "apply", "splunk_readback", "rollback"),
        "J13-failed-apply-rollback": ("baseline", "validation_failed", "rollback", "post_restore_health"),
        "J14-negative-security-validation": ("unauthenticated_mutation_denied", "invalid_inputs_rejected", "secret_leak_found", "path_traversal_rejected"),
        "J15-ui-crud-journey-coverage": ("ui_routes", "api_calls", "screenshots"),
    }

    for journey_id, journey in by_id.items():
        if journey_id not in required_ids or not isinstance(journey, dict):
            continue
        if journey.get("status") != "covered":
            findings.append(Finding(str(path), False, f"{journey_id} must be covered, not {journey.get('status')!r}"))
        if not journey.get("persona") or not journey.get("goal"):
            findings.append(Finding(str(path), False, f"{journey_id} missing persona/goal"))
        steps = journey.get("steps")
        if not isinstance(steps, list) or len(steps) < 3:
            findings.append(Finding(str(path), False, f"{journey_id} must list concrete operator steps"))
        evidence = journey.get("evidence")
        if not isinstance(evidence, dict):
            findings.append(Finding(str(path), False, f"{journey_id} evidence object is required"))
            continue
        findings.extend(_validate_required_evidence(path, journey_id, evidence, required_evidence[journey_id]))

    j09 = by_id.get("J09-hec-destination-crud-lifecycle")
    if isinstance(j09, dict) and isinstance(j09.get("evidence"), dict):
        ev = j09["evidence"]
        inventory = ev.get("inventory") if isinstance(ev.get("inventory"), dict) else {}
        if inventory.get("token") != "[REDACTED]":
            findings.append(Finding(str(path), False, "J09 inventory must redact the HEC token"))
        cleanup = ev.get("cleanup") if isinstance(ev.get("cleanup"), dict) else {}
        if cleanup.get("secret_leak_found") is not False:
            findings.append(Finding(str(path), False, "J09 cleanup must prove no destination secret leak"))

    j11 = by_id.get("J11-source-pack-destination-route-lifecycle")
    if isinstance(j11, dict) and isinstance(j11.get("evidence"), dict):
        ev = j11["evidence"]
        readback = ev.get("splunk_readback") if isinstance(ev.get("splunk_readback"), dict) else {}
        if readback.get("ok") is not True or not isinstance(readback.get("result_count"), int) or readback.get("result_count", 0) <= 0:
            findings.append(Finding(str(path), False, "J11 splunk_readback must prove at least one indexed routed marker result"))
        for key in ("index", "sourcetype", "destination_id"):
            if not readback.get(key):
                findings.append(Finding(str(path), False, f"J11 splunk_readback missing {key}"))
        post_delete = ev.get("post_delete") if isinstance(ev.get("post_delete"), dict) else {}
        if post_delete.get("route_applied") is not False:
            findings.append(Finding(str(path), False, "J11 post_delete must prove the route no longer applies"))

    j14 = by_id.get("J14-negative-security-validation")
    if isinstance(j14, dict) and isinstance(j14.get("evidence"), dict):
        ev = j14["evidence"]
        for key in ("unauthenticated_mutation_denied", "invalid_inputs_rejected", "path_traversal_rejected"):
            if ev.get(key) is not True:
                findings.append(Finding(str(path), False, f"J14 must prove {key}"))
        if ev.get("secret_leak_found") is not False:
            findings.append(Finding(str(path), False, "J14 must prove no secret leak"))

    j15 = by_id.get("J15-ui-crud-journey-coverage")
    if isinstance(j15, dict) and isinstance(j15.get("evidence"), dict):
        ev = j15["evidence"]
        routes = set(ev.get("ui_routes") or []) if isinstance(ev.get("ui_routes"), list) else set()
        for route in ("/sources", "/destinations", "/routes"):
            if route not in routes:
                findings.append(Finding(str(path), False, f"J15 missing UI route {route}"))
        api_calls = " ".join(str(call) for call in ev.get("api_calls", [])) if isinstance(ev.get("api_calls"), list) else ""
        for fragment in ("/api/sources", "/api/destinations", "/api/routes"):
            if fragment not in api_calls:
                findings.append(Finding(str(path), False, f"J15 missing API call coverage for {fragment}"))

    return findings or [Finding(str(path), True, "CRUD operator journey proof is valid")]


def find_package_drill_evidence(acceptance_dir: Path = ACCEPTANCE) -> Path | None:
    """Return the most recent package-install-<timestamp>.json, or None if absent."""
    candidates = sorted(
        p for p in acceptance_dir.glob(PACKAGE_DRILL_GLOB)
        if p != PACKAGE_DRILL_TEMPLATE and "template" not in p.name
    )
    return candidates[-1] if candidates else None


def validate_package_drill_proof(path: Path | None = None) -> list[Finding]:
    """Validate a package install/upgrade/rollback drill evidence JSON."""
    if path is None:
        path = find_package_drill_evidence()

    if path is None:
        return [Finding(
            str(ACCEPTANCE / "package-install-<timestamp>.json"),
            False,
            "missing package drill evidence — run validate_package_install.py --evidence-out "
            "docs/acceptance/package-install-<timestamp>.json on a disposable VM/LXC first",
        )]

    data, error = load_json(path)
    if error:
        return [Finding(str(path), False, error)]
    if not isinstance(data, dict):
        return [Finding(str(path), False, "top-level JSON value must be an object")]

    findings: list[Finding] = []
    if secret := text_has_secret_shape(path):
        findings.append(Finding(str(path), False, secret))

    for field in ("ok", "version", "artifact_sha256", "install", "upgrade", "rollback", "service_state", "redaction", "commands"):
        if field not in data:
            findings.append(Finding(str(path), False, f"missing required field: {field}"))

    install = data.get("install")
    if isinstance(install, dict):
        for field in ("started_at", "finished_at", "ok"):
            if field not in install:
                findings.append(Finding(str(path), False, f"install.{field} is required"))
    elif install is not None:
        findings.append(Finding(str(path), False, "install must be a dict"))

    service_state = data.get("service_state")
    if isinstance(service_state, dict):
        for field in ("manager", "control_daemon"):
            if field not in service_state:
                findings.append(Finding(str(path), False, f"service_state.{field} is required"))
    elif service_state is not None:
        findings.append(Finding(str(path), False, "service_state must be a dict"))

    redaction = data.get("redaction")
    if isinstance(redaction, dict):
        if "findings" not in redaction:
            findings.append(Finding(str(path), False, "redaction.findings list is required"))
    elif redaction is not None:
        findings.append(Finding(str(path), False, "redaction must be a dict"))

    if not isinstance(data.get("commands"), list):
        findings.append(Finding(str(path), False, "commands must be a list"))

    return findings or [Finding(str(path), True, "Package install/upgrade/rollback drill evidence is valid")]


def validate_next_release_evidence(path: Path, workflow: str, required_fields: tuple[str, ...]) -> list[Finding]:
    """Validate one next-release live/dry-run evidence JSON without fabricating proof."""
    data, error = load_json(path)
    if error:
        return [Finding(str(path), False, f"missing {workflow} evidence — capture {path.relative_to(ACCEPTANCE)} from the lab workflow first")]
    if not isinstance(data, dict):
        return [Finding(str(path), False, "top-level JSON value must be an object")]

    findings: list[Finding] = []
    if secret := text_has_secret_shape(path):
        findings.append(Finding(str(path), False, secret))
    for field in required_fields:
        if field not in data:
            findings.append(Finding(str(path), False, f"missing required field: {field}"))
    if data.get("ok") is not True:
        findings.append(Finding(str(path), False, f"{workflow} evidence ok must be true"))
    return findings or [Finding(str(path), True, f"{workflow} evidence is valid")]


def validate_ci_functional_proof(path: Path = CI_FUNCTIONAL_PROOF) -> list[Finding]:
    data, error = load_json(path)
    if error:
        return [Finding(str(path), False, error)]
    if not isinstance(data, dict):
        return [Finding(str(path), False, "top-level JSON value must be an object")]
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from sc4s_manager.ci_functional import validate_ci_evidence
    except Exception as exc:
        return [Finding(str(path), False, f"could not import CI evidence validator: {exc}")]
    findings = []
    if secret := text_has_secret_shape(path):
        findings.append(Finding(str(path), False, secret))
    for item in validate_ci_evidence(data, release_mode=True):
        findings.append(Finding(str(path), bool(item.get("ok")), str(item.get("detail", ""))))
    return findings or [Finding(str(path), True, "CI functional evidence is valid")]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate sanitized v1 release evidence artifacts.")
    parser.add_argument("--require-final", action="store_true", help="Fail when either final proof artifact is missing.")
    parser.add_argument("--require-e2e-ui", action="store_true", help="Require E2E UI user-journey matrix evidence.")
    parser.add_argument("--require-ci-functional", action="store_true", help="Require disposable CI functional browser/pack/SPL evidence.")
    parser.add_argument("--require-crud-journeys", action="store_true", help="Require V1 source/destination/route CRUD operator-journey evidence.")
    parser.add_argument("--require-package-drill", action="store_true", help="Require package install/upgrade/rollback drill evidence.")
    parser.add_argument("--require-runtime-dashboard", action="store_true", help="Require runtime dashboard live-state and counter-delta evidence.")
    parser.add_argument("--require-source-preview", action="store_true", help="Require source onboarding preview good-path and fallback-path evidence.")
    parser.add_argument("--require-library-health", action="store_true", help="Require SecHub Library source-health success and controlled-failure evidence.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    findings: list[Finding] = []

    validators = [(SPLUNK_PROOF, validate_splunk_proof), (BROWSER_PROOF, validate_browser_proof)]
    if args.require_e2e_ui:
        validators.append((E2E_JOURNEY_PROOF, validate_e2e_journey_proof))
    if args.require_ci_functional:
        validators.append((CI_FUNCTIONAL_PROOF, validate_ci_functional_proof))
    if args.require_crud_journeys:
        validators.append((CRUD_JOURNEY_PROOF, validate_crud_journey_proof))

    for path, validator in validators:
        required = args.require_final
        if path == E2E_JOURNEY_PROOF:
            required = args.require_e2e_ui or args.require_final
        if path == CI_FUNCTIONAL_PROOF:
            required = args.require_ci_functional
        if path == CRUD_JOURNEY_PROOF:
            required = args.require_crud_journeys
        if path.exists() or required:
            findings.extend(validator(path))

    if args.require_package_drill:
        findings.extend(validate_package_drill_proof())
    elif find_package_drill_evidence() is not None:
        findings.extend(validate_package_drill_proof())

    if args.require_runtime_dashboard:
        findings.extend(validate_next_release_evidence(
            RUNTIME_DASHBOARD_PROOF,
            "runtime dashboard",
            ("ok", "captured_at", "runtime_state", "dashboard_artifact", "counter_delta", "redaction"),
        ))
    if args.require_source_preview:
        findings.extend(validate_next_release_evidence(
            SOURCE_PREVIEW_PROOF,
            "source preview",
            ("ok", "captured_at", "good_path", "fallback_path", "redaction"),
        ))
    if args.require_library_health:
        findings.extend(validate_next_release_evidence(
            LIBRARY_HEALTH_PROOF,
            "library health",
            ("ok", "captured_at", "source_health", "curated_import_apply", "broken_source", "trust_semantics", "redaction"),
        ))

    ok = all(finding.ok for finding in findings)
    print(json.dumps({"ok": ok, "findings": [finding.__dict__ for finding in findings]}, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
