"""Release artifact manifest builder.

Builds a typed manifest describing the contents of a release artifact.
Does not create tarballs, run builds, or access external services.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACT_PATHS = [
    "src/sc4s_manager/app.py",
    "src/sc4s_manager/control.py",
    "src/sc4s_manager/standalone.py",
    "Dockerfile",
    "deploy/compose/compose.yaml",
    "deploy/compose/.env.example",
    "deploy/compose/env_file.example",
    "deploy/compose/manager.env.example",
    "scripts/build_binary.py",
    ".github/workflows/release.yml",
    "deploy/systemd/sc4s-manager.service",
    "deploy/systemd/sc4s-manager-control.service",
    "deploy/systemd/sc4s-manager-control.socket",
    "deploy/install/install.sh",
    "deploy/upgrade/upgrade.sh",
    "frontend/dist/index.html",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_manifest(
    version: str,
    git_commit: str,
    created_at: str,
    root: Path,
) -> dict[str, Any]:
    """Return a manifest dict describing the release artifact contents.

    The manifest reports present files, their sizes and SHA-256 checksums,
    whether the frontend dist is present, and which required paths are missing.
    No tarballs are created; no builds are run.
    """
    paths: list[dict[str, Any]] = []
    missing: list[str] = []

    for rel in REQUIRED_ARTIFACT_PATHS:
        p = root / rel
        if p.exists():
            paths.append({
                "path": rel,
                "size_bytes": p.stat().st_size,
                "sha256": _sha256(p),
            })
        else:
            missing.append(rel)

    frontend_dist = root / "frontend" / "dist" / "index.html"

    return {
        "version": version,
        "git_commit": git_commit,
        "created_at": created_at,
        "paths": paths,
        "frontend_dist_present": frontend_dist.exists(),
        "missing_required_paths": missing,
    }
