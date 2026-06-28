from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .packs import load_packs, summarize_field_contract, summarize_preset_previews, validate_pack_fixtures
except ImportError:  # Loaded via importlib.spec_from_file_location in app.py
    from sc4s_manager.packs import load_packs, summarize_field_contract, summarize_preset_previews, validate_pack_fixtures

UPSTREAM_OUTPUT_SUBDIR = Path("catalogue/generated/upstream")
COMMUNITY_OUTPUT_SUBDIR = Path("catalogue/generated/community")
VALIDATION_OUTPUT_SUBDIR = Path("catalogue/generated/validation")
REQUIRED_VERIFICATION_STAGES = ("syslog_ng_syntax", "runtime_pack_validation", "splunk_readback")
DRIFT_REPORT_PATH = UPSTREAM_OUTPUT_SUBDIR / "drift-report.json"
UPSTREAM_ORIGINS = {"sc4s-inbuilt", "sc4s-inbuilt-lite"}
NEXT_ORIGIN = "sechub-resource"
COMMUNITY_ORIGIN = "community-extra"
COMMUNITY_DEFAULT_SOURCE_STATUS = "candidate"
COMMUNITY_DEFAULT_TRUST_LEVEL = "community_submitted"
COMMUNITY_DEFAULT_QUALITY_STATUS = "catalogued"
COMMUNITY_DEFAULT_VALIDATION_STATE = "unvalidated_source_corpus"
DEFAULT_CANDIDATE_WARNINGS = [
    "Community candidate only: not curated or validated for production.",
    "Provenance must be reviewed and representative Splunk evidence captured before promotion.",
]
PARSER_TYPES = {"syslog_app_parser", "netsource_app_parser"}
FILTER_TYPES = {"filter"}
POSTFILTER_TYPES = {"postfilter"}
DESTINATION_TYPES = {"destination"}
DOC_TYPES = {"source_documentation"}
LITE_TYPES = {"lite_addon"}


def _load_upstream_catalogues(manager_root: Path) -> list[dict[str, Any]]:
    output_dir = manager_root / UPSTREAM_OUTPUT_SUBDIR
    payloads: list[dict[str, Any]] = []
    for origin in sorted(UPSTREAM_ORIGINS):
        path = output_dir / f"{origin}.json"
        if path.exists():
            payloads.append(json.loads(path.read_text()))
    return payloads


def _load_community_catalogues(manager_root: Path) -> list[dict[str, Any]]:
    output_dir = manager_root / COMMUNITY_OUTPUT_SUBDIR
    if not output_dir.exists():
        return []
    payloads: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*.json")):
        payloads.append(json.loads(path.read_text()))
    return payloads


def _load_drift_report(manager_root: Path) -> dict[str, Any] | None:
    path = manager_root / DRIFT_REPORT_PATH
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _contains_any(values: list[str], needles: tuple[str, ...]) -> bool:
    joined = "\n".join(values).lower()
    return any(needle in joined for needle in needles)


def _normalize_upstream_artifact(row: dict[str, Any]) -> dict[str, Any]:
    artifact_type = row.get("artifact_type") or "unknown"
    return {
        "origin": row.get("origin"),
        "type": artifact_type,
        "path": row.get("artifact_path"),
        "kind": artifact_type,
        "contains_secrets": False,
        "sha256": row.get("sha256"),
    }


def _normalize_export_artifact(artifact: dict[str, Any], origin: str) -> dict[str, Any]:
    return {
        "origin": origin,
        "type": artifact.get("group"),
        "path": artifact.get("source_path"),
        "kind": artifact.get("kind"),
        "contains_secrets": bool(artifact.get("contains_secrets")),
        "required": bool(artifact.get("required", False)),
        "target_path": artifact.get("target_path"),
        "artifact_id": artifact.get("id"),
    }


def _normalize_community_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact_type = artifact.get("type") or "community_reference"
    return {
        "origin": COMMUNITY_ORIGIN,
        "type": artifact_type,
        "path": artifact.get("path"),
        "kind": artifact.get("kind") or artifact_type,
        "contains_secrets": False,
        "url": artifact.get("url"),
    }


