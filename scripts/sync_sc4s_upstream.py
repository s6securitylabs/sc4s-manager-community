#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.upstream_catalog import sync_main


if __name__ == "__main__":
    raise SystemExit(sync_main(manager_root=ROOT))
