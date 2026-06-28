#!/usr/bin/env python3
"""Build a single-file SC4S Manager executable with PyInstaller.

The binary embeds the Python Manager app, built frontend assets, and built-in
packs. It does not embed secrets or mutable operator state.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SC4S Manager standalone binary.")
    parser.add_argument("--version", required=True, help="Release version string used in the output filename.")
    parser.add_argument("--output-dir", required=True, help="Directory to write the binary into.")
    parser.add_argument("--name", default="sc4s-manager", help="Base executable name.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frontend_index = ROOT / "frontend" / "dist" / "index.html"
    if not frontend_index.exists():
        print("error: frontend/dist/index.html is absent — run scripts/build_frontend.sh first", file=sys.stderr)
        return 1

    if shutil.which("pyinstaller") is None:
        print("error: pyinstaller is not installed in this Python environment", file=sys.stderr)
        print("hint: python3 -m venv /tmp/sc4s-manager-build && . /tmp/sc4s-manager-build/bin/activate && pip install pyinstaller", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / ".pyinstaller-work"
    spec_dir = output_dir / ".pyinstaller-spec"
    binary_name = f"{args.name}-{args.version}-linux-x86_64"

    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name", binary_name,
        "--distpath", str(output_dir),
        "--workpath", str(work_dir),
        "--specpath", str(spec_dir),
        "--paths", str(ROOT / "src"),
        "--add-data", f"{ROOT / 'frontend' / 'dist'}:frontend/dist",
        "--add-data", f"{ROOT / 'packs'}:packs",
        str(ROOT / "src" / "sc4s_manager" / "standalone.py"),
    ]
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        return result.returncode
    print(f"binary: {output_dir / binary_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
