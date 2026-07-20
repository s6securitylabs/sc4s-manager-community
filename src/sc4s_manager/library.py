from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlparse

try:
    from .packs import validate_pack, validate_pack_fixtures
except ImportError:  # Loaded via importlib.spec_from_file_location in tests
    from sc4s_manager.packs import validate_pack, validate_pack_fixtures

def _build_default_source(base_url: str) -> dict[str, Any]:
    base = base_url.rstrip("/")
    return {
        "source_id": "official",
        "catalogue_url": f"{base}/data/catalogue.json",
        "manifest_url": f"{base}/downloads/manifest.json",
        "entry_base_url": f"{base}/data/entries",
        "downloads_base_url": f"{base}/downloads",
        "enabled": True,
    }


_LIBRARY_SOURCE_URL = os.environ.get("SC4S_LIBRARY_SOURCE_URL", "https://sechub.s6ops.com").strip()
DEFAULT_SOURCES: list[dict[str, Any]] = (
    [_build_default_source(_LIBRARY_SOURCE_URL)]
    if _LIBRARY_SOURCE_URL and _LIBRARY_SOURCE_URL.lower() != "none"
    else []
)

MAX_JSON_BYTES = 2_000_000
MAX_ZIP_BYTES = 10_000_000
MAX_MEMBERS = 200
MAX_UNCOMPRESSED_BYTES = 20_000_000
MAX_MEMBER_BYTES = 5_000_000
LIBRARY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
LIBRARY_FETCH_HEADERS = {
    "User-Agent": "SC4S-Manager/1.0 (+https://github.com/s6securitylabs/sc4s-manager)",
    "Accept": "application/json, application/zip;q=0.9, */*;q=0.1",
}
RUNTIME_PREFIXES = ("local/config/", "local/context/")
REFERENCE_PREFIXES = ("env_file.d/", "splunk_app/", "test-events/", "scripts/")

LIBRARY_ERROR_NEXT_ACTIONS = {
    "dns_failure": "Check DNS resolution, source hostname, and outbound network policy from the Manager host.",
    "http_forbidden_or_bot_policy": "Check Cloudflare/bot policy, required client headers, and whether the Manager HTTP client is allowed to fetch this source.",
    "http_not_found": "Check that the configured catalogue, manifest, entry, or bundle URL exists in the current SecHub contract.",
    "manifest_missing": "Refresh the source and verify the downloads manifest contains the requested bundle filename/version/sha256.",
    "checksum_mismatch": "Do not apply the bundle; refresh the source and compare the manifest/detail sha256 against the downloaded artifact.",
    "bundle_too_large": "Reject the bundle or raise the Manager limit only after reviewing the source contract and archive contents.",
    "unsafe_archive_member": "Reject the bundle and fix the source artifact; archives must not contain traversal, absolute paths, symlinks, duplicates, or oversized members.",
    "schema_contract_mismatch": "Check the SecHub/Library contract version and required JSON fields before retrying import.",
    "timeout": "Check source reachability and retry; persistent timeouts need source or network remediation.",
    "unknown_fetch_error": "Review the controlled error detail and Manager logs, then retry after fixing the source contract or network path.",
}


class LibraryFetchError(ValueError):
    def __init__(self, code: str, message: str, *, next_action: str | None = None, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.next_action = next_action or LIBRARY_ERROR_NEXT_ACTIONS.get(code, LIBRARY_ERROR_NEXT_ACTIONS["unknown_fetch_error"])
        self.detail = detail or {}

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "next_action": self.next_action, "detail": self.detail}


def classify_library_exception(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, LibraryFetchError):
        return exc.as_dict()
    text = str(exc)
    lower = text.lower()
    code = "unknown_fetch_error"
    if isinstance(exc, TimeoutError) or "timed out" in lower or "timeout" in lower:
        code = "timeout"
    elif "name or service not known" in lower or "temporary failure in name resolution" in lower or "nodename nor servname" in lower or "dns" in lower:
        code = "dns_failure"
    elif "403" in lower or "forbidden" in lower or "bot" in lower or "cloudflare" in lower:
        code = "http_forbidden_or_bot_policy"
    elif "404" in lower or "not found" in lower:
        code = "http_not_found"
    elif "manifest" in lower and ("missing" in lower or "mismatch" in lower):
        code = "manifest_missing"
    elif "sha256" in lower or "checksum" in lower or "hash mismatch" in lower:
        code = "checksum_mismatch"
    elif "too large" in lower or "payload too large" in lower or "download too large" in lower:
        code = "bundle_too_large"
    elif "unsafe" in lower or "traversal" in lower or "symlink" in lower or "duplicate members" in lower or "escapes" in lower:
        code = "unsafe_archive_member"
    elif "schema" in lower or "required field" in lower or "must contain" in lower or "must be" in lower or "missing required" in lower:
        code = "schema_contract_mismatch"
    return {"code": code, "message": text, "next_action": LIBRARY_ERROR_NEXT_ACTIONS[code]}


def remote_trust_summary(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "remote_review_status": detail.get("review_status") or detail.get("quality_status") or detail.get("status"),
        "remote_trust_level": detail.get("trust_level"),
        "remote_quality_score": detail.get("quality_score"),
        "remote_validation": detail.get("validation"),
        "remote_is_verified": bool(detail.get("is_verified") or detail.get("validated_pack")),
        "advisory_only": True,
        "local_is_verified": False,
        "local_validation_state": "unverified",
        "local_verification_required": ["syslog_ng_syntax", "runtime_pack_validation", "splunk_readback"],
    }


