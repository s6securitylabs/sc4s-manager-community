#!/usr/bin/env python3
"""SC4S Manager standalone binary entrypoint.

PyInstaller builds this module into a single-file executable. At startup it seeds
bundled static assets and built-in packs into SC4S_MANAGER_ROOT if they are not
already present, then starts the normal Manager app. Existing operator state is
not overwritten.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _bundle_root() -> Path:
    # PyInstaller exposes bundled data under sys._MEIPASS. In source/dev mode the
    # repository root is two parents above this file: src/sc4s_manager/standalone.py.
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled)
    return Path(__file__).resolve().parents[2]


def _copy_tree_if_missing(src: Path, dst: Path) -> None:
    if not src.exists() or dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


def seed_bundled_assets() -> None:
    root = Path(os.environ.get("SC4S_MANAGER_ROOT", "/opt/sc4s-manager"))
    bundle = _bundle_root()
    _copy_tree_if_missing(bundle / "frontend" / "dist", root / "frontend" / "dist")
    _copy_tree_if_missing(bundle / "packs", root / "packs")


def main() -> None:
    seed_bundled_assets()
    from sc4s_manager.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()
