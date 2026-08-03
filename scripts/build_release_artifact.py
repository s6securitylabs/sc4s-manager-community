#!/usr/bin/env python3
"""Build a deterministic SC4S Manager release archive and complete manifest."""
from __future__ import annotations

import argparse
import datetime
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sc4s_manager.packaging import REQUIRED_ARTIFACT_PATHS, build_archive_manifest  # noqa: E402

ARTIFACT_TREES = [
    "src/sc4s_manager", "frontend/dist", "packs", "embedded_library", "docs/runbooks",
    "docs/contracts", "docs/contributing",
]
ARTIFACT_FILES = ["README.md", "LICENSE", "pyproject.toml"]
MANAGER_VERSION_PATTERN = re.compile(r"SC4S_MANAGER_VERSION(?:(:-)|=)[^\s#}]+")


def _git_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(root),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return "unknown"


def _artifact_files() -> list[str]:
    files = set(REQUIRED_ARTIFACT_PATHS) | set(ARTIFACT_FILES)
    for tree in ARTIFACT_TREES:
        base = ROOT / tree
        if base.exists():
            files.update(str(path.relative_to(ROOT)) for path in base.rglob("*") if path.is_file())
    return sorted(files)


def _release_versioned_compose_text(text: str, version: str) -> str:
    """Bind packaged Compose templates to the requested release version."""
    updated, replacements = MANAGER_VERSION_PATTERN.subn(
        lambda match: f"SC4S_MANAGER_VERSION{match.group(1) or '='}{version}", text
    )
    if replacements != 1:
        raise ValueError("release Compose template must contain exactly one SC4S_MANAGER_VERSION pin")
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SC4S Manager release artifact tarball.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--allow-missing-frontend", action="store_true",
                        help="test-only: permit absent frontend build")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frontend_index = ROOT / "frontend" / "dist" / "index.html"
    if not frontend_index.exists() and not args.allow_missing_frontend:
        print("error: frontend/dist/index.html is absent — run scripts/build_frontend.sh first", file=sys.stderr)
        return 1

    created_at = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tarball = output_dir / f"sc4s-manager-{args.version}.tar.gz"
    with tarfile.open(tarball, "w:gz") as tf:
        for rel in _artifact_files():
            source = ROOT / rel
            if not source.is_file():
                continue
            if rel in {"deploy/compose/.env.example", "deploy/compose/compose.yaml"}:
                data = _release_versioned_compose_text(source.read_text(encoding="utf-8"), args.version).encode()
                info = tarfile.TarInfo(f"sc4s-manager/{rel}")
                info.size = len(data)
                info.mode = source.stat().st_mode & 0o777
                tf.addfile(info, io.BytesIO(data))
            else:
                tf.add(str(source), arcname=f"sc4s-manager/{rel}")

    manifest = build_archive_manifest(
        version=args.version, git_commit=_git_commit(ROOT), created_at=created_at, archive=tarball,
    )
    # Production honesty still fails closed on missing required paths. The
    # test-only --allow-missing-frontend flag only relaxes the SPA dist path so
    # packaging unit tests can run without a full frontend build; all other
    # required release members remain mandatory.
    missing = list(manifest["missing_required_paths"])
    if args.allow_missing_frontend:
        missing = [path for path in missing if path != "frontend/dist/index.html"]
        manifest["missing_required_paths"] = missing
        manifest["allow_missing_frontend"] = True
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"artifact: {tarball}")
    print(f"manifest: {manifest_path}")
    if missing:
        print("error: missing required paths: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