def local_verification_summary(validation: dict[str, Any] | None = None) -> dict[str, Any]:
    validation = validation or {}
    stages = {
        "syslog_ng_syntax": False,
        "runtime_pack_validation": False,
        "splunk_readback": False,
    }
    for key in stages:
        value = validation.get(key)
        stages[key] = isinstance(value, dict) and value.get("ok") is True
    return {
        "is_verified": all(stages.values()),
        "state": "verified" if all(stages.values()) else "unverified",
        "stages": stages,
        "remote_metadata_can_verify": False,
    }


def validate_library_id(value: str, field: str = "library_id") -> str:
    candidate = str(value or "")
    if not LIBRARY_ID_RE.fullmatch(candidate) or candidate in {".", ".."}:
        raise ValueError(f"invalid library {field}")
    return candidate


def validate_download_filename(filename: str) -> str:
    candidate = str(filename or "")
    if (
        not candidate
        or candidate in {".", ".."}
        or "/" in candidate
        or "\\" in candidate
        or Path(candidate).is_absolute()
        or Path(candidate).name != candidate
        or not candidate.lower().endswith(".zip")
    ):
        raise ValueError("invalid library download filename")
    return candidate


def apply_live_state(validation: dict[str, Any], control: dict[str, Any], post_check: dict[str, Any]) -> dict[str, Any]:
    validation_ok = bool(validation.get("ok"))
    control_ok = bool(control.get("ok", True))
    post_ok: bool | None = None
    if "ok" in post_check:
        post_ok = bool(post_check.get("ok"))
    elif isinstance(post_check.get("health"), dict) and "ok" in post_check["health"]:
        post_ok = bool(post_check["health"].get("ok"))

    apply_state = "applied" if validation_ok and control_ok else "applied_reload_failed" if validation_ok else "validation_failed"
    if not validation_ok or not control_ok or post_ok is False:
        live_state = "not_live"
    elif post_ok is True:
        live_state = "live"
    else:
        live_state = "unknown"
    return {
        "apply_state": apply_state,
        "live_state": live_state,
    }


def _post_check_failed(post_check: dict[str, Any]) -> bool:
    """Only explicit negative live evidence triggers automatic rollback."""
    if post_check.get("ok") is False:
        return True
    health = post_check.get("health")
    if isinstance(health, dict) and health.get("ok") is False:
        return True
    docker = post_check.get("docker")
    if isinstance(docker, dict) and docker.get("running") is False:
        return True
    provider = post_check.get("control_provider")
    if isinstance(provider, dict) and provider.get("ok") is False:
        return True
    ports = post_check.get("ports")
    if isinstance(ports, dict):
        for state in ports.values():
            if isinstance(state, dict) and state.get("enabled") is True and state.get("listener_active") is False:
                return True
    return False