def _artifact_inventory_by_type(artifacts: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for artifact in artifacts:
        artifact_type = str(artifact.get("type") or "unknown")
        path = str(artifact.get("path") or "")
        if not path:
            continue
        grouped.setdefault(artifact_type, []).append(path)
    return {key: sorted(dict.fromkeys(values)) for key, values in sorted(grouped.items())}


def _generated_validation_evidence_path(pack: dict[str, Any] | None, manager_root: Path | None) -> Path | None:
    if not pack or manager_root is None:
        return None
    pack_id = str(pack.get("id") or "").strip()
    if not pack_id:
        return None
    validation_root = (manager_root / VALIDATION_OUTPUT_SUBDIR).resolve()
    evidence_path = (validation_root / pack_id / "validation-evidence.json").resolve()
    try:
        evidence_path.relative_to(validation_root)
    except ValueError:
        return None
    return evidence_path


def _stage_passed(checks_by_stage: dict[str, dict[str, Any]], stage: str) -> bool:
    check = checks_by_stage.get(stage)
    if not isinstance(check, dict) or check.get("ok") is not True:
        return False
    details = check.get("details", {})
    if not isinstance(details, dict):
        return False
    return str(details.get("status") or "").strip().lower() == "passed"


def _validation_evidence_status(pack: dict[str, Any] | None, manager_root: Path | None = None) -> dict[str, bool]:
    status = {
        "ok": False,
        "syntax_validated": False,
        "runtime_pack_validation": False,
        "splunk_ingestion_validated": False,
        "full_verification": False,
    }
    evidence_path = _generated_validation_evidence_path(pack, manager_root)
    if evidence_path is None or not evidence_path.exists() or not evidence_path.is_file():
        return status
    try:
        evidence = json.loads(evidence_path.read_text())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return status
    if not isinstance(evidence, dict):
        return status
    pack_id = str((pack or {}).get("id") or "").strip()
    if str(evidence.get("pack_id") or "").strip() != pack_id:
        return status
    checks = evidence.get("checks")
    if not isinstance(checks, list):
        return status
    checks_by_stage = {
        str(check.get("stage") or "").strip(): check
        for check in checks
        if isinstance(check, dict) and str(check.get("stage") or "").strip()
    }
    evidence_ok = evidence.get("ok") is True
    status["ok"] = evidence_ok
    if not evidence_ok:
        return status
    status["syntax_validated"] = _stage_passed(checks_by_stage, "syslog_ng_syntax")
    status["runtime_pack_validation"] = _stage_passed(checks_by_stage, "runtime_pack_validation")
    status["splunk_ingestion_validated"] = _stage_passed(checks_by_stage, "splunk_readback")
    status["full_verification"] = all(
        _stage_passed(checks_by_stage, stage) for stage in REQUIRED_VERIFICATION_STAGES
    )
    return status


def _has_structured_validation_evidence(
    pack: dict[str, Any] | None,
    manager_root: Path | None = None,
) -> bool:
    return _validation_evidence_status(pack, manager_root)["full_verification"]


def _compute_capabilities(
    artifacts: list[dict[str, Any]],
    pack: dict[str, Any] | None,
    manager_root: Path | None = None,
) -> dict[str, bool]:
    artifact_types = {str(artifact.get("kind") or artifact.get("type") or "") for artifact in artifacts}
    artifact_paths = [str(artifact.get("path") or "") for artifact in artifacts]
    field_contract = pack.get("field_contract", {}) if pack else {}
    reduction_rules = pack.get("reduction_rules", []) if pack else []
    presets = pack.get("logging_presets", []) if pack else []
    validation_status = _validation_evidence_status(pack, manager_root)
    return {
        "parser": bool(artifact_types & PARSER_TYPES) or _contains_any(artifact_paths, ("app_parsers/", "app-")),
        "filters": bool(artifact_types & FILTER_TYPES) or _contains_any(artifact_paths, ("/filters/", "f-")),
        "postfilters": bool(artifact_types & POSTFILTER_TYPES) or _contains_any(artifact_paths, ("/postfilters/", "postfilter")),
        "log_reduction": bool(reduction_rules) or any(preset.get("reduction_rules") for preset in presets),
        "splunk_props_transforms": _contains_any(artifact_paths, ("props.conf", "transforms.conf")),
        "cim_mapping": field_contract.get("cim", {}).get("mapping_status") in {"partial", "complete"},
        "ocsf_mapping": field_contract.get("ocsf", {}).get("mapping_status") in {"partial", "complete"},
        "fixtures": _contains_any(artifact_paths, ("test-events/",)),
        "syntax_validated": validation_status["syntax_validated"],
        "splunk_ingestion_validated": validation_status["splunk_ingestion_validated"],
    }


def _upstream_summary(source_id: str, vendor: str, product: str, origins: list[str]) -> str:
    label = " ".join(part for part in [vendor, product] if part).strip() or source_id.replace("_", " ")
    origin_text = ", ".join(origins)
    return f"Upstream SC4S catalogue coverage for {label}, sourced from {origin_text}."


QUALITY_STATUS_SCORES = {
    "deprecated": 1,
    "draft": 1,
    "catalogued": 2,
    "curated": 3,
    "validated": 4,
    "field_validated": 5,
}


def _derive_vendor_product(source_id: str, vendor: str | None, product: str | None) -> tuple[str, str]:
    normalized_source = _normalize_id(source_id) or source_id
    clean_vendor = str(vendor or "").strip()
    clean_product = str(product or "").strip()
    if not clean_vendor:
        clean_vendor = normalized_source.split("_", 1)[0]
    if not clean_product:
        vendor_prefix = _normalize_id(clean_vendor) or clean_vendor.lower()
        if normalized_source == vendor_prefix:
            clean_product = clean_vendor
        elif normalized_source.startswith(f"{vendor_prefix}_"):
            clean_product = normalized_source[len(vendor_prefix) + 1 :]
        else:
            clean_product = normalized_source
    return clean_vendor, clean_product


def _quality_score(
    entry_or_pack: dict[str, Any] | None,
    capabilities: dict[str, bool] | None = None,
    manager_root: Path | None = None,
) -> int:
    if not entry_or_pack:
        return 2
    status = str(entry_or_pack.get("quality_status") or "catalogued").strip().lower()
    score = QUALITY_STATUS_SCORES.get(status, 2)
    has_structured_evidence = _has_structured_validation_evidence(entry_or_pack, manager_root)
    if has_structured_evidence:
        score = max(score, 4)
    else:
        score = min(score, 3)
    return max(1, min(5, int(score)))


def _review_status(entry_or_pack: dict[str, Any] | None) -> str:
    """Public advisory review status; never a local deployment approval."""
    if not entry_or_pack:
        return "unreviewed"
    if str(entry_or_pack.get("quality_status") or "").strip().lower() == "deprecated":
        return "deprecated"
    source_status = str(entry_or_pack.get("source_status") or "").strip().lower()
    if source_status in {"candidate", "generated"}:
        return "unreviewed"
    quality_status = str(entry_or_pack.get("quality_status") or "").strip().lower()
    trust_level = str(entry_or_pack.get("trust_level") or "").strip().lower()
    if quality_status in {"curated", "validated", "field_validated"} and trust_level != COMMUNITY_DEFAULT_TRUST_LEVEL:
        return "reviewed"
    return "unreviewed"


def _is_verified(
    entry_or_pack: dict[str, Any] | None,
    capabilities: dict[str, bool] | None = None,
    manager_root: Path | None = None,
) -> bool:
    return _quality_score(entry_or_pack, capabilities, manager_root) >= 4


def _display_name(source_id: str, vendor: str | None, product: str | None, pack: dict[str, Any] | None) -> str:
    if pack and pack.get("display_name"):
        return str(pack["display_name"])
    label = " ".join(part for part in [vendor, product] if part).strip()
    return label or source_id.replace("_", " ").replace("-", " ").title()


def _normalize_id(value: str | None) -> str | None:
    if not value:
        return None
    return str(value).strip().lower().replace("-", "_")


def _pack_source_keys(pack: dict[str, Any]) -> set[str]:
    keys = {_normalize_id(str(pack.get("id") or ""))}
    vendor = _normalize_id(str(pack.get("vendor") or ""))
    product = _normalize_id(str(pack.get("product") or ""))
    if vendor and product:
        keys.add(f"{vendor}_{product}")
    listener_source_id = _normalize_id(pack.get("listener", {}).get("source_id"))
    if listener_source_id:
        keys.add(listener_source_id)
    return {key for key in keys if key}


def _validation_state(
    pack: dict[str, Any] | None,
    capabilities: dict[str, bool] | None = None,
    manager_root: Path | None = None,
) -> str:
    if not pack:
        return "catalogued_only"
    if _is_verified(pack, capabilities, manager_root):
        return "validated_pack"
    if str(pack.get("quality_status") or "").strip().lower() == "curated":
        return "curated_pack"
    return "catalogued_pack"


def _validation_evidence_bundle(pack: dict[str, Any] | None, manager_root: Path | None) -> dict[str, Any] | None:
    if not pack:
        return None
    pack_dir = Path(str(pack.get("pack_dir") or "")) if pack.get("pack_dir") else None
    paths: list[str] = []
    if pack_dir is not None:
        local_doc = pack_dir / "docs" / "validation-evidence.md"
        if local_doc.exists():
            paths.append(str(local_doc))
    if manager_root is not None:
        generated_dir = manager_root / VALIDATION_OUTPUT_SUBDIR / str(pack.get("id"))
        for candidate in [generated_dir / "validation-evidence.json", generated_dir / "validation-evidence.md"]:
            if candidate.exists():
                paths.append(str(candidate))
    deduped = sorted(dict.fromkeys(paths))
    if not deduped:
        return None
    return {
        "pack_id": pack.get("id"),
        "paths": deduped,
        "generated": [path for path in deduped if "/catalogue/generated/validation/" in path],
        "docs": [path for path in deduped if path.endswith("validation-evidence.md") and "/catalogue/generated/validation/" not in path],
    }


def _base_validation(pack: dict[str, Any] | None, capabilities: dict[str, bool] | None = None, manager_root: Path | None = None) -> dict[str, Any]:
    if not pack:
        return {
            "last_verified_at": None,
            "trust_level": "unverified",
            "evidence_paths": [],
            "state": "catalogued_only",
            "evidence_bundle": None,
        }
    validation = pack.get("validation", {})
    evidence_text = str(validation.get("evidence") or "")
    evidence_paths: list[str] = []
    if evidence_text and "/" in evidence_text:
        evidence_paths.append(evidence_text)
    bundle = _validation_evidence_bundle(pack, manager_root)
    if bundle:
        evidence_paths.extend(bundle["paths"])
    return {
        "last_verified_at": validation.get("date_validated"),
        "trust_level": pack.get("trust_level", "unverified"),
        "evidence_paths": sorted(dict.fromkeys(evidence_paths)),
        "validated_by": validation.get("validated_by"),
        "summary": validation.get("evidence"),
        "state": _validation_state(pack, capabilities, manager_root),
        "evidence_bundle": bundle,
    }


def _pack_provenance(pack: dict[str, Any] | None) -> dict[str, Any] | None:
    if not pack:
        return None
    provenance = pack.get("provenance", {})
    source = provenance.get("source", {})
    reference = source.get("reference")
    return {
        "origin": provenance.get("origin"),
        "pack_class": provenance.get("pack_class"),
        "source_type": source.get("type"),
        "reference": reference,
        "redistribution": source.get("redistribution"),
        "url": reference if isinstance(reference, str) and reference.startswith(("http://", "https://")) else pack.get("url"),
        "source_kind": None,
        "source_status": None,
    }


def _community_provenance(entry: dict[str, Any]) -> dict[str, Any]:
    source_kind = str(entry.get("source_kind") or "issue")
    reference = entry.get("provenance_url") or entry.get("reference") or entry.get("id")
    return {
        "origin": COMMUNITY_ORIGIN,
        "pack_class": COMMUNITY_ORIGIN,
        "source_type": entry.get("source_type") or f"github_{source_kind}",
        "reference": reference,
        "redistribution": entry.get("redistribution") or "unknown",
        "url": entry.get("provenance_url"),
        "source_kind": source_kind,
        "source_status": COMMUNITY_DEFAULT_SOURCE_STATUS,
    }


def _community_candidate_warnings(entry: dict[str, Any]) -> list[str]:
    warnings = [str(item) for item in entry.get("candidate_warnings", []) if str(item).strip()]
    for warning in DEFAULT_CANDIDATE_WARNINGS:
        if warning not in warnings:
            warnings.append(warning)
    return warnings


def _community_validation(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "last_verified_at": None,
        "trust_level": COMMUNITY_DEFAULT_TRUST_LEVEL,
        "evidence_paths": [],
        "validated_by": None,
        "summary": None,
        "state": COMMUNITY_DEFAULT_VALIDATION_STATE,
        "evidence_bundle": None,
    }


def _comparison_to_upstream(pack: dict[str, Any] | None, capabilities: dict[str, bool]) -> dict[str, Any]:
    relationship = pack.get("relationship_to_upstream", "upstream_only") if pack else "upstream_only"
    validation = pack.get("validation", {}) if pack else {}
    return {
        "relationship": relationship,
        "event_family_delta": sorted((pack.get("sourcetypes") or {}).keys()) if pack else [],
        "field_extraction_delta": sorted((pack.get("normalized_fields") or {}).keys()) if pack else [],
        "splunk_knowledge_added": capabilities["splunk_props_transforms"],
        "reduction_added": capabilities["log_reduction"],
        "fixture_validation_summary": validation.get("evidence") if pack else None,
    }


def _upstream_section(payloads: list[dict[str, Any]], artifacts: list[dict[str, Any]], source_id: str) -> dict[str, Any]:
    repo = None
    requested_ref = None
    resolved_commit = None
    generated_at = None
    sc4s_version = None
    for payload in payloads:
        meta = payload.get("upstream", {})
        repo = repo or meta.get("repo_url")
        requested_ref = requested_ref or meta.get("requested_ref")
        resolved_commit = resolved_commit or meta.get("resolved_commit")
        generated_at = generated_at or meta.get("generated_at")
        sc4s_version = sc4s_version or meta.get("requested_ref")
    return {
        "source_id": source_id,
        "repo": repo,
        "ref": requested_ref,
        "commit": resolved_commit,
        "generated_at": generated_at,
        "sc4s_version": sc4s_version,
        "paths": sorted(dict.fromkeys(str(artifact.get("path")) for artifact in artifacts if artifact.get("origin") in UPSTREAM_ORIGINS)),
    }


def _entry_drift(source_id: str, drift_report: dict[str, Any] | None) -> dict[str, Any] | None:
    if not drift_report:
        return None

    def matches(item: dict[str, Any]) -> bool:
        before = item.get("before", {}) if isinstance(item.get("before"), dict) else {}
        after = item.get("after", {}) if isinstance(item.get("after"), dict) else {}
        return source_id in {
            _normalize_id(item.get("source_id")),
            _normalize_id(before.get("source_id")),
            _normalize_id(after.get("source_id")),
        }

    added = [item for item in drift_report.get("added", []) if matches(item)]
    removed = [item for item in drift_report.get("removed", []) if matches(item)]
    changed = [item for item in drift_report.get("changed", []) if matches(item)]
    if not (added or removed or changed):
        return None
    metadata = drift_report.get("metadata", {}) if isinstance(drift_report.get("metadata"), dict) else {}
    return {
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
        "previous_ref": metadata.get("previous_ref"),
        "current_ref": metadata.get("current_ref"),
        "previous_commit": metadata.get("previous_commit"),
        "current_commit": metadata.get("current_commit"),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def _sc4s_manager_section(pack: dict[str, Any] | None) -> dict[str, Any] | None:
    if not pack:
        return None
    export_artifacts = pack.get("export_artifacts", [])
    return {
        "pack_version": pack.get("version"),
        "schema_version": pack.get("schema_version"),
        "paths": [artifact.get("source_path") for artifact in export_artifacts],
        "pack_url": pack.get("url"),
    }


def _community_comparison(entry: dict[str, Any], capabilities: dict[str, bool]) -> dict[str, Any]:
    return {
        "relationship": entry.get("relationship_to_upstream", "new_pack"),
        "event_family_delta": [],
        "field_extraction_delta": [],
        "splunk_knowledge_added": capabilities["splunk_props_transforms"],
        "reduction_added": capabilities["log_reduction"],
        "fixture_validation_summary": None,
    }


def build_catalogue_entries(packs_root: str | Path, manager_root: str | Path | None = None) -> list[dict[str, Any]]:
    packs_root = Path(packs_root)
    manager_root = Path(manager_root) if manager_root else packs_root.parent
    packs = load_packs(packs_root)
    upstream_payloads = _load_upstream_catalogues(manager_root)
    community_payloads = _load_community_catalogues(manager_root)
    drift_report = _load_drift_report(manager_root)

    pack_index: dict[str, dict[str, Any]] = {}
    fixture_index: dict[str, list[dict[str, Any]]] = {}
    for pack in packs:
        fixture_index[str(pack.get("id"))] = validate_pack_fixtures(pack, pack["pack_dir"])
        for key in _pack_source_keys(pack):
            pack_index[key] = pack

    upstream_groups: dict[str, dict[str, Any]] = {}
    for payload in upstream_payloads:
        for row in payload.get("artifacts", []):
            source_id = _normalize_id(row.get("source_id"))
            if not source_id:
                continue
            group = upstream_groups.setdefault(
                source_id,
                {
                    "source_id": source_id,
                    "vendor": _derive_vendor_product(source_id, row.get("vendor"), row.get("product"))[0],
                    "product": _derive_vendor_product(source_id, row.get("vendor"), row.get("product"))[1],
                    "origins": set(),
                    "artifacts": [],
                    "payloads": [],
                },
            )
            group["origins"].add(row.get("origin"))
            group["artifacts"].append(_normalize_upstream_artifact(row))
            group["payloads"].append(payload)

    seen_ids: set[str] = set()
    merged_entries: list[dict[str, Any]] = []
    all_ids = sorted(set(upstream_groups) | set(pack_index))
    for source_id in all_ids:
        pack = pack_index.get(source_id)
        upstream_group = upstream_groups.get(source_id)
        upstream_artifacts = list(upstream_group.get("artifacts", [])) if upstream_group else []
        pack_origin = pack.get("provenance", {}).get("origin", NEXT_ORIGIN) if pack else None
        next_artifacts = [_normalize_export_artifact(artifact, pack_origin or NEXT_ORIGIN) for artifact in pack.get("export_artifacts", [])] if pack else []
        artifacts = upstream_artifacts + next_artifacts
        origins = sorted(
            dict.fromkeys(
                (list(upstream_group.get("origins", [])) if upstream_group else [])
                + ([pack_origin] if pack_origin else [])
            )
        )
        vendor, product = _derive_vendor_product(
            source_id,
            pack.get("vendor") if pack else upstream_group.get("vendor"),
            pack.get("product") if pack else upstream_group.get("product"),
        )
        capabilities = _compute_capabilities(artifacts, pack, manager_root)
        quality_score = _quality_score(pack, capabilities, manager_root)
        is_verified = _is_verified(pack, capabilities, manager_root)
        relationship = pack.get("relationship_to_upstream") if pack else "upstream_only"
        entry_id = str(pack.get("id") if pack else source_id)
        fixture_results = fixture_index.get(entry_id, []) if pack else []
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        merged_entries.append(
            {
                "id": entry_id,
                "display_name": _display_name(entry_id, vendor, product, pack),
                "vendor": vendor,
                "product": product,
                "origins": origins,
                "effective_origin": pack_origin if pack_origin else (origins[-1] if origins else "sc4s-inbuilt"),
                "relationship_to_upstream": relationship,
                "review_status": _review_status(pack),
                "trust_level": pack.get("trust_level", "unverified") if pack else "unverified",
                "quality_status": pack.get("quality_status", "catalogued") if pack else "catalogued",
                "quality_score": quality_score,
                "is_verified": is_verified,
                "capabilities": capabilities,
                "summary": str(pack.get("description")) if pack else _upstream_summary(source_id, vendor, product, origins),
                "upstream": _upstream_section(upstream_group.get("payloads", []) if upstream_group else [], upstream_artifacts, source_id),
                "upstream_drift": _entry_drift(source_id, drift_report),
                "sc4s_manager": _sc4s_manager_section(pack),
                "artifacts": artifacts,
                "artifact_inventory": _artifact_inventory_by_type(artifacts),
                "presets": list(pack.get("logging_presets", [])) if pack else [],
                "preset_previews": summarize_preset_previews(pack, fixture_results) if pack else [],
                "fixture_results": fixture_results,
                "fixture_summary": {
                    "set_count": len(fixture_results),
                    "event_count": sum(int(result.get("event_count") or 0) for result in fixture_results),
                    "families": sorted({family for result in fixture_results for family in (result.get("families") or {}).keys()}),
                },
                "field_contract": pack.get("field_contract") if pack else {"mapping_status": "unknown", "cim": {}, "ocsf": {}, "ecs": {}},
                "field_contract_summary": summarize_field_contract(pack) if pack else {"common": {"required_fields": [], "optional_fields": [], "present_fields": [], "missing_required_fields": [], "status": "unknown"}, "cim": {"declared_status": "unknown", "mapped_fields": [], "incomplete_fields": [], "coverage_gap_count": 0, "honesty_warnings": []}},
                "comparison_to_upstream": _comparison_to_upstream(pack, capabilities),
                "validation": _base_validation(pack, capabilities, manager_root),
                "known_limitations": [] if not pack else [note for note in [pack.get("source_log_version", {}).get("notes")] if note],
                "feedback": {"likes": 0, "rating_average": None, "comments_url": None},
                "provenance": _pack_provenance(pack),
                "source_status": None,
                "candidate_warnings": [],
            }
        )

    for payload in community_payloads:
        for raw_entry in payload.get("entries", []):
            entry_id = str(raw_entry.get("id") or "").strip()
            if not entry_id or entry_id in seen_ids:
                continue
            seen_ids.add(entry_id)
            source_id = _normalize_id(entry_id) or entry_id
            vendor, product = _derive_vendor_product(source_id, raw_entry.get("vendor"), raw_entry.get("product"))
            artifacts = [_normalize_community_artifact(artifact) for artifact in raw_entry.get("artifacts", [])]
            capabilities = _compute_capabilities(artifacts, None)
            trust_level = COMMUNITY_DEFAULT_TRUST_LEVEL
            quality_status = COMMUNITY_DEFAULT_QUALITY_STATUS
            source_status = COMMUNITY_DEFAULT_SOURCE_STATUS
            quality_score = _quality_score({"trust_level": trust_level, "quality_status": quality_status}, capabilities)
            relationship = raw_entry.get("relationship_to_upstream") or "new_pack"
            merged_entries.append(
                {
                    "id": entry_id,
                    "display_name": raw_entry.get("display_name") or _display_name(entry_id, vendor, product, None),
                    "vendor": vendor,
                    "product": product,
                    "origins": [COMMUNITY_ORIGIN],
                    "effective_origin": COMMUNITY_ORIGIN,
                    "relationship_to_upstream": relationship,
                    "review_status": "unreviewed",
                    "trust_level": trust_level,
                    "quality_status": quality_status,
                    "quality_score": quality_score,
                    "is_verified": False,
                    "capabilities": capabilities,
                    "summary": str(raw_entry.get("summary") or f"Community candidate for {vendor} {product}"),
                    "upstream": {
                        "source_id": source_id,
                        "repo": None,
                        "ref": None,
                        "commit": None,
                        "generated_at": payload.get("generated_at"),
                        "sc4s_version": None,
                        "paths": [],
                    },
                    "upstream_drift": None,
                    "sc4s_manager": None,
                    "artifacts": artifacts,
                    "artifact_inventory": _artifact_inventory_by_type(artifacts),
                    "presets": [],
                    "preset_previews": [],
                    "fixture_results": [],
                    "fixture_summary": {"set_count": 0, "event_count": 0, "families": []},
                    "field_contract": {"mapping_status": "unknown", "cim": {}, "ocsf": {}, "ecs": {}},
                    "field_contract_summary": {"common": {"required_fields": [], "optional_fields": [], "present_fields": [], "missing_required_fields": [], "status": "unknown"}, "cim": {"declared_status": "unknown", "mapped_fields": [], "incomplete_fields": [], "coverage_gap_count": 0, "honesty_warnings": []}},
                    "comparison_to_upstream": _community_comparison(raw_entry, capabilities),
                    "validation": _community_validation(raw_entry),
                    "known_limitations": list(raw_entry.get("known_limitations") or []),
                    "feedback": {"likes": 0, "rating_average": None, "comments_url": None},
                    "provenance": _community_provenance(raw_entry),
                    "source_status": source_status,
                    "candidate_warnings": _community_candidate_warnings(raw_entry),
                }
            )
    return sorted(merged_entries, key=lambda item: (str(item.get("product", "")).lower(), str(item.get("vendor", "")).lower(), item["id"]))


def _matches_query(entry: dict[str, Any], query: str) -> bool:
    haystack = "\n".join(
        str(entry.get(key) or "")
        for key in ["id", "display_name", "vendor", "product", "summary"]
    ).lower()
    return all(token in haystack for token in query.lower().split())


FACET_LABELS = {
    "sc4s-inbuilt": "SC4S built-in",
    "sc4s-inbuilt-lite": "SC4S built-in Lite",
    "sechub-resource": "SecHub Resources SC4S pack",
    "community-extra": "Community extra",
    "parser": "Parser",
    "filters": "Filters",
    "postfilters": "Post-filters",
    "log_reduction": "Log reduction",
    "splunk_props_transforms": "Splunk knowledge",
    "cim_mapping": "CIM mapping",
    "ocsf_mapping": "OCSF mapping",
    "fixtures": "Fixtures",
    "syntax_validated": "Syntax validated",
    "splunk_ingestion_validated": "Splunk ingestion validated",
    "candidate": "Candidate",
}


def _title_label(value: str) -> str:
    label = FACET_LABELS.get(value)
    if label:
        return label
    if not value:
        return value
    return value.replace("_", " ").replace("-", " ").title()


def _facet_items(counts: dict[str, int], *, labels: dict[str, str] | None = None) -> list[dict[str, Any]]:
    labels = labels or {}
    return [
        {"value": value, "label": labels.get(value) or _title_label(value), "count": counts[value]}
        for value in sorted(counts)
        if value and counts[value] > 0
    ]


def _increment(counts: dict[str, int], value: Any) -> None:
    normalized = str(value or "").strip()
    if normalized:
        counts[normalized] = counts.get(normalized, 0) + 1


def catalogue_facets(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    origins: dict[str, int] = {}
    vendors: dict[str, int] = {}
    products: dict[str, int] = {}
    relationships: dict[str, int] = {}
    review_statuses: dict[str, int] = {}
    trust_levels: dict[str, int] = {}
    quality_statuses: dict[str, int] = {}
    source_statuses: dict[str, int] = {}
    artifact_types: dict[str, int] = {}
    capabilities: dict[str, int] = {}
    sc4s_versions: dict[str, int] = {}

    for entry in entries:
        for origin in entry.get("origins", []):
            _increment(origins, origin)
        _increment(vendors, entry.get("vendor"))
        _increment(products, entry.get("product"))
        _increment(relationships, entry.get("relationship_to_upstream"))
        _increment(review_statuses, entry.get("review_status"))
        _increment(trust_levels, entry.get("trust_level"))
        _increment(quality_statuses, entry.get("quality_status"))
        _increment(source_statuses, entry.get("source_status"))
        for artifact in entry.get("artifacts", []):
            _increment(artifact_types, artifact.get("type") or artifact.get("kind"))
        for capability, enabled in entry.get("capabilities", {}).items():
            if enabled:
                _increment(capabilities, capability)
        _increment(sc4s_versions, entry.get("upstream", {}).get("sc4s_version"))

    return {
        "origins": _facet_items(origins),
        "vendors": _facet_items(vendors),
        "products": _facet_items(products),
        "relationships": _facet_items(relationships),
        "review_statuses": _facet_items(review_statuses),
        "trust_levels": _facet_items(trust_levels),
        "quality_statuses": _facet_items(quality_statuses),
        "source_statuses": _facet_items(source_statuses),
        "artifact_types": _facet_items(
            artifact_types,
            labels={
                "syslog_app_parser": "syslog app parser",
                "netsource_app_parser": "netsource app parser",
                "source_documentation": "source documentation",
                "lite_addon": "Lite addon",
            },
        ),
        "capabilities": _facet_items(capabilities),
        "sc4s_versions": _facet_items(sc4s_versions),
    }


def _bool_filter(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean filter: {value}")


def filter_catalogue_entries(entries: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
    filtered = list(entries)
    q = str(filters.get("q") or "").strip()
    if q:
        filtered = [entry for entry in filtered if _matches_query(entry, q)]
    for key in ["vendor", "product", "relationship", "review_status", "trust_level", "quality_status", "source_status"]:
        value = str(filters.get(key) or "").strip().lower()
        if not value:
            continue
        source_key = "relationship_to_upstream" if key == "relationship" else key
        filtered = [entry for entry in filtered if str(entry.get(source_key) or "").lower() == value]
    origin = str(filters.get("origin") or "").strip().lower()
    if origin:
        filtered = [entry for entry in filtered if origin in {str(item).lower() for item in entry.get("origins", [])}]
    artifact_type = str(filters.get("artifact_type") or "").strip().lower()
    if artifact_type:
        filtered = [entry for entry in filtered if any(str(artifact.get("type") or "").lower() == artifact_type or str(artifact.get("kind") or "").lower() == artifact_type for artifact in entry.get("artifacts", []))]
    has_reduction = _bool_filter(filters.get("has_reduction")) if filters.get("has_reduction") is not None else None
    if has_reduction is not None:
        filtered = [entry for entry in filtered if bool(entry.get("capabilities", {}).get("log_reduction")) is has_reduction]
    has_splunk_knowledge = _bool_filter(filters.get("has_splunk_knowledge")) if filters.get("has_splunk_knowledge") is not None else None
    if has_splunk_knowledge is not None:
        filtered = [entry for entry in filtered if bool(entry.get("capabilities", {}).get("splunk_props_transforms")) is has_splunk_knowledge]
    is_verified = _bool_filter(filters.get("is_verified")) if filters.get("is_verified") is not None else None
    if is_verified is not None:
        filtered = [entry for entry in filtered if bool(entry.get("is_verified")) is is_verified]
    min_quality_score = filters.get("min_quality_score")
    if min_quality_score not in (None, ""):
        try:
            minimum_score = int(min_quality_score)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid min_quality_score filter: {min_quality_score}") from exc
        if minimum_score < 1 or minimum_score > 5:
            raise ValueError("min_quality_score must be between 1 and 5")
        filtered = [entry for entry in filtered if int(entry.get("quality_score") or 0) >= minimum_score]
    sc4s_version = str(filters.get("sc4s_version") or "").strip().lower()
    if sc4s_version:
        filtered = [entry for entry in filtered if sc4s_version in str(entry.get("upstream", {}).get("sc4s_version") or "").lower()]
    return filtered


def catalogue_inventory(packs_root: str | Path, manager_root: str | Path | None = None, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    entries = filter_catalogue_entries(build_catalogue_entries(packs_root, manager_root), filters)
    facets = catalogue_facets(entries)
    count = len(entries)
    limit = int(filters.get("limit", 50) or 50)
    offset = int(filters.get("offset", 0) or 0)
    if limit < 0 or offset < 0:
        raise ValueError("limit and offset must be non-negative")
    page = entries[offset : offset + limit]
    list_entries = []
    for entry in page:
        list_entries.append(
            {
                "id": entry["id"],
                "display_name": entry["display_name"],
                "vendor": entry["vendor"],
                "product": entry["product"],
                "origins": entry["origins"],
                "effective_origin": entry["effective_origin"],
                "relationship_to_upstream": entry["relationship_to_upstream"],
                "review_status": entry.get("review_status"),
                "trust_level": entry["trust_level"],
                "quality_status": entry["quality_status"],
                "quality_score": entry["quality_score"],
                "is_verified": entry["is_verified"],
                "capabilities": entry["capabilities"],
                "summary": entry["summary"],
                "source_status": entry.get("source_status"),
                "provenance_url": (entry.get("provenance") or {}).get("url"),
                "candidate_warnings": entry.get("candidate_warnings", []),
            }
        )
    return {"entries": list_entries, "count": count, "limit": limit, "offset": offset, "facets": facets}


def catalogue_detail(entry_id: str, packs_root: str | Path, manager_root: str | Path | None = None) -> dict[str, Any]:
    normalized = _normalize_id(entry_id)
    for entry in build_catalogue_entries(packs_root, manager_root):
        if entry["id"] == entry_id or _normalize_id(entry["id"]) == normalized:
            return entry
    raise KeyError(f"catalogue entry not found: {entry_id}")
