#!/usr/bin/env python3
"""Generate or validate SC4S Manager CI functional acceptance evidence.

Default mode is safe/dry-run: it writes a manifest containing the disposable
Splunk LXC plan, UI page inventory, pack matrix, and SPL templates. Real LXC
execution and live browser/search evidence should be wired by CI with runtime
secrets injected outside committed evidence.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.ci_functional import main


if __name__ == "__main__":
    raise SystemExit(main())