class LibraryManager:
    def __init__(
        self,
        *,
        root: Path,
        manager_root: Path,
        sources: list[dict[str, Any]] | None = None,
        fetch_json: Callable[[str, dict[str, Any], int], dict[str, Any]] | None = None,
        fetch_bytes: Callable[[str, dict[str, Any], int], bytes] | None = None,
        validate_config: Callable[[], dict[str, Any]] | None = None,
        reload_sc4s: Callable[[str], dict[str, Any]] | None = None,
        post_check: Callable[[], dict[str, Any]] | None = None,
        audit: Callable[[str, str, dict[str, Any]], None] | None = None,
        apply_lock: Any | None = None,
    ) -> None:
        self.root = Path(root)
        self.manager_root = Path(manager_root)
        self.library_dir = self.manager_root / "state" / "library"
        self.catalogue_dir = self.library_dir / "catalogue"
        self.entries_dir = self.library_dir / "entries"
        self.downloads_dir = self.library_dir / "downloads"
        self.imports_dir = self.library_dir / "imports"
        self.sources_file = self.library_dir / "sources.json"
        self._sources = [dict(source) for source in (sources if sources is not None else DEFAULT_SOURCES)]
        self._fetch_json = fetch_json or _default_fetch_json
        self._fetch_bytes = fetch_bytes or _default_fetch_bytes
        self._validate_config = validate_config or (lambda: {"ok": True, "skipped": True})
        self._reload_sc4s = reload_sc4s or (lambda actor: {"ok": True, "skipped": True, "actor": actor})
        self._post_check = post_check or (lambda: {})
        self._audit = audit or (lambda action, actor, details: None)
        self._apply_lock = apply_lock
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for path in [self.library_dir, self.catalogue_dir, self.entries_dir, self.downloads_dir, self.imports_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def sources(self) -> dict[str, Any]:
        state = self._load_sources_state()
        out = []
        for source in self._sources:
            merged = dict(source)
            merged.update(state.get("sources", {}).get(source["source_id"], {}))
            out.append(merged)
        return {"sources": out}

    def sync_source(self, source_id: str) -> dict[str, Any]:
        source_id = validate_library_id(source_id, "source_id")
        source = self._source(source_id)
        self._validate_source_urls(source)
        catalogue = self._fetch_json(source["catalogue_url"], source, MAX_JSON_BYTES)
        if not isinstance(catalogue, dict) or not isinstance(catalogue.get("entries", []), list):
            raise ValueError("library catalogue must contain an entries list")
        manifest = self._fetch_json(source["manifest_url"], source, MAX_JSON_BYTES)
        if not isinstance(manifest, dict):
            raise ValueError("downloads manifest must be a JSON object")
        atomic_write_json(self._catalogue_cache_path(source_id), catalogue)
        atomic_write_json(self._manifest_cache_path(source_id), manifest)
        state = self._load_sources_state()
        state.setdefault("sources", {})[source_id] = {
            "last_sync": now(),
            "entry_count": len(catalogue.get("entries", [])),
            "manifest_download_count": len(_manifest_downloads(manifest)),
            "catalogue_path": str(self._catalogue_cache_path(source_id)),
        }
        atomic_write_json(self.sources_file, state)
        return {
            "ok": True,
            "source_id": source_id,
            "entry_count": len(catalogue.get("entries", [])),
            "manifest_download_count": len(_manifest_downloads(manifest)),
            "last_sync": state["sources"][source_id]["last_sync"],
        }

    def catalogue(self, source_id: str = "official", filters: dict[str, Any] | None = None) -> dict[str, Any]:
        source_id = validate_library_id(source_id, "source_id")
        source = self._source(source_id)
        cached = self._read_json(self._catalogue_cache_path(source_id))
        if cached is None:
            self.sync_source(source_id)
            cached = self._read_json(self._catalogue_cache_path(source_id)) or {"entries": []}
        entries = list(cached.get("entries", []))
        filters = filters or {}
        search = str(filters.get("search", "")).strip().lower()
        downloadable_only = _truthy(filters.get("downloadable_only"))
        if downloadable_only:
            entries = [entry for entry in entries if entry.get("download_available")]
        if search:
            def matches(entry: dict[str, Any]) -> bool:
                haystack = " ".join(str(entry.get(key, "")) for key in ("id", "display_name", "vendor", "product")).lower()
                return search in haystack
            entries = [entry for entry in entries if matches(entry)]
        for entry in entries:
            entry.setdefault("source_id", source_id)
            entry.setdefault("source_type", "library_remote")
            entry["is_remote"] = True
            entry["remote_trust_advisory"] = remote_trust_summary(entry)
            entry["local_is_verified"] = False
            entry["local_validation_state"] = "unverified"
        return {
            "source_id": source_id,
            "source": {"source_id": source_id, "enabled": bool(source.get("enabled", True))},
            "entries": entries,
            "filters": {k: str(v) for k, v in filters.items() if v not in (None, "")},
        }

    def entry(self, source_id: str, entry_id: str, refresh: bool = False) -> dict[str, Any]:
        source_id = validate_library_id(source_id, "source_id")
        entry_id = validate_library_id(entry_id, "entry_id")
        source = self._source(source_id)
        cache_path = self._entry_cache_path(source_id, entry_id)
        detail = None if refresh else self._read_json(cache_path)
        if detail is None:
            detail_url = self._entry_url(source, entry_id)
            detail = self._fetch_json(detail_url, source, MAX_JSON_BYTES)
            self._validate_detail_shape(detail, entry_id, source)
            atomic_write_json(cache_path, detail)
        else:
            self._validate_detail_shape(detail, entry_id, source)
        summary = self._eligibility_summary(detail)
        return {
            "source_id": source_id,
            "entry": detail,
            "refresh": bool(refresh),
            "eligibility": summary,
            "remote_trust_advisory": remote_trust_summary(detail),
            "local_verification": local_verification_summary(),
        }

    def download_bundle(self, source_id: str, entry_id: str, *, refresh: bool = True) -> dict[str, Any]:
        source_id = validate_library_id(source_id, "source_id")
        entry_id = validate_library_id(entry_id, "entry_id")
        source = self._source(source_id)
        detail = self.entry(source_id, entry_id, refresh=refresh)["entry"]
        manifest_cache = self._read_json(self._manifest_cache_path(source_id))
        if manifest_cache is not None:
            self._cross_check_download_manifest(detail, manifest_cache)
        download = detail.get("download") or {}
        bundle_bytes = self._fetch_bytes(str(download.get("url", "")), source, MAX_ZIP_BYTES)
        if len(bundle_bytes) > MAX_ZIP_BYTES:
            raise ValueError("library zip too large")
        digest = sha256_bytes(bundle_bytes)
        if digest != download.get("sha256"):
            raise ValueError("library zip sha256 mismatch")
        filename = validate_download_filename(str(download.get("filename", "bundle.zip")))
        downloads_path = self._download_cache_path(source_id, filename)
        downloads_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_within(self.downloads_dir / source_id, downloads_path)
        downloads_path.write_bytes(bundle_bytes)
        extracted = inspect_bundle(bundle_bytes, detail)
        return {
            "ok": True,
            "source_id": source_id,
            "entry_id": entry_id,
            "detail": detail,
            "download": {
                "filename": filename,
                "sha256": digest,
                "expected_sha256": str(download.get("sha256", "")),
                "path": str(downloads_path),
                "url": str(download.get("url", "")),
                "size_bytes": len(bundle_bytes),
            },
            "verification": {
                "zip_sha256": digest,
                "manifest_verified": True,
                "artifact_count": len(extracted["artifacts"]),
            },
            "bundle_bytes": bundle_bytes,
            "extracted": extracted,
        }

    def validate_import(self, source_id: str, entry_id: str, *, actor: str = "manager") -> dict[str, Any]:
        source_id = validate_library_id(source_id, "source_id")
        entry_id = validate_library_id(entry_id, "entry_id")
        download_result = self.download_bundle(source_id, entry_id, refresh=True)
        detail = download_result["detail"]
        bundle_bytes = download_result["bundle_bytes"]
        extracted = download_result["extracted"]
        digest = download_result["download"]["sha256"]
        filename = download_result["download"]["filename"]
        downloads_path = Path(download_result["download"]["path"])
        import_id = f"imp_{entry_id}_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
        import_dir = self.imports_dir / import_id
        bundle_dir = import_dir / "bundle"
        reference_dir = import_dir / "reference"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        reference_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(Path(downloads_path)) as zf:
            for info in zf.infolist():
                if info.filename.endswith("/"):
                    continue
                target = (bundle_dir / info.filename).resolve()
                ensure_within(bundle_dir, target)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(info.filename))

        pack_validation: dict[str, Any] = {"ok": True, "skipped": True, "reason": "bundle has no embedded pack.json"}
        pack_manifest = bundle_dir / "pack.json"
        if pack_manifest.exists():
            pack = json.loads(pack_manifest.read_text())
            validate_pack(pack, bundle_dir)
            fixture_results = validate_pack_fixtures(pack, bundle_dir)
            pack_validation = {
                "ok": True,
                "pack_id": pack.get("id"),
                "pack_version": pack.get("version"),
                "fixture_sets": len(fixture_results),
                "fixture_event_count": sum(int(result.get("event_count", 0)) for result in fixture_results),
            }

        runtime_artifacts: list[dict[str, Any]] = []
        reference_artifacts: list[dict[str, Any]] = []
        for artifact in extracted["artifacts"]:
            staged = dict(artifact)
            staged["bundle_path"] = str(bundle_dir / artifact["source_path"])
            if is_runtime_target(artifact["target_path"]):
                runtime_artifacts.append(staged)
            else:
                reference_artifacts.append(staged)
                src = bundle_dir / artifact["source_path"]
                dest = reference_dir / artifact["target_path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

        runtime_plan = {
            "import_id": import_id,
            "source_id": source_id,
            "entry_id": entry_id,
            "artifacts": [
                {
                    "source_path": artifact["source_path"],
                    "target_path": artifact["target_path"],
                    "sha256": artifact["sha256"],
                    "kind": artifact.get("kind", "unknown"),
                }
                for artifact in runtime_artifacts
            ],
        }
        atomic_write_json(import_dir / "runtime-plan.json", runtime_plan)
        record = {
            "import_id": import_id,
            "source_id": source_id,
            "entry_id": entry_id,
            "detail": detail,
            "download": {
                "filename": filename,
                "sha256": digest,
                "path": str(downloads_path),
            },
            "created_at": now(),
            "runtime_files": runtime_artifacts,
            "reference_files": reference_artifacts,
            "apply_allowed": bool(runtime_artifacts),
            "reference_only": not runtime_artifacts,
            "pack_validation": pack_validation,
            "remote_trust_advisory": remote_trust_summary(detail),
            "local_verification": local_verification_summary(),
            "bundle_dir": str(bundle_dir),
            "reference_dir": str(reference_dir),
        }
        atomic_write_json(import_dir / "record.json", record)
        self._audit("library_validate_import", actor, {"import_id": import_id, "entry_id": entry_id, "source_id": source_id})
        return {
            "ok": True,
            "import_id": import_id,
            "source_id": source_id,
            "entry_id": entry_id,
            "apply_allowed": bool(runtime_artifacts),
            "reference_only": not runtime_artifacts,
            "runtime_files": runtime_artifacts,
            "reference_files": reference_artifacts,
            "verification": {
                "zip_sha256": digest,
                "manifest_verified": True,
                "artifact_count": len(extracted["artifacts"]),
            },
            "pack_validation": pack_validation,
            "remote_trust_advisory": remote_trust_summary(detail),
            "local_verification": local_verification_summary(),
        }

    def list_imports(self) -> dict[str, Any]:
        rows = []
        if self.imports_dir.exists():
            for record_path in sorted(self.imports_dir.glob("*/record.json"), reverse=True):
                record = self._read_json(record_path)
                if record:
                    rows.append(record)
        return {"imports": rows}

    def apply_import(self, import_id: str, actor: str, apply: bool = True) -> dict[str, Any]:
        import_id = validate_library_id(import_id, "import_id")
        record = self._read_json(self.imports_dir / import_id / "record.json")
        if not record:
            raise ValueError("library import not found")
        runtime_plan = self._read_json(self.imports_dir / import_id / "runtime-plan.json") or {"artifacts": []}
        detail = record.get("detail") or {}
        bundle_dir = Path(record.get("bundle_dir", ""))
        verified = self._revalidate_staged_bundle(bundle_dir, detail, runtime_plan)
        if not verified["ok"]:
            raise ValueError(verified["error"])
        if not record.get("apply_allowed"):
            return {
                "ok": True,
                "import_id": import_id,
                "apply": bool(apply),
                "apply_allowed": False,
                "reference_only": True,
                "changed_targets": [],
                "validation": {"ok": True, "skipped": True},
                "control": {"ok": True, "skipped": True},
                "post_check": {},
                "rolled_back": False,
            }
        if not apply:
            return {
                "ok": True,
                "import_id": import_id,
                "apply": False,
                "apply_allowed": True,
                "changed_targets": [artifact["target_path"] for artifact in runtime_plan.get("artifacts", [])],
                "validation": {"ok": True, "skipped": True},
                "control": {"ok": True, "skipped": True},
                "post_check": {},
                "rolled_back": False,
            }

        backups: list[tuple[Path, Path | None]] = []
        changed_targets: list[str] = []
        validation: dict[str, Any] = {}
        lock_context = self._apply_lock if self._apply_lock is not None else contextlib.nullcontext()
        try:
            with lock_context:
                for artifact in runtime_plan.get("artifacts", []):
                    target = resolve_runtime_target(self.root, artifact["target_path"])
                    source_path = (bundle_dir / artifact["source_path"]).resolve()
                    ensure_within(bundle_dir, source_path)
                    if sha256_bytes(source_path.read_bytes()) != artifact["sha256"]:
                        raise ValueError(f"runtime artifact hash mismatch for {artifact['target_path']}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    backup_path = None
                    if target.exists():
                        backup_path = create_backup_copy(target, self.manager_root / "backups" / "library", actor)
                    backups.append((target, backup_path))
                    shutil.copy2(source_path, target)
                    changed_targets.append(artifact["target_path"])
                validation = self._validate_config()
                if not validation.get("ok"):
                    raise ValidationFailure(validation)
                control = self._reload_sc4s(actor)
                post_check = self._post_check()
                if not control.get("ok", True) or _post_check_failed(post_check):
                    restore_backups(backups)
                    # A failed control action may have partially changed the
                    # runtime. Re-issue the fixed reload after restoring files
                    # so disk and running SC4S configuration converge.
                    rollback_runtime = self._reload_sc4s(actor)
                    rollback_post_check = self._post_check()
                    raise RuntimeApplyFailure(control, post_check, rollback_runtime, rollback_post_check)
            state = apply_live_state(validation, control, post_check)
            applied_at = now()
            record["last_apply"] = {
                "actor": actor,
                "applied_at": applied_at,
                "changed_targets": changed_targets,
                "rolled_back": False,
                "validation": validation,
                "control": control,
                "post_check": post_check,
                **state,
            }
            atomic_write_json(self.imports_dir / import_id / "record.json", record)
            self._audit("library_apply_import", actor, {"import_id": import_id, "changed_targets": changed_targets, "rolled_back": False})
            return {
                "ok": bool(validation.get("ok") and control.get("ok", True)),
                "import_id": import_id,
                "apply": True,
                "apply_allowed": True,
                "changed_targets": changed_targets,
                "validation": validation,
                "control": control,
                "post_check": post_check,
                "rolled_back": False,
                **state,
            }
        except ValidationFailure as failure:
            restore_backups(backups)
            self._audit("library_apply_import", actor, {"import_id": import_id, "changed_targets": changed_targets, "rolled_back": True})
            return {
                "ok": False,
                "import_id": import_id,
                "apply": True,
                "apply_allowed": True,
                "changed_targets": changed_targets,
                "validation": failure.validation,
                "control": {"ok": True, "skipped": True},
                "post_check": {},
                "rolled_back": True,
            }
        except RuntimeApplyFailure as failure:
            state = {
                "apply_state": "applied_reload_failed" if not failure.control.get("ok", True) else "applied",
                "live_state": "not_live",
            }
            record["last_apply"] = {
                "actor": actor,
                "applied_at": now(),
                "changed_targets": changed_targets,
                "rolled_back": True,
                "validation": validation,
                "control": failure.control,
                "post_check": failure.post_check,
                "rollback_runtime": failure.rollback_runtime,
                "rollback_post_check": failure.rollback_post_check,
                **state,
            }
            atomic_write_json(self.imports_dir / import_id / "record.json", record)
            self._audit("library_apply_import", actor, {
                "import_id": import_id,
                "changed_targets": changed_targets,
                "rolled_back": True,
                "rollback_runtime": failure.rollback_runtime,
            })
            return {
                "ok": False,
                "import_id": import_id,
                "apply": True,
                "apply_allowed": True,
                "changed_targets": changed_targets,
                "validation": validation,
                "control": failure.control,
                "post_check": failure.post_check,
                "rolled_back": True,
                "rollback_runtime": failure.rollback_runtime,
                "rollback_post_check": failure.rollback_post_check,
                **state,
            }
        except Exception:
            restore_backups(backups)
            raise

    def source_health(self, source_id: str = "official") -> dict[str, Any]:
        source_id = validate_library_id(source_id, "source_id")
        source = self._source(source_id)
        self._validate_source_urls(source)
        checks: list[dict[str, Any]] = []
        catalogue: dict[str, Any] | None = None
        manifest: dict[str, Any] | None = None
        sample_detail: dict[str, Any] | None = None

        catalogue = self._health_fetch_json(checks, "catalogue", str(source.get("catalogue_url", "")), source, MAX_JSON_BYTES)
        if isinstance(catalogue, dict) and not isinstance(catalogue.get("entries", []), list):
            checks[-1].update({"ok": False, "error_code": "schema_contract_mismatch", "message": "library catalogue must contain an entries list", "next_action": LIBRARY_ERROR_NEXT_ACTIONS["schema_contract_mismatch"]})
            catalogue = None

        manifest = self._health_fetch_json(checks, "manifest", str(source.get("manifest_url", "")), source, MAX_JSON_BYTES)
        if isinstance(manifest, dict) and not isinstance(manifest.get("downloads", []), list):
            checks[-1].update({"ok": False, "error_code": "manifest_missing", "message": "downloads manifest must contain a downloads list", "next_action": LIBRARY_ERROR_NEXT_ACTIONS["manifest_missing"]})
            manifest = None

        entries = catalogue.get("entries", []) if isinstance(catalogue, dict) and isinstance(catalogue.get("entries"), list) else []
        downloadable = next((entry for entry in entries if isinstance(entry, dict) and entry.get("download_available") and entry.get("id")), None)
        if downloadable:
            entry_id = str(downloadable.get("id"))
            sample_detail = self._health_fetch_json(checks, "sample_entry", self._entry_url(source, entry_id), source, MAX_JSON_BYTES)
            if isinstance(sample_detail, dict):
                try:
                    self._validate_detail_shape(sample_detail, entry_id, source)
                except Exception as exc:
                    err = classify_library_exception(exc)
                    checks[-1].update({"ok": False, "error_code": err["code"], "message": err["message"], "next_action": err["next_action"]})
                    sample_detail = None
        else:
            checks.append({"name": "sample_entry", "ok": False, "error_code": "manifest_missing", "message": "no downloadable entry found in catalogue", "next_action": "Sync a source that exposes at least one downloadable entry before testing bundle health."})

        if isinstance(sample_detail, dict):
            download = sample_detail.get("download") or {}
            bundle_url = str(download.get("url", ""))
            bundle_check = self._health_fetch_bytes(checks, "sample_bundle", bundle_url, source, MAX_ZIP_BYTES)
            bundle_bytes = bundle_check.get("bytes") if isinstance(bundle_check.get("bytes"), bytes) else None
            if bundle_bytes is not None:
                digest = sha256_bytes(bundle_bytes)
                bundle_check["sha256"] = digest
                bundle_check.pop("bytes", None)
                if digest != download.get("sha256"):
                    bundle_check.update({"ok": False, "error_code": "checksum_mismatch", "message": "downloaded bundle sha256 does not match entry detail", "next_action": LIBRARY_ERROR_NEXT_ACTIONS["checksum_mismatch"]})
                else:
                    try:
                        extracted = inspect_bundle(bundle_bytes, sample_detail)
                        bundle_check["artifact_count"] = len(extracted.get("artifacts", []))
                        bundle_check["sidecars"] = [artifact for artifact in extracted.get("artifacts", []) if not is_runtime_target(str(artifact.get("target_path", "")))]
                    except Exception as exc:
                        err = classify_library_exception(exc)
                        bundle_check.update({"ok": False, "error_code": err["code"], "message": err["message"], "next_action": err["next_action"]})
        else:
            checks.append({"name": "sample_bundle", "ok": False, "error_code": "manifest_missing", "message": "sample entry unavailable; bundle health not tested", "next_action": "Fix catalogue/entry health first, then retry bundle health."})

        overall_ok = all(bool(check.get("ok")) for check in checks)
        return {
            "source_id": source_id,
            "checked_at": now(),
            "overall_ok": overall_ok,
            "source": {
                "source_id": source_id,
                "enabled": bool(source.get("enabled", True)),
                "catalogue_url": source.get("catalogue_url"),
                "manifest_url": source.get("manifest_url"),
                "entry_base_url": source.get("entry_base_url"),
                "downloads_base_url": source.get("downloads_base_url"),
            },
            "checks": checks,
            "catalogue": {"entry_count": len(entries)},
            "manifest": {"download_count": len(_manifest_downloads(manifest or {}))},
            "sample_entry": {"id": sample_detail.get("id") if isinstance(sample_detail, dict) else None, "ok": isinstance(sample_detail, dict)},
            "sample_bundle": next((check for check in checks if check.get("name") == "sample_bundle"), {"ok": False}),
            "trust_semantics": {
                "remote_labels_are_advisory": True,
                "local_verification_requires_local_validation_json": True,
                "remote_metadata_can_set_local_is_verified": False,
            },
        }

    def _health_fetch_json(self, checks: list[dict[str, Any]], name: str, url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any] | None:
        started = dt.datetime.now(dt.timezone.utc)
        check: dict[str, Any] = {"name": name, "url": url, "ok": False}
        try:
            payload = self._fetch_json(url, source, max_bytes)
            elapsed_ms = int((dt.datetime.now(dt.timezone.utc) - started).total_seconds() * 1000)
            check.update({"ok": True, "elapsed_ms": elapsed_ms, "size_bytes": len(json.dumps(payload).encode("utf-8")), "content_type": "application/json", "sha256": sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))})
            checks.append(check)
            return payload
        except Exception as exc:
            err = classify_library_exception(exc)
            check.update({"ok": False, "error_code": err["code"], "message": err["message"], "next_action": err["next_action"]})
            checks.append(check)
            return None

    def _health_fetch_bytes(self, checks: list[dict[str, Any]], name: str, url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
        started = dt.datetime.now(dt.timezone.utc)
        check: dict[str, Any] = {"name": name, "url": url, "ok": False}
        try:
            payload = self._fetch_bytes(url, source, max_bytes)
            elapsed_ms = int((dt.datetime.now(dt.timezone.utc) - started).total_seconds() * 1000)
            check.update({"ok": True, "elapsed_ms": elapsed_ms, "size_bytes": len(payload), "content_type": "application/zip", "sha256": sha256_bytes(payload), "bytes": payload})
        except Exception as exc:
            err = classify_library_exception(exc)
            check.update({"ok": False, "error_code": err["code"], "message": err["message"], "next_action": err["next_action"]})
        checks.append(check)
        return check

    def _source(self, source_id: str) -> dict[str, Any]:
        source_id = validate_library_id(source_id, "source_id")
        for source in self._sources:
            if source.get("source_id") == source_id:
                return source
        raise ValueError("unknown library source")

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _load_sources_state(self) -> dict[str, Any]:
        return self._read_json(self.sources_file) or {"sources": {}}

    def _validate_source_urls(self, source: dict[str, Any]) -> None:
        for key in ("catalogue_url", "manifest_url"):
            validate_allowed_url(str(source.get(key, "")), source)

    def _entry_url(self, source: dict[str, Any], entry_id: str) -> str:
        entry_id = validate_library_id(entry_id, "entry_id")
        base = str(source.get("entry_base_url") or "").rstrip("/")
        url = f"{base}/{entry_id}.json"
        validate_allowed_url(url, source)
        return url

    def _validate_detail_shape(self, detail: dict[str, Any], entry_id: str, source: dict[str, Any]) -> None:
        entry_id = validate_library_id(entry_id, "entry_id")
        if detail.get("id") != entry_id:
            raise ValueError("library entry id mismatch")
        required = ["id", "version", "display_name", "vendor", "product", "capabilities", "artifacts", "download"]
        for key in required:
            if key not in detail:
                raise ValueError(f"library entry missing required field: {key}")
        download = detail.get("download") or {}
        for key in ("filename", "url", "sha256"):
            if not download.get(key):
                raise ValueError(f"library download missing required field: {key}")
        validate_allowed_url(str(download.get("url", "")), source)
        validate_download_filename(str(download.get("filename", "")))

    def _catalogue_cache_path(self, source_id: str) -> Path:
        source_id = validate_library_id(source_id, "source_id")
        path = (self.catalogue_dir / f"{source_id}.json").resolve()
        ensure_within(self.catalogue_dir, path)
        return path

    def _manifest_cache_path(self, source_id: str) -> Path:
        source_id = validate_library_id(source_id, "source_id")
        path = (self.library_dir / f"downloads-manifest-{source_id}.json").resolve()
        ensure_within(self.library_dir, path)
        return path

    def _entry_cache_path(self, source_id: str, entry_id: str) -> Path:
        source_id = validate_library_id(source_id, "source_id")
        entry_id = validate_library_id(entry_id, "entry_id")
        root = (self.entries_dir / source_id).resolve()
        path = (root / f"{entry_id}.json").resolve()
        ensure_within(root, path)
        return path

    def _download_cache_path(self, source_id: str, filename: str) -> Path:
        source_id = validate_library_id(source_id, "source_id")
        filename = validate_download_filename(filename)
        root = (self.downloads_dir / source_id).resolve()
        path = (root / filename).resolve()
        ensure_within(root, path)
        return path

    def _cross_check_download_manifest(self, detail: dict[str, Any], manifest: dict[str, Any]) -> None:
        download = detail.get("download") or {}
        matches = [
            item for item in _manifest_downloads(manifest)
            if item.get("filename") == download.get("filename")
        ]
        if not matches:
            return
        item = matches[0]
        if item.get("pack_id") != detail.get("id") or item.get("version") != detail.get("version") or item.get("sha256") != download.get("sha256"):
            raise ValueError("downloads manifest mismatch")

    def _eligibility_summary(self, detail: dict[str, Any]) -> dict[str, Any]:
        artifacts = detail.get("artifacts") if isinstance(detail.get("artifacts"), list) else []
        runtime_targets = [a for a in artifacts if is_runtime_target(str(a.get("target_path", "")))]
        return {
            "download_available": bool((detail.get("download") or {}).get("url")),
            "runtime_candidate_count": len(runtime_targets),
        }

    def _revalidate_staged_bundle(self, bundle_dir: Path, detail: dict[str, Any], runtime_plan: dict[str, Any]) -> dict[str, Any]:
        manifest_path = bundle_dir / "manifest.json"
        if not manifest_path.exists():
            return {"ok": False, "error": "staged bundle missing manifest.json"}
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("pack_id") != detail.get("id") or manifest.get("pack_version") != detail.get("version"):
            return {"ok": False, "error": "staged bundle manifest/detail mismatch"}
        artifact_by_source = {str(item.get("source_path")): item for item in manifest.get("artifacts", [])}
        for runtime in runtime_plan.get("artifacts", []):
            manifest_artifact = artifact_by_source.get(runtime.get("source_path"))
            if not manifest_artifact:
                return {"ok": False, "error": f"runtime artifact missing from manifest: {runtime.get('source_path')}"}
            source_path = bundle_dir / str(runtime.get("source_path", ""))
            if not source_path.exists():
                return {"ok": False, "error": f"staged runtime artifact missing: {runtime.get('source_path')}"}
            if sha256_bytes(source_path.read_bytes()) != manifest_artifact.get("sha256"):
                return {"ok": False, "error": f"staged runtime artifact hash mismatch: {runtime.get('source_path')}"}
        return {"ok": True}


def inspect_bundle(bundle_bytes: bytes, detail: dict[str, Any]) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        tmp.write(bundle_bytes)
        tmp.flush()
        with zipfile.ZipFile(tmp.name) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_MEMBERS:
                raise ValueError("library zip has too many members")
            names: set[str] = set()
            total_uncompressed = 0
            for info in infos:
                if info.filename in names:
                    raise ValueError("library zip has duplicate members")
                names.add(info.filename)
                if not info.filename or info.filename.startswith("/"):
                    raise ValueError("library zip has an unsafe member path")
                pure = PurePosixPath(info.filename)
                if any(part == ".." for part in pure.parts):
                    raise ValueError("library zip has a traversal member")
                if _zipinfo_is_symlink(info):
                    raise ValueError("library zip symlinks are not allowed")
                if info.is_dir():
                    continue
                total_uncompressed += info.file_size
                if info.file_size > MAX_MEMBER_BYTES:
                    raise ValueError("library zip member too large")
            if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("library zip total uncompressed content too large")
            if "manifest.json" not in names:
                raise ValueError("library zip missing manifest.json")
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            if manifest.get("pack_id") != detail.get("id"):
                raise ValueError("library manifest pack_id mismatch")
            if manifest.get("pack_version") != detail.get("version"):
                raise ValueError("library manifest pack_version mismatch")
            if not manifest.get("schema_version"):
                raise ValueError("library manifest missing schema_version")
            artifacts = []
            seen_targets: set[str] = set()
            for artifact in (manifest.get("artifacts") or []):
                source_path = str(artifact.get("source_path", ""))
                target_path = str(artifact.get("target_path", ""))
                digest = str(artifact.get("sha256", ""))
                if not source_path or source_path not in names:
                    raise ValueError(f"library manifest references missing artifact: {source_path}")
                if not target_path:
                    raise ValueError("library manifest artifact missing target_path")
                validate_target_path(target_path)
                if target_path in seen_targets:
                    raise ValueError("library manifest has duplicate target_path entries")
                seen_targets.add(target_path)
                data = zf.read(source_path)
                actual = sha256_bytes(data)
                if actual != digest:
                    raise ValueError(f"library manifest artifact hash mismatch: {source_path}")
                artifacts.append({
                    "kind": str(artifact.get("kind", "unknown")),
                    "source_path": source_path,
                    "target_path": target_path,
                    "sha256": digest,
                    "size": len(data),
                })
            return {"manifest": manifest, "artifacts": artifacts}


def validate_allowed_url(url: str, source: dict[str, Any]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("library URLs must use https")
    if not parsed.netloc:
        raise ValueError("library URL must include a hostname")
    allowed_hosts = {
        urlparse(str(source.get("catalogue_url", ""))).netloc,
        urlparse(str(source.get("manifest_url", ""))).netloc,
        urlparse(str(source.get("entry_base_url", ""))).netloc,
        urlparse(str(source.get("downloads_base_url", ""))).netloc,
    }
    allowed_hosts.discard("")
    if parsed.netloc not in allowed_hosts:
        raise ValueError("library URL host is not allowlisted")


def validate_target_path(target_path: str) -> None:
    pure = PurePosixPath(target_path)
    if target_path.startswith("/") or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe library target_path: {target_path}")


def is_runtime_target(target_path: str) -> bool:
    return any(target_path.startswith(prefix) for prefix in RUNTIME_PREFIXES)


def resolve_runtime_target(root: Path, target_path: str) -> Path:
    if not is_runtime_target(target_path):
        raise ValueError("target path is not runtime-safe")
    validate_target_path(target_path)
    resolved = (Path(root) / target_path).resolve()
    allowed_roots = [(Path(root) / "local" / "config").resolve(), (Path(root) / "local" / "context").resolve()]
    for allowed in allowed_roots:
        if resolved == allowed or str(resolved).startswith(str(allowed) + os.sep):
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
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, target)


def ensure_within(root: Path, candidate: Path) -> None:
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve()
    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError:
        raise ValueError("path escapes allowed root")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _manifest_downloads(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    downloads = manifest.get("downloads")
    if isinstance(downloads, list):
        return [item for item in downloads if isinstance(item, dict)]
    return []


def _truthy(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def _zipinfo_is_symlink(info: zipfile.ZipInfo) -> bool:
    return ((info.external_attr >> 16) & 0o170000) == 0o120000


def _default_fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    validate_allowed_url(url, source)
    opener = urllib.request.build_opener(_NoRedirectHandler())
    request = urllib.request.Request(url, headers=LIBRARY_FETCH_HEADERS)
    try:
        with opener.open(request, timeout=15) as response:
            final_url = response.geturl()
            validate_allowed_url(final_url, source)
            if final_url != url:
                raise LibraryFetchError("schema_contract_mismatch", "library redirects are not allowed")
            payload = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise LibraryFetchError("http_forbidden_or_bot_policy", f"library source returned HTTP {exc.code}") from exc
        if exc.code == 404:
            raise LibraryFetchError("http_not_found", f"library source returned HTTP {exc.code}") from exc
        raise LibraryFetchError("unknown_fetch_error", f"library source returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        code = classify_library_exception(exc)["code"]
        raise LibraryFetchError(code, reason) from exc
    if len(payload) > max_bytes:
        raise LibraryFetchError("bundle_too_large", "library JSON payload too large")
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise LibraryFetchError("schema_contract_mismatch", "library JSON payload must be an object")
    return data


def _default_fetch_bytes(url: str, source: dict[str, Any], max_bytes: int) -> bytes:
    validate_allowed_url(url, source)
    opener = urllib.request.build_opener(_NoRedirectHandler())
    request = urllib.request.Request(url, headers=LIBRARY_FETCH_HEADERS)
    try:
        with opener.open(request, timeout=30) as response:
            final_url = response.geturl()
            validate_allowed_url(final_url, source)
            if final_url != url:
                raise LibraryFetchError("schema_contract_mismatch", "library redirects are not allowed")
            payload = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise LibraryFetchError("http_forbidden_or_bot_policy", f"library source returned HTTP {exc.code}") from exc
        if exc.code == 404:
            raise LibraryFetchError("http_not_found", f"library source returned HTTP {exc.code}") from exc
        raise LibraryFetchError("unknown_fetch_error", f"library source returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        code = classify_library_exception(exc)["code"]
        raise LibraryFetchError(code, reason) from exc
    if len(payload) > max_bytes:
        raise LibraryFetchError("bundle_too_large", "library download too large")
    return payload


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise ValueError("library redirects are not allowed")


class ValidationFailure(Exception):
    def __init__(self, validation: dict[str, Any]) -> None:
        super().__init__("validation failed")
        self.validation = validation


class RuntimeApplyFailure(Exception):
    def __init__(
        self,
        control: dict[str, Any],
        post_check: dict[str, Any],
        rollback_runtime: dict[str, Any],
        rollback_post_check: dict[str, Any],
    ) -> None:
        super().__init__("runtime apply failed")
        self.control = control
        self.post_check = post_check
        self.rollback_runtime = rollback_runtime
        self.rollback_post_check = rollback_post_check
