#!/usr/bin/env python3
"""Build a SC4S Manager release artifact tarball with accompanying manifest.

This script creates a deterministic release tarball and writes a manifest.json
beside it. It never invokes frontend build tools — frontend/dist must be pre-built
by scripts/build_frontend.sh before packaging. If frontend/dist is absent the
build fails unless --allow-missing-frontend is explicitly passed (test/CI only).

Usage:
    python3 scripts/build_release_artifact.py --version 0.9.0 --output-dir dist/
    python3 scripts/build_release_artifact.py --version 0.9.0 --output-dir dist/ --allow-missing-frontend
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "src"))
from sc4s_manager.packaging import REQUIRED_ARTIFACT_PATHS, build_manifest  # noqa: E402

# Paths included in the tarball beyond the required manifest paths.
EXTRA_ARTIFACT_PATHS = [
    "src/sc4s_manager/catalogue.py",
    "src/sc4s_manager/control.py",
    "src/sc4s_manager/exporters.py",
    "src/sc4s_manager/library.py",
    "src/sc4s_manager/pack_validation.py",
    "src/sc4s_manager/packs.py",
    "src/sc4s_manager/test_paths.py",
    "src/sc4s_manager/upstream_catalog.py",
    "src/sc4s_manager/__init__.py",
    "frontend/dist/",
    "packs/",
    "README.md",
]


def _git_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(root),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return "unknown"


def _add_dir_to_tarball(tf: tarfile.TarFile, src: Path, arcname_prefix: str) -> None:
    for child in sorted(src.rglob("*")):
        if child.is_file():
            rel = child.relative_to(src)
            tf.add(str(child), arcname=f"{arcname_prefix}{rel}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SC4S Manager release artifact tarball.")
    parser.add_argument("--version", required=True, help="Release version string (e.g. 0.9.0)")
    parser.add_argument("--output-dir", required=True, help="Directory to write tarball and manifest into")
    parser.add_argument(
        "--allow-missing-frontend",
        action="store_true",
        help="Skip the frontend/dist check (dry-run/test use only; do not use for real releases)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frontend_dist = ROOT / "frontend" / "dist" / "index.html"
    if not frontend_dist.exists() and not args.allow_missing_frontend:
        print(
            "error: frontend/dist/index.html is absent — run scripts/build_frontend.sh first.\n"
            "Use --allow-missing-frontend only for test/CI dry runs.",
            file=sys.stderr,
        )
        return 1

    created_at = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    git_commit = _git_commit(ROOT)

    manifest = build_manifest(
        version=args.version,
        git_commit=git_commit,
        created_at=created_at,
        root=ROOT,
    )

    tarball_name = f"sc4s-manager-{args.version}.tar.gz"
    tarball_path = output_dir / tarball_name
    arc_root = "sc4s-manager"

    with tarfile.open(tarball_path, "w:gz") as tf:
        for rel in REQUIRED_ARTIFACT_PATHS:
            src = ROOT / rel
            if src.exists():
                tf.add(str(src), arcname=f"{arc_root}/{rel}")

        for rel in EXTRA_ARTIFACT_PATHS:
            src = ROOT / rel
            if not src.exists():
                continue
            if src.is_dir():
                _add_dir_to_tarball(tf, src, f"{arc_root}/{rel}")
            else:
                tf.add(str(src), arcname=f"{arc_root}/{rel}")

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(f"artifact: {tarball_path}")
    print(f"manifest: {manifest_path}")
    if manifest["missing_required_paths"]:
        print(
            f"warning: {len(manifest['missing_required_paths'])} required path(s) absent from artifact: "
            + ", ".join(manifest["missing_required_paths"]),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
