"""Pinned, local-only SC4S Library snapshot access.

This module deliberately has no URL, HTTP, polling, or remote-cache path.  A
snapshot refresh is a repository maintenance action, never a Manager runtime
operation.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Callable

from sc4s_manager.packs import validate_pack_fixtures

EMBEDDED_SOURCE_ID = "embedded"
SNAPSHOT_SCHEMA_VERSION = "1.0"


def classify_embedded_library_exception(exc: BaseException) -> dict[str, str]:
    """Return a local-only failure contract without importing legacy fetch code."""
    message = str(exc)
    lower = message.lower()
    if "path" in lower or "target" in lower:
        code, next_action = "unsafe_snapshot_path", "Repair the committed snapshot; do not stage this pack."
    elif "snapshot" in lower or "manifest" in lower or "hash" in lower:
        code, next_action = "embedded_snapshot_invalid", "Repair or replace the pinned embedded snapshot before staging packs."
    else:
        code, next_action = "embedded_library_error", "Review the local snapshot and Manager logs before retrying."
    return {"code": code, "message": message, "next_action": next_action}


def local_verification_summary(validation: dict[str, Any] | None = None) -> dict[str, Any]:
    validation = validation or {}
    stages = {"syslog_ng_syntax": False, "runtime_pack_validation": False, "splunk_readback": False}
    for key in stages:
        value = validation.get(key)
        stages[key] = isinstance(value, dict) and value.get("ok") is True
    return {"is_verified": all(stages.values()), "state": "verified" if all(stages.values()) else "unverified", "stages": stages, "remote_metadata_can_verify": False}


def ensure_within(root: Path, candidate: Path) -> None:
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("path escapes allowed root") from exc


def resolve_runtime_target(root: Path, target_path: str) -> Path:
    pure = PurePosixPath(target_path)
    if target_path.startswith("/") or "\\" in target_path or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe library target_path: {target_path}")
    if not target_path.startswith(("local/config/", "local/context/")):
        raise ValueError("target path is not runtime-safe")
    resolved = (root / target_path).resolve()
    for allowed in ((root / "local" / "config").resolve(), (root / "local" / "context").resolve()):
        if resolved != allowed and str(resolved).startswith(str(allowed) + os.sep):
            return resolved
    raise ValueError("resolved runtime target escapes allowed local paths")


def create_backup_copy(path: Path, backup_root: Path, actor: str) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe_actor = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in actor)[:80] or "unknown"
    target = backup_root / f"{path.name}.{stamp}.{safe_actor}.bak"
    shutil.copy2(path, target)
    return target


def restore_backups(backups: list[tuple[Path, Path | None]]) -> None:
    for target, backup_path in reversed(backups):
        if backup_path is None:
            if target.exists():
                target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target)


def apply_live_state(validation: dict[str, Any], control: dict[str, Any], post_check: dict[str, Any]) -> dict[str, Any]:
    validation_ok, control_ok = bool(validation.get("ok")), bool(control.get("ok", True))
    post_ok = bool(post_check["ok"]) if "ok" in post_check else None
    return {"apply_state": "applied" if validation_ok and control_ok else "applied_reload_failed" if validation_ok else "validation_failed", "live_state": "live" if validation_ok and control_ok and post_ok is True else "not_live" if not validation_ok or not control_ok or post_ok is False else "unknown"}


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def snapshot_content_sha256(snapshot_root: Path, packs_root: Path) -> str:
    """Return the deterministic content digest required by SNAPSHOT.json."""
    digest = hashlib.sha256()
    for path in sorted(packs_root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(snapshot_root).as_posix().encode()
            digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).hexdigest().encode() + b"\n")
    return digest.hexdigest()


class EmbeddedLibraryManager:
    def __init__(self, *, root: Path, manager_root: Path, validate_config: Callable[[], dict[str, Any]], reload_sc4s: Callable[[str], dict[str, Any]], post_check: Callable[[], dict[str, Any]], audit: Callable[[str, str, dict[str, Any]], None], apply_lock: Any | None = None) -> None:
        self.root, self.manager_root = Path(root), Path(manager_root)
        self.snapshot_root = self.manager_root / "embedded_library"
        self.packs_root = self.snapshot_root / "packs"
        self.imports_dir = self.manager_root / "state" / "library" / "imports"
        self.validate_config, self.reload_sc4s, self.post_check, self.audit = validate_config, reload_sc4s, post_check, audit
        self.apply_lock = apply_lock
        self._verified_tree_hash: str | None = None
        self.imports_dir.mkdir(parents=True, exist_ok=True)

    def snapshot(self) -> dict[str, Any]:
        path = self.snapshot_root / "SNAPSHOT.json"
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("embedded Library snapshot metadata is unreadable") from exc
        required = {"schema_version", "source_repository", "source_ref", "source_revision", "source_tree", "pack_count", "snapshot_kind", "content_sha256"}
        if not isinstance(payload, dict) or required - payload.keys() or payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION or payload.get("snapshot_kind") != "immutable_embedded_library":
            raise ValueError("embedded Library snapshot metadata is malformed")
        if not isinstance(payload["pack_count"], int) or payload["pack_count"] < 1:
            raise ValueError("embedded Library snapshot pack_count is malformed")
        if not isinstance(payload["content_sha256"], str) or len(payload["content_sha256"]) != 64 or any(ch not in "0123456789abcdef" for ch in payload["content_sha256"]):
            raise ValueError("embedded Library snapshot content hash is malformed")
        return payload

    def _packs(self) -> list[dict[str, Any]]:
        snapshot = self.snapshot()
        self._verify_snapshot_content(snapshot)
        packs: list[dict[str, Any]] = []
        for manifest in sorted(self.packs_root.glob("*/pack.json")):
            try:
                pack = json.loads(manifest.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"embedded Library pack manifest is unreadable: {manifest.parent.name}") from exc
            if not isinstance(pack, dict) or not isinstance(pack.get("id"), str) or not pack["id"] or not isinstance(pack.get("artifacts"), dict) or not isinstance(pack.get("export_artifacts"), list):
                raise ValueError(f"embedded Library pack manifest is malformed: {manifest.parent.name}")
            pack["pack_dir"], pack["manifest_path"] = str(manifest.parent), str(manifest)
            packs.append(pack)
        if len(packs) != snapshot["pack_count"]:
            raise ValueError("embedded Library snapshot pack count does not match metadata")
        ids = [str(pack["id"]) for pack in packs]
        if len(ids) != len(set(ids)):
            raise ValueError("embedded Library snapshot has duplicate pack ids")
        return packs

    def _verify_snapshot_content(self, snapshot: dict[str, Any]) -> None:
        expected = snapshot["content_sha256"]
        if self._verified_tree_hash == expected:
            return
        actual = snapshot_content_sha256(self.snapshot_root, self.packs_root)
        if actual != expected:
            raise ValueError("embedded Library snapshot content hash does not match metadata")
        self._verified_tree_hash = actual

    def sources(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        return {"sources": [{"source_id": EMBEDDED_SOURCE_ID, "enabled": True, "entry_count": snapshot["pack_count"], "snapshot": snapshot}]}

    def source_health(self, source_id: str = EMBEDDED_SOURCE_ID) -> dict[str, Any]:
        self._source(source_id)
        packs = self._packs()
        return {"source_id": EMBEDDED_SOURCE_ID, "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(), "overall_ok": True, "checks": [{"name": "snapshot_integrity", "ok": True}], "catalogue": {"entry_count": len(packs)}, "sample_entry": {"ok": True, "id": packs[0]["id"]}, "sample_bundle": {"ok": True, "skipped": True}, "trust_semantics": {"snapshot_provenance_is_advisory": True, "local_verification_requires_local_validation_json": True, "snapshot_metadata_can_set_local_is_verified": False}, "snapshot": self.snapshot()}

    def catalogue(self, source_id: str = EMBEDDED_SOURCE_ID, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        self._source(source_id)
        filters = filters or {}
        search = str(filters.get("search", "")).lower().strip()
        entries = [self._entry_summary(pack) for pack in self._packs()]
        if search:
            entries = [entry for entry in entries if search in " ".join(str(entry.get(k, "")) for k in ("id", "display_name", "vendor", "product")).lower()]
        if str(filters.get("downloadable_only", "")).lower() in {"1", "true", "yes", "on"}:
            entries = [entry for entry in entries if entry["download_available"]]
        return {"source_id": EMBEDDED_SOURCE_ID, "source": {"source_id": EMBEDDED_SOURCE_ID, "enabled": True, "snapshot": self.snapshot()}, "entries": entries, "filters": {k: str(v) for k, v in filters.items() if v not in (None, "")}, "snapshot": self.snapshot()}

    def entry(self, source_id: str, entry_id: str, refresh: bool = False) -> dict[str, Any]:
        self._source(source_id)
        pack = self._pack(entry_id)
        runtime = self._runtime_artifacts(pack)
        detail = dict(pack)
        detail.pop("pack_dir", None); detail.pop("manifest_path", None)
        detail["source_type"] = "embedded_library"; detail["is_remote"] = False; detail["snapshot"] = self.snapshot()
        return {"source_id": EMBEDDED_SOURCE_ID, "entry": detail, "refresh": False, "eligibility": {"download_available": True, "runtime_candidate_count": len(runtime)}, "local_verification": local_verification_summary(), "snapshot": self.snapshot()}

    def validate_import(self, source_id: str, entry_id: str, *, actor: str = "manager") -> dict[str, Any]:
        self._source(source_id)
        pack = self._pack(entry_id)
        self._validate_pack_files(pack)
        fixture_results = validate_pack_fixtures(pack, pack["pack_dir"])
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        import_id = f"imp_{entry_id}_{stamp}"
        import_dir = self.imports_dir / import_id
        bundle_dir, reference_dir = import_dir / "bundle", import_dir / "reference"
        bundle_dir.mkdir(parents=True); reference_dir.mkdir(parents=True)
        runtime, reference = self._stage_artifacts(pack, bundle_dir, reference_dir)
        plan = {"import_id": import_id, "source_id": EMBEDDED_SOURCE_ID, "entry_id": entry_id, "artifacts": runtime, "snapshot": self.snapshot()}
        atomic_write_json(import_dir / "runtime-plan.json", plan)
        record = {"import_id": import_id, "source_id": EMBEDDED_SOURCE_ID, "entry_id": entry_id, "created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "detail": self.entry(EMBEDDED_SOURCE_ID, entry_id)["entry"], "runtime_files": runtime, "reference_files": reference, "apply_allowed": bool(runtime), "reference_only": not runtime, "pack_validation": {"ok": True, "fixture_validation": "passed", "fixture_results": fixture_results}, "local_verification": local_verification_summary(), "bundle_dir": str(bundle_dir), "reference_dir": str(reference_dir), "snapshot": self.snapshot()}
        atomic_write_json(import_dir / "record.json", record)
        self.audit("embedded_library_validate_import", actor, {"import_id": import_id, "entry_id": entry_id})
        return {"ok": True, **{k: record[k] for k in ("import_id", "source_id", "entry_id", "apply_allowed", "reference_only", "runtime_files", "reference_files", "pack_validation", "local_verification", "snapshot")}}

    def list_imports(self) -> dict[str, Any]:
        return {"imports": [json.loads(path.read_text()) for path in sorted(self.imports_dir.glob("*/record.json"), reverse=True)]}

    def apply_import(self, import_id: str, actor: str, apply: bool = True) -> dict[str, Any]:
        record_path = self.imports_dir / import_id / "record.json"
        if not record_path.is_file(): raise ValueError("embedded Library import not found")
        record = json.loads(record_path.read_text()); artifacts = record["runtime_files"]
        if not apply:
            return {"ok": True, "import_id": import_id, "apply": False, "apply_allowed": bool(artifacts), "changed_targets": [a["target_path"] for a in artifacts], "validation": {"ok": True, "skipped": True}, "control": {"ok": True, "skipped": True}, "post_check": {}, "rolled_back": False}
        backups: list[tuple[Path, Path | None]] = []; changed: list[str] = []
        try:
            for artifact in artifacts:
                source = Path(artifact["bundle_path"]).resolve(); ensure_within(Path(record["bundle_dir"]), source)
                if self._sha(source) != artifact["sha256"]: raise ValueError("staged embedded Library artifact hash mismatch")
                target = resolve_runtime_target(self.root, artifact["target_path"]); target.parent.mkdir(parents=True, exist_ok=True)
                backup = create_backup_copy(target, self.manager_root / "backups" / "library", actor) if target.exists() else None
                backups.append((target, backup)); shutil.copy2(source, target); changed.append(artifact["target_path"])
            validation = self.validate_config()
            if not validation.get("ok"): raise ValueError("SC4S validation failed")
            control = self.reload_sc4s(actor); post = self.post_check() if control.get("ok") else {}; state = apply_live_state(validation, control, post)
            self.audit("embedded_library_apply_import", actor, {"import_id": import_id, "changed_targets": changed})
            return {"ok": bool(control.get("ok")), "import_id": import_id, "apply": True, "apply_allowed": True, "changed_targets": changed, "validation": validation, "control": control, "post_check": post, "rolled_back": False, **state}
        except Exception:
            restore_backups(backups)
            raise

    def _source(self, source_id: str) -> None:
        if source_id not in {"", EMBEDDED_SOURCE_ID}: raise ValueError("remote library sources are retired; use embedded")

    def _pack(self, entry_id: str) -> dict[str, Any]:
        for pack in self._packs():
            if pack["id"] == entry_id: return pack
        raise ValueError("embedded Library pack not found")

    def _entry_summary(self, pack: dict[str, Any]) -> dict[str, Any]:
        return {"id": pack["id"], "display_name": pack.get("display_name"), "vendor": pack.get("vendor"), "product": pack.get("product"), "version": pack.get("version"), "download_available": True, "source_id": EMBEDDED_SOURCE_ID, "source_type": "embedded_library", "is_remote": False, "local_is_verified": False, "local_validation_state": "unverified", "snapshot": self.snapshot()}

    def _runtime_artifacts(self, pack: dict[str, Any]) -> list[dict[str, Any]]:
        return [artifact for artifact in pack.get("export_artifacts", []) if str(artifact.get("target_path", "")).startswith(("local/config/", "local/context/")) and not artifact.get("contains_secrets")]

    def _validate_pack_files(self, pack: dict[str, Any]) -> None:
        root = Path(pack["pack_dir"])
        for group in ("sc4s", "splunk", "test_events", "docs", "scripts"):
            for rel in pack.get("artifacts", {}).get(group, []):
                candidate = (root / str(rel)).resolve()
                ensure_within(root, candidate)
                if not candidate.is_file():
                    raise ValueError(f"embedded Library pack artifact is missing: {pack['id']}:{rel}")
        for artifact in pack.get("export_artifacts", []):
            if not isinstance(artifact, dict) or not isinstance(artifact.get("source_path"), str) or not isinstance(artifact.get("target_path"), str):
                raise ValueError(f"embedded Library export artifact is malformed: {pack['id']}")
            candidate = (root / artifact["source_path"]).resolve()
            ensure_within(root, candidate)
            if not candidate.is_file():
                raise ValueError(f"embedded Library export artifact is missing: {pack['id']}:{artifact['source_path']}")
            if artifact["target_path"].startswith(("local/config/", "local/context/")):
                resolve_runtime_target(self.root, artifact["target_path"])

    def _stage_artifacts(self, pack: dict[str, Any], bundle_dir: Path, reference_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        runtime: list[dict[str, Any]] = []; reference: list[dict[str, Any]] = []
        runtime_paths = {str(a["source_path"]): a for a in self._runtime_artifacts(pack)}
        for source in sorted(Path(pack["pack_dir"]).rglob("*")):
            if not source.is_file(): continue
            rel = source.relative_to(pack["pack_dir"]).as_posix(); target = (bundle_dir / rel).resolve(); ensure_within(bundle_dir, target); target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
            base = {"source_path": rel, "sha256": self._sha(source), "size": source.stat().st_size, "bundle_path": str(target)}
            if rel in runtime_paths:
                artifact = runtime_paths[rel]; runtime.append({**base, "target_path": artifact["target_path"], "kind": artifact.get("kind"), "size_bytes": source.stat().st_size})
            else:
                ref = reference_dir / rel; ref.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, ref); reference.append({**base, "target_path": rel, "kind": "reference"})
        return runtime, reference

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
