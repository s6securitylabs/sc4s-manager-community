#!/usr/bin/env python3
"""Capture authenticated screenshots of the CRUD operator UI routes.

Requires playwright with chromium. Authentication uses the manager API token
header (X-SC4S-Manager-Token, valid for localhost/tunnelled access) from the
SC4S_MANAGER_API_TOKEN environment variable, or the manual login token
(Authorization: Bearer) from SC4S_MANAGER_MANUAL_LOGIN_TOKEN when the manager
does not listen on loopback. Tokens are never written to artifacts or output.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture CRUD UI route screenshots.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8090")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--route", action="append", default=[], help="App route to capture (repeatable).")
    args = parser.parse_args()

    api_token = os.environ.get("SC4S_MANAGER_API_TOKEN", "")
    manual_token = os.environ.get("SC4S_MANAGER_MANUAL_LOGIN_TOKEN", "")
    if api_token:
        auth_headers = {"X-SC4S-Manager-Token": api_token}
    elif manual_token:
        auth_headers = {"Authorization": f"Bearer {manual_token}"}
    else:
        print(json.dumps({"ok": False, "error": "SC4S_MANAGER_API_TOKEN or SC4S_MANAGER_MANUAL_LOGIN_TOKEN is required"}))
        return 1
    routes = args.route or ["/sources", "/destinations", "/routes"]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    captured = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 1080},
            extra_http_headers=auth_headers,
        )
        page = context.new_page()
        for route in routes:
            target = args.base_url.rstrip("/") + route
            page.goto(target, wait_until="networkidle", timeout=45000)
            name = route.strip("/").replace("/", "-") or "root"
            path = out_dir / f"crud-ui-{name}.png"
            page.screenshot(path=str(path), full_page=True)
            captured.append({"route": route, "artifact_path": str(path), "title": page.title()})
        browser.close()

    print(json.dumps({"ok": True, "captured": captured}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
