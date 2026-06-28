from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sc4s_manager.ci_functional import build_basic_spl, build_targeted_spl, field_presence_alias
from sc4s_manager.exporters import PackExportError, build_pack_export_bundle
from sc4s_manager.packs import (
    pack_by_id,
    validate_pack,
    validate_pack_fixtures,
)


class PackValidationError(ValueError):
    """Raised when pack validation fails with a stage-specific message."""

    def __init__(self, pack_id: str, stage: str, message: str):
        self.pack_id = pack_id
        self.stage = stage
        self.message = message
        super().__init__(f"{pack_id}:{stage}: {message}")


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_validation_evidence_dir(*, tmp_root: str | Path | None = None) -> Path:
    root = Path(tmp_root) if tmp_root is not None else Path(tempfile.gettempdir())
    return Path(tempfile.mkdtemp(prefix="sc4s-manager-validation-evidence.", dir=str(root)))


def standard_validation_evidence_dir(manager_root: str | Path) -> Path:
    return Path(manager_root) / "catalogue" / "generated" / "validation"


def validate_packs_bundle(
    packs: list[dict[str, Any]],
    *,
    pack_id: str | None = None,
    evidence_dir: str | Path | None = None,
    syslog_ng_validate_cmd: str | None = None,
    release_mode: bool = False,
    runtime_root: str | Path | None = None,
    runtime_send_cmd: str | None = None,
    splunk_search_cmd: str | None = None,
    listener_host: str | None = None,
) -> dict[str, Any]:
    selected = packs
    if pack_id is not None:
        selected = [pack_by_id(packs, pack_id)]

    generated_at = _utc_now_iso()
    bundle: dict[str, Any] = {
        "generated_at": generated_at,
        "pack_count": len(selected),
        "ok": True,
        "packs": [],
    }

    evidence_base = Path(evidence_dir) if evidence_dir else None
    if evidence_base is not None:
        evidence_base.mkdir(parents=True, exist_ok=True)

    for pack in selected:
        report = validate_single_pack(
            pack,
            generated_at=generated_at,
            evidence_dir=evidence_base,
            syslog_ng_validate_cmd=syslog_ng_validate_cmd,
            release_mode=release_mode,
            runtime_root=runtime_root,
            runtime_send_cmd=runtime_send_cmd,
            splunk_search_cmd=splunk_search_cmd,
            listener_host=listener_host,
        )
        bundle["packs"].append(report)
        if not report["ok"]:
            bundle["ok"] = False

    return bundle


