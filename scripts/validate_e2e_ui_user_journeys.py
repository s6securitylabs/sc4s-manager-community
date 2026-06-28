#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def run_command(command: list[str], *, cwd: Path) -> dict[str, object]:
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {
        "command": command,
        "cwd": str(cwd),
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode == 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SC4S Manager e2e UI journey evidence capture plus source-level UI tests.")
    parser.add_argument("--public-url", default="https://sc4s-manager.s6securitylabs.com/")
    parser.add_argument("--internal-base-url", default="http://127.0.0.1:18090")
    parser.add_argument("--auth-mode", default="auto", choices=["auto", "direct", "manual-token", "api-token", "proxy"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = []

    results.append(
        run_command(
            [
                sys.executable,
                "scripts/browser_route_acceptance.py",
                "--public-url",
                args.public_url,
                "--internal-base-url",
                args.internal_base_url,
                "--auth-mode",
                args.auth_mode,
            ],
            cwd=ROOT,
        )
    )
    results.append(
        run_command(
            [sys.executable, "scripts/validate_acceptance_evidence.py", "--require-e2e-ui"],
            cwd=ROOT,
        )
    )
    results.append(
        run_command(
            [
                "npm",
                "test",
                "--",
                "src/components/AppLayout.test.tsx",
                "src/routes/CatalogueList.test.tsx",
                "src/routes/CatalogueDetail.test.tsx",
                "src/routes/Library.test.tsx",
                "src/routes/UserJourneyCoverage.test.tsx",
            ],
            cwd=FRONTEND,
        )
    )
    results.append(
        run_command(
            [
                "bash",
                "scripts/test.sh",
                "tests/test_browser_route_acceptance.py",
                "tests/test_acceptance_evidence.py",
            ],
            cwd=ROOT,
        )
    )

    ok = all(bool(item["ok"]) for item in results)
    print(json.dumps({"ok": ok, "results": results}, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
