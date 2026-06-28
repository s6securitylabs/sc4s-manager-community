from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any


class PackExportError(ValueError):
    """Raised when a pack cannot be safely exported."""


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_relative_path(value: str, field: str) -> Path:
    raw = str(value)
    normalized = raw.replace("\\", "/")
    rel = Path(normalized)
    if (
        not raw
        or raw in {"."}
        or raw.startswith("/")
        or re.match(r"^[A-Za-z]:[/\\]", raw)
        or rel.is_absolute()
        or ".." in rel.parts
        or str(rel) in {"", "."}
    ):
        raise PackExportError(f"artifact {field} must be a relative safe path")
    return rel


def _artifact_source(pack_dir: Path, source_path: str) -> Path:
    rel = _safe_relative_path(source_path, "source_path")
    base = pack_dir.resolve()
    path = (base / rel).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise PackExportError(f"artifact source_path escapes pack directory: {source_path}") from exc
    if not path.is_file():
        raise PackExportError(f"export artifact missing: {source_path}")
    return path


def _assert_export_allowed(artifact: dict[str, Any]) -> None:
    if artifact.get("contains_secrets") is True and not (artifact.get("rendered") is True or artifact.get("redacted") is True):
        artifact_id = artifact.get("id", artifact.get("source_path", "<unknown>"))
        raise PackExportError(f"export artifact {artifact_id} contains secrets and is not rendered/redacted")


def build_pack_export_bundle(pack: dict[str, Any], pack_dir: str | Path | None = None, *, created_at: str | None = None) -> tuple[str, bytes, dict[str, Any]]:
    """Build a zip export bundle for a pack from its export_artifacts.

    Bundle members preserve each artifact's source_path layout. manifest.json
    records source/target metadata and SHA-256 checksums of the exported bytes.
    """

    base = Path(pack_dir or pack.get("pack_dir") or ".")
    artifacts = pack.get("export_artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        raise PackExportError("pack export_artifacts must be a non-empty list")

    manifest_artifacts: list[dict[str, Any]] = []
    files: list[tuple[str, bytes]] = []
    seen: set[str] = set()
    for artifact in artifacts:
        _assert_export_allowed(artifact)
        source_path = str(artifact.get("source_path", ""))
        target_path = str(artifact.get("target_path", ""))
        _safe_relative_path(target_path, "target_path")
        source_file = _artifact_source(base, source_path)
        arcname = source_path.replace("\\", "/")
        if arcname in seen or arcname == "manifest.json":
            raise PackExportError(f"duplicate or reserved export artifact path: {arcname}")
        seen.add(arcname)
        data = source_file.read_bytes()
        files.append((arcname, data))
        manifest_artifacts.append({
            "source_path": arcname,
            "target_path": target_path.replace("\\", "/"),
            "kind": artifact.get("kind"),
            "sha256": hashlib.sha256(data).hexdigest(),
            "rendered": bool(artifact.get("rendered")),
            "contains_secrets": bool(artifact.get("contains_secrets")),
            "required": bool(artifact.get("required")),
        })

    manifest = {
        "pack_id": pack.get("id"),
        "pack_version": pack.get("version"),
        "schema_version": pack.get("schema_version"),
        "created_at": created_at or _utc_now_iso(),
        "artifacts": manifest_artifacts,
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        for arcname, data in files:
            bundle.writestr(arcname, data)

    filename = f"{pack.get('id')}-{pack.get('version')}.zip"
    return filename, buffer.getvalue(), manifest