def validate_single_pack(
    pack: dict[str, Any],
    *,
    generated_at: str | None = None,
    evidence_dir: Path | None = None,
    syslog_ng_validate_cmd: str | None = None,
    release_mode: bool = False,
    runtime_root: str | Path | None = None,
    runtime_send_cmd: str | None = None,
    splunk_search_cmd: str | None = None,
    listener_host: str | None = None,
) -> dict[str, Any]:
    pack_id = pack.get("id", "<unknown>")
    pack_dir = Path(pack["pack_dir"])
    generated_at = generated_at or _utc_now_iso()

    report: dict[str, Any] = {
        "pack_id": pack_id,
        "pack_version": pack.get("version"),
        "generated_at": generated_at,
        "ok": True,
        "checks": [],
    }

    def run_check(stage: str, fn):
        try:
            details = fn()
        except PackValidationError:
            raise
        except PackExportError as exc:
            raise PackValidationError(pack_id, stage, str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive catch to preserve actionable stage context
            raise PackValidationError(pack_id, stage, str(exc)) from exc
        report["checks"].append({"stage": stage, "ok": True, "details": details})
        return details

    try:
        run_check("manifest", lambda: _manifest_check(pack, pack_dir))
        fixture_results = run_check("fixtures", lambda: _fixture_check(pack, pack_dir))
        run_check("event_family_counts", lambda: _event_family_counts(pack, fixture_results))
        run_check("export_manifest", lambda: _export_manifest_check(pack, pack_dir, generated_at))
        run_check("splunk_knowledge", lambda: _splunk_knowledge_check(pack, pack_dir))
        run_check("sc4s_artifacts", lambda: _sc4s_artifact_check(pack, pack_dir))
        run_check(
            "syslog_ng_syntax",
            lambda: _syslog_ng_syntax_check(pack, pack_dir, syslog_ng_validate_cmd, release_mode=release_mode),
        )
        install_details = run_check(
            "runtime_artifact_install",
            lambda: _runtime_artifact_install_check(pack, pack_dir, runtime_root=runtime_root, evidence_dir=evidence_dir),
        )
        runtime_details = run_check(
            "runtime_pack_validation",
            lambda: _runtime_pack_validation_check(
                pack,
                pack_dir,
                install_details=install_details,
                runtime_send_cmd=runtime_send_cmd,
                release_mode=release_mode,
                listener_host=listener_host,
            ),
        )
        run_check(
            "splunk_readback",
            lambda: _splunk_readback_check(
                pack,
                runtime_details=runtime_details,
                splunk_search_cmd=splunk_search_cmd,
                release_mode=release_mode,
            ),
        )
    except PackValidationError as exc:
        report["ok"] = False
        report["error"] = {
            "stage": exc.stage,
            "message": exc.message,
        }

    if evidence_dir is not None:
        evidence_paths = write_validation_evidence(report, evidence_dir)
        report["evidence"] = evidence_paths

    return report


def write_validation_evidence(report: dict[str, Any], evidence_dir: Path) -> dict[str, str]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pack_id = str(report["pack_id"])
    base = evidence_dir / pack_id
    base.mkdir(parents=True, exist_ok=True)
    json_path = base / "validation-evidence.json"
    markdown_path = base / "validation-evidence.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    markdown_path.write_text(render_validation_markdown(report))
    return {
        "directory": str(base),
        "json": str(json_path),
        "markdown": str(markdown_path),
        "report_id": f"{pack_id}:{report.get('generated_at')}",
    }


def render_validation_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Validation evidence: {report['pack_id']}",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Pack version: {report.get('pack_version')}",
        f"- Result: {'PASS' if report.get('ok') else 'FAIL'}",
    ]
    if report.get("error"):
        lines.extend([
            f"- Failure stage: {report['error']['stage']}",
            f"- Failure reason: {report['error']['message']}",
        ])
    if report.get("evidence"):
        lines.append(f"- Evidence directory: {report['evidence'].get('directory')}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        stage = check["stage"]
        status = "PASS" if check.get("ok") else "FAIL"
        lines.append(f"### {stage}")
        lines.append("")
        lines.append(f"Status: {status}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(check.get("details", {}), indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_validation_text(bundle: dict[str, Any]) -> str:
    lines = [
        f"generated_at={bundle['generated_at']} packs={bundle['pack_count']} ok={bundle['ok']}",
    ]
    for report in bundle.get("packs", []):
        summary = f"{report['pack_id']}: {'PASS' if report.get('ok') else 'FAIL'}"
        if report.get("error"):
            summary += f" stage={report['error']['stage']} reason={report['error']['message']}"
        evidence = report.get("evidence", {}).get("directory")
        if evidence:
            summary += f" evidence={evidence}"
        lines.append(summary)
        for check in report.get("checks", []):
            details = check.get("details", {})
            detail_summary = _check_text_summary(check["stage"], details)
            lines.append(f"  - {check['stage']}: {detail_summary}")
    return "\n".join(lines)


def _check_text_summary(stage: str, details: dict[str, Any]) -> str:
    if stage == "manifest":
        return f"schema_version={details['schema_version']} export_artifacts={details['export_artifact_count']}"
    if stage == "fixtures":
        return f"fixtures={details['fixture_count']} events={details['total_events']}"
    if stage == "event_family_counts":
        families = ",".join(f"{family}={count}" for family, count in sorted(details["family_totals"].items()))
        return f"{families}"
    if stage == "export_manifest":
        return f"bundle={details['bundle_filename']} artifacts={details['artifact_count']}"
    if stage == "splunk_knowledge":
        return f"files={len(details['files'])} props={details['required_props_stanzas_checked']}"
    if stage == "sc4s_artifacts":
        return f"parser_files={len(details['parser_files'])} expected_sourcetypes={len(details['expected_sourcetypes'])}"
    if stage == "syslog_ng_syntax":
        return f"mode={details['mode']} status={details['status']}"
    if stage == "runtime_artifact_install":
        return f"root={details['runtime_root']} artifacts={len(details['installed_artifacts'])}"
    if stage == "runtime_pack_validation":
        return f"mode={details['mode']} status={details['status']} marker={details.get('marker')} event_sets={len(details.get('event_sets', []))}"
    if stage == "splunk_readback":
        return f"mode={details['mode']} status={details['status']} queries={details.get('query_count', 0)}"
    return json.dumps(details, sort_keys=True)


def _manifest_check(pack: dict[str, Any], pack_dir: Path) -> dict[str, Any]:
    validate_pack(pack, pack_dir)
    return {
        "schema_version": pack["schema_version"],
        "event_family_count": len(pack.get("event_families", [])),
        "export_artifact_count": len(pack.get("export_artifacts", [])),
        "pack_dir": str(pack_dir),
    }


def _fixture_check(pack: dict[str, Any], pack_dir: Path) -> dict[str, Any]:
    try:
        results = validate_pack_fixtures(pack, pack_dir)
    except ValueError as exc:
        raise PackValidationError(pack["id"], "fixtures", str(exc)) from exc
    return {
        "fixture_count": len(results),
        "total_events": sum(result["event_count"] for result in results),
        "results": results,
    }


def _event_family_counts(pack: dict[str, Any], fixture_results: dict[str, Any]) -> dict[str, Any]:
    declared = [family["id"] for family in pack.get("event_families", [])]
    totals = {family_id: 0 for family_id in declared}
    for result in fixture_results["results"]:
        for family_id, count in result["families"].items():
            totals[family_id] = totals.get(family_id, 0) + count
    missing = sorted(family_id for family_id, count in totals.items() if count == 0)
    if missing:
        raise PackValidationError(pack["id"], "event_family_counts", f"declared event families missing fixture coverage: {', '.join(missing)}")
    return {
        "declared_families": declared,
        "family_totals": totals,
    }


def _export_manifest_check(pack: dict[str, Any], pack_dir: Path, created_at: str) -> dict[str, Any]:
    filename, _data, manifest = build_pack_export_bundle(pack, pack_dir, created_at=created_at)
    return {
        "bundle_filename": filename,
        "artifact_count": len(manifest["artifacts"]),
        "artifacts": manifest["artifacts"],
    }


def _splunk_knowledge_check(pack: dict[str, Any], pack_dir: Path) -> dict[str, Any]:
    files: dict[str, Any] = {}
    export_artifacts = pack.get("export_artifacts", [])
    splunk_artifacts = [artifact for artifact in export_artifacts if artifact.get("group") == "splunk"]
    artifact_by_source = {artifact["source_path"]: artifact for artifact in splunk_artifacts}

    parsed_props: dict[str, list[dict[str, Any]]] | None = None
    parsed_transforms: dict[str, list[dict[str, Any]]] | None = None
    referenced_transform_stanzas: set[str] = set()
    required_props_stanzas = sorted(set(pack.get("sourcetypes", {}).values()))

    for rel_path in sorted(artifact_by_source):
        path = pack_dir / rel_path
        parsed = _parse_splunk_conf(path)
        summary = {
            "path": rel_path,
            "stanza_count": len(parsed["stanzas"]),
            "stanzas": sorted(parsed["stanzas"]),
            "comment_only": parsed["comment_only"],
        }
        files[rel_path] = summary
        if rel_path.endswith("props.conf"):
            parsed_props = parsed["stanzas"]
        elif rel_path.endswith("transforms.conf"):
            parsed_transforms = parsed["stanzas"]

    if parsed_props is None:
        raise PackValidationError(pack["id"], "splunk_knowledge", "missing required Splunk props.conf export artifact")

    missing_props = [stanza for stanza in required_props_stanzas if stanza not in parsed_props]
    if missing_props:
        raise PackValidationError(
            pack["id"],
            "splunk_knowledge",
            f"props.conf missing required sourcetype stanza(s): {', '.join(missing_props)}",
        )

    for stanza_name, entries in parsed_props.items():
        for entry in entries:
            key = entry["key"]
            if key.startswith("REPORT-") or key.startswith("TRANSFORMS-"):
                referenced_transform_stanzas.update(_split_conf_list(entry["value"]))

    if referenced_transform_stanzas and parsed_transforms is None:
        raise PackValidationError(
            pack["id"],
            "splunk_knowledge",
            f"props.conf references transform stanza(s) but transforms.conf export artifact is missing: {', '.join(sorted(referenced_transform_stanzas))}",
        )

    if parsed_transforms is not None:
        missing_transforms = sorted(name for name in referenced_transform_stanzas if name not in parsed_transforms)
        if missing_transforms:
            raise PackValidationError(
                pack["id"],
                "splunk_knowledge",
                f"transforms.conf missing referenced stanza(s): {', '.join(missing_transforms)}",
            )

    for rel_path, summary in files.items():
        if rel_path.endswith("eventtypes.conf") and not summary["comment_only"]:
            eventtypes = _parse_splunk_conf(pack_dir / rel_path)["stanzas"]
            missing_search = sorted(stanza for stanza, entries in eventtypes.items() if not any(entry["key"] == "search" for entry in entries))
            if missing_search:
                raise PackValidationError(
                    pack["id"],
                    "splunk_knowledge",
                    f"eventtypes.conf stanzas missing search= entries: {', '.join(missing_search)}",
                )

    return {
        "files": files,
        "required_props_stanzas_checked": required_props_stanzas,
        "referenced_transform_stanzas": sorted(referenced_transform_stanzas),
    }


def _sc4s_artifact_check(pack: dict[str, Any], pack_dir: Path) -> dict[str, Any]:
    parser_artifacts = [
        artifact for artifact in pack.get("export_artifacts", [])
        if artifact.get("group") == "sc4s" and artifact.get("kind") == "syslog_ng_parser"
    ]
    parser_files: list[str] = []
    parser_texts: list[str] = []
    for artifact in parser_artifacts:
        rel_path = artifact["source_path"]
        parser_files.append(rel_path)
        parser_texts.append((pack_dir / rel_path).read_text())

    expected_sourcetypes = sorted(set(pack.get("sourcetypes", {}).values()))
    combined_parser_text = "\n".join(parser_texts)
    missing_sourcetypes = [sourcetype for sourcetype in expected_sourcetypes if sourcetype not in combined_parser_text]
    if missing_sourcetypes:
        raise PackValidationError(
            pack["id"],
            "sc4s_artifacts",
            f"SC4S parser artifacts do not reference expected sourcetype(s): {', '.join(missing_sourcetypes)}",
        )

    return {
        "parser_files": parser_files,
        "expected_sourcetypes": expected_sourcetypes,
    }


def _syslog_ng_syntax_check(pack: dict[str, Any], pack_dir: Path, override_cmd: str | None, *, release_mode: bool = False) -> dict[str, Any]:
    command = override_cmd or os.environ.get("SC4S_MANAGER_SYSLOG_NG_VALIDATE_CMD")
    files = [
        artifact["source_path"]
        for artifact in pack.get("export_artifacts", [])
        if artifact.get("group") == "sc4s" and str(artifact.get("source_path", "")).endswith(".conf")
    ]
    if not command:
        if release_mode:
            raise PackValidationError(
                pack["id"],
                "syslog_ng_syntax",
                "runtime syslog-ng syntax validation is required in release mode; set SC4S_MANAGER_SYSLOG_NG_VALIDATE_CMD or pass --syslog-ng-validate-cmd",
            )
        return {
            "mode": "not_run",
            "status": "skipped",
            "reason": "set SC4S_MANAGER_SYSLOG_NG_VALIDATE_CMD to enable runtime syntax validation",
            "files": files,
        }

    with tempfile.NamedTemporaryFile("w", delete=False, prefix=f"{pack['id']}-syslog-ng-files-", suffix=".json") as handle:
        json.dump(files, handle)
        handle.flush()
        files_manifest = handle.name

    try:
        format_args = {
            "pack_dir": shlex.quote(str(pack_dir)),
            "pack_id": shlex.quote(str(pack["id"])),
            "files_json": shlex.quote(files_manifest),
        }
        rendered = command.format(**format_args)
        proc = subprocess.run(rendered, shell=True, capture_output=True, text=True)
    finally:
        Path(files_manifest).unlink(missing_ok=True)

    if proc.returncode != 0:
        raise PackValidationError(
            pack["id"],
            "syslog_ng_syntax",
            (proc.stderr or proc.stdout or "runtime syslog-ng validation failed").strip(),
        )

    return {
        "mode": "external_command",
        "status": "passed",
        "files": files,
        "stdout": (proc.stdout or "").strip(),
    }


def _runtime_artifact_install_check(
    pack: dict[str, Any],
    pack_dir: Path,
    *,
    runtime_root: str | Path | None,
    evidence_dir: Path | None,
) -> dict[str, Any]:
    base_root = Path(runtime_root) if runtime_root else None
    if base_root is None:
        if evidence_dir is not None:
            base_root = evidence_dir / "_runtime"
        else:
            base_root = default_validation_evidence_dir() / "runtime"
    pack_runtime_root = base_root / str(pack["id"])
    installed: list[dict[str, Any]] = []
    for artifact in pack.get("export_artifacts", []):
        source_path = pack_dir / str(artifact["source_path"])
        target_rel = Path(str(artifact["target_path"]))
        target_path = pack_runtime_root / target_rel
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        installed.append({
            "id": artifact.get("id"),
            "group": artifact.get("group"),
            "kind": artifact.get("kind"),
            "required": bool(artifact.get("required")),
            "source_path": str(source_path),
            "target_path": str(target_path),
            "target_relative_path": str(target_rel),
            "sha256": "sha256:" + hashlib.sha256(target_path.read_bytes()).hexdigest(),
        })
    return {
        "mode": "copied",
        "status": "passed",
        "runtime_root": str(pack_runtime_root),
        "installed_artifacts": installed,
    }


def _runtime_pack_validation_check(
    pack: dict[str, Any],
    pack_dir: Path,
    *,
    install_details: dict[str, Any],
    runtime_send_cmd: str | None,
    release_mode: bool,
    listener_host: str | None,
) -> dict[str, Any]:
    if not runtime_send_cmd:
        if release_mode:
            raise PackValidationError(
                pack["id"],
                "runtime_pack_validation",
                "runtime pack validation is required in release mode; set SC4S_MANAGER_RUNTIME_SEND_CMD or pass --runtime-send-cmd",
            )
        return {
            "mode": "not_run",
            "status": "skipped",
            "reason": "set SC4S_MANAGER_RUNTIME_SEND_CMD to enable test-event injection",
            "runtime_root": install_details["runtime_root"],
            "event_sets": [],
        }

    marker = f"sc4s-pack-{pack['id']}-{uuid.uuid4().hex[:12]}"
    event_reports: list[dict[str, Any]] = []
    runtime_root = Path(install_details["runtime_root"])
    payload_dir = runtime_root / "test-events"
    payload_dir.mkdir(parents=True, exist_ok=True)
    raw_listener = pack.get("listener")
    listener: dict[str, Any] = raw_listener if isinstance(raw_listener, dict) else {}
    transport = str(listener.get("transport") or pack.get("recommended_transport") or "")
    port = listener.get("port")
    source_id = listener.get("source_id")

    for event_set in pack.get("test_event_sets", []):
        raw_text = (pack_dir / str(event_set["path"])).read_text()
        rendered_text = raw_text.replace("<MARKER>", marker)
        payload_path = payload_dir / f"{event_set['id']}.payload"
        payload_path.write_text(rendered_text)
        format_args = {
            "pack_dir": shlex.quote(str(pack_dir)),
            "runtime_root": shlex.quote(str(runtime_root)),
            "pack_id": shlex.quote(str(pack["id"])),
            "event_set_id": shlex.quote(str(event_set["id"])),
            "payload_path": shlex.quote(str(payload_path)),
            "marker": shlex.quote(marker),
            "listener_host": shlex.quote(str(listener_host or "127.0.0.1")),
            "transport": shlex.quote(str(transport)),
            "port": shlex.quote(str(port or "")),
            "source_id": shlex.quote(str(source_id or "")),
            "event_count": shlex.quote(str(event_set.get("event_count", 0))),
        }
        proc = subprocess.run(runtime_send_cmd.format(**format_args), shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            raise PackValidationError(
                pack["id"],
                "runtime_pack_validation",
                (proc.stderr or proc.stdout or f"runtime send command failed for event set {event_set['id']}").strip(),
            )
        parsed_output = _maybe_parse_json(proc.stdout)
        event_reports.append({
            "event_set_id": event_set["id"],
            "fixture_path": str(pack_dir / str(event_set["path"])),
            "payload_path": str(payload_path),
            "event_count": event_set.get("event_count"),
            "marker_tokens": event_set.get("marker_tokens", []),
            "payload_preview": _payload_preview(rendered_text),
            "transport": transport,
            "listener_host": listener_host or "127.0.0.1",
            "listener_port": port,
            "command_stdout": (proc.stdout or "").strip(),
            "send_result": parsed_output,
        })

    return {
        "mode": "external_command",
        "status": "passed",
        "marker": marker,
        "runtime_root": str(runtime_root),
        "event_sets": event_reports,
    }


def _splunk_readback_check(
    pack: dict[str, Any],
    *,
    runtime_details: dict[str, Any],
    splunk_search_cmd: str | None,
    release_mode: bool,
) -> dict[str, Any]:
    if runtime_details.get("status") == "skipped":
        if release_mode:
            raise PackValidationError(
                pack["id"],
                "splunk_readback",
                "Splunk read-back cannot run because runtime pack validation was skipped in release mode",
            )
        return {
            "mode": "not_run",
            "status": "skipped",
            "reason": "runtime pack validation did not run",
            "query_count": 0,
            "results": [],
        }
    if not splunk_search_cmd:
        if release_mode:
            raise PackValidationError(
                pack["id"],
                "splunk_readback",
                "Splunk read-back is required in release mode; set SC4S_MANAGER_SPLUNK_SEARCH_CMD or pass --splunk-search-cmd",
            )
        return {
            "mode": "not_run",
            "status": "skipped",
            "reason": "set SC4S_MANAGER_SPLUNK_SEARCH_CMD to enable targeted SPL proof",
            "query_count": 0,
            "results": [],
        }

    marker = str(runtime_details["marker"])
    query_reports: list[dict[str, Any]] = []
    queries = [{
        "name": "basic",
        "family_id": "",
        "search": build_basic_spl(pack, marker),
    }]
    targeted = build_targeted_spl(pack, marker)
    for family_id, searches in targeted.items():
        queries.append({"name": "sourcetype_search", "family_id": family_id, "search": searches["sourcetype_search"]})
        queries.append({"name": "required_fields_search", "family_id": family_id, "search": searches["required_fields_search"]})

    for query in queries:
        format_args = {
            "pack_id": shlex.quote(str(pack["id"])),
            "family_id": shlex.quote(str(query["family_id"])),
            "search_name": shlex.quote(str(query["name"])),
            "search": shlex.quote(str(query["search"])),
            "marker": shlex.quote(marker),
            "runtime_root": shlex.quote(str(runtime_details.get("runtime_root", ""))),
        }
        proc = subprocess.run(splunk_search_cmd.format(**format_args), shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            raise PackValidationError(
                pack["id"],
                "splunk_readback",
                (proc.stderr or proc.stdout or f"Splunk search command failed for {query['name']}").strip(),
            )
        parsed = _require_json_object(pack["id"], "splunk_readback", proc.stdout)
        result_count = parsed.get("result_count")
        results = parsed.get("results")
        if not isinstance(result_count, int) or result_count <= 0:
            raise PackValidationError(pack["id"], "splunk_readback", f"{query['name']} for {query['family_id'] or 'basic'} returned no results")
        if not isinstance(results, list) or not results:
            raise PackValidationError(pack["id"], "splunk_readback", f"{query['name']} for {query['family_id'] or 'basic'} must return a non-empty results array")
        if marker not in json.dumps(results, sort_keys=True):
            raise PackValidationError(pack["id"], "splunk_readback", f"{query['name']} for {query['family_id'] or 'basic'} results do not contain marker {marker}")
        if query["name"] == "required_fields_search":
            family = next(item for item in pack.get("event_families", []) if item["id"] == query["family_id"])
            missing_fields = [
                field for field in family.get("required_fields", [])
                if not _field_presence_found(results, field_presence_alias(str(field)))
            ]
            if missing_fields:
                raise PackValidationError(
                    pack["id"],
                    "splunk_readback",
                    f"required_fields_search for {query['family_id']} missing field presence proof: {', '.join(missing_fields)}",
                )
        query_reports.append({
            "name": query["name"],
            "family_id": query["family_id"],
            "search": query["search"],
            "result_count": result_count,
            "results": results,
            "job": parsed.get("job"),
        })

    return {
        "mode": "external_command",
        "status": "passed",
        "marker": marker,
        "query_count": len(query_reports),
        "results": query_reports,
    }


def _payload_preview(text: str, *, max_lines: int = 3, max_chars: int = 240) -> list[str]:
    previews = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        previews.append(line[:max_chars])
        if len(previews) >= max_lines:
            break
    return previews


def _maybe_parse_json(text: str) -> Any:
    payload = (text or "").strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload


def _require_json_object(pack_id: str, stage: str, text: str) -> dict[str, Any]:
    parsed = _maybe_parse_json(text)
    if not isinstance(parsed, dict):
        raise PackValidationError(pack_id, stage, "command must emit a JSON object to stdout")
    return parsed


def _field_presence_found(results: list[Any], field_name: str) -> bool:
    for result in results:
        if isinstance(result, dict):
            value = result.get(field_name)
            if isinstance(value, (int, float)) and value > 0:
                return True
            if isinstance(value, str):
                try:
                    if float(value) > 0:
                        return True
                except ValueError:
                    pass
    return False


def _parse_splunk_conf(path: Path) -> dict[str, Any]:
    stanzas: dict[str, list[dict[str, Any]]] = {}
    current: str | None = None
    saw_content = False
    for line_no, raw_line in enumerate(path.read_text().splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        saw_content = True
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1].strip()
            if not current:
                raise PackValidationError(path.parent.parent.parent.name, "splunk_knowledge", f"{path.name}:{line_no} has an empty stanza header")
            stanzas.setdefault(current, [])
            continue
        if current is None:
            raise PackValidationError(path.parent.parent.parent.name, "splunk_knowledge", f"{path.name}:{line_no} defines a setting before any stanza header")
        if "=" not in raw_line:
            raise PackValidationError(path.parent.parent.parent.name, "splunk_knowledge", f"{path.name}:{line_no} is missing '='")
        key, value = raw_line.split("=", 1)
        key = key.strip()
        if not key:
            raise PackValidationError(path.parent.parent.parent.name, "splunk_knowledge", f"{path.name}:{line_no} has an empty key")
        stanzas[current].append({"key": key, "value": value.strip(), "line": line_no})
    return {
        "comment_only": saw_content is False,
        "stanzas": stanzas,
    }


def _split_conf_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r",\s*", value) if item.strip()]
