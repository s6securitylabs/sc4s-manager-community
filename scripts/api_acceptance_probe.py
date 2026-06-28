#!/usr/bin/env python3
"""SC4S Manager API acceptance probe.

Reads the manager token from SC4S_MANAGER_MANUAL_LOGIN_TOKEN first, falling back
to SC4S_MANAGER_API_TOKEN, and never prints token values. The probe avoids
destructive writes; negative tests use invalid inputs that should be rejected
before any state change is applied.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


MANUAL_TOKEN_ENV = "SC4S_MANAGER_MANUAL_LOGIN_TOKEN"
TOKEN_ENV = "SC4S_MANAGER_API_TOKEN"


@dataclass
class Check:
    name: str
    ok: bool
    status: int | None
    detail: str


def scrub(value: Any, secret: str) -> Any:
    if isinstance(value, dict):
        return {k: scrub(v, secret) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v, secret) for v in value]
    if isinstance(value, str) and secret:
        return value.replace(secret, "[REDACTED]")
    return value


def load_auth_token() -> tuple[str, str, str]:
    manual_token = os.environ.get(MANUAL_TOKEN_ENV, "")
    if manual_token:
        return manual_token, MANUAL_TOKEN_ENV, "bearer"
    api_token = os.environ.get(TOKEN_ENV, "")
    if api_token:
        return api_token, TOKEN_ENV, "legacy-header"
    return "", "unset", "none"


def request(base_url: str, method: str, path: str, token: str, auth_scheme: str = "bearer", data: dict[str, Any] | None = None) -> tuple[int, Any]:
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Authentik-Username": "acceptance.api"}
    if token:
        if auth_scheme == "legacy-header":
            headers["X-SC4S-Manager-Token"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(urllib.parse.urljoin(base_url, path), data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            parsed: Any = json.loads(text) if text else None
        except json.JSONDecodeError:
            parsed = text[:200]
        return exc.code, parsed
    except TimeoutError:
        return 598, {"error": "timeout"}
    except urllib.error.URLError as exc:
        return 599, {"error": type(exc).__name__}


def add_check(checks: list[Check], name: str, status: int | None, ok: bool, detail: str = "") -> None:
    checks.append(Check(name=name, ok=ok, status=status, detail=detail))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run non-destructive SC4S Manager API acceptance checks.")
    parser.add_argument("--base-url", default=os.environ.get("SC4S_MANAGER_BASE_URL", "http://127.0.0.1:8090"))
    parser.add_argument("--require-token", action="store_true", help=f"Fail immediately when neither {MANUAL_TOKEN_ENV} nor {TOKEN_ENV} is set.")
    parser.add_argument("--skip-authenticated", action="store_true", help="Only run open unauthenticated checks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token, token_source, auth_scheme = load_auth_token()
    if args.require_token and not token:
        print(json.dumps({"ok": False, "error": f"{MANUAL_TOKEN_ENV} or {TOKEN_ENV} is required but neither was set"}))
        return 2

    checks: list[Check] = []
    evidence: dict[str, Any] = {"base_url": args.base_url, "token_source": token_source}

    try:
        status, body = request(args.base_url, "GET", "/health", "")
        add_check(checks, "open health endpoint", status, status == 200, "health reachable")
        evidence["health"] = scrub(body, token)

        if args.skip_authenticated:
            pass
        elif not token:
            status, body = request(args.base_url, "GET", "/api/stats", "")
            add_check(checks, "protected API rejects missing token", status, status == 403, "expected forbidden without token")
            evidence["missing_token_response"] = scrub(body, token)
        else:
            for path in [
                "/api/health",
                "/api/stats",
                "/api/config",
                "/api/templates",
                "/api/products",
                "/api/source-catalog",
                "/api/destinations",
                "/api/metrics/syslog-ng",
                "/api/schema",
                "/api/tls",
                "/api/validate",
                "/api/backups",
                "/api/audit",
            ]:
                status, body = request(args.base_url, "GET", path, token, auth_scheme)
                add_check(checks, f"GET {path}", status, status == 200, "expected 200")
                if path in {"/api/config", "/api/destinations", "/api/schema"}:
                    evidence[path] = scrub(body, token)

            status, body = request(args.base_url, "GET", "/api/config/file?path=../env_file", token, auth_scheme)
            add_check(checks, "path traversal read rejected", status, status == 400, "expected 400")
            evidence["path_traversal_response"] = scrub(body, token)

            status, body = request(args.base_url, "POST", "/api/ports", token, auth_scheme, {"kind": "udp", "enabled": True, "port": 70000})
            add_check(checks, "invalid port rejected", status, status == 400, "expected 400")
            evidence["invalid_port_response"] = scrub(body, token)

            status, body = request(
                args.base_url,
                "POST",
                "/api/env",
                token,
                auth_scheme,
                {"key": "SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN", "value": "acceptance-placeholder"},
            )
            add_check(checks, "secret value rejected by normal env route", status, status == 400, "expected 400")
            evidence["secret_route_response"] = scrub(body, token)

            status, body = request(args.base_url, "POST", "/api/validate", token, auth_scheme, {})
            add_check(checks, "validation endpoint executes", status, status == 200, "expected 200")
            evidence["validate"] = scrub(body, token)

    except urllib.error.URLError as exc:
        add_check(checks, "manager reachable", None, False, type(exc).__name__)

    report = {
        "ok": all(check.ok for check in checks),
        "passed": sum(1 for check in checks if check.ok),
        "total": len(checks),
        "checks": [asdict(check) for check in checks],
        "evidence": evidence,
    }
    print(json.dumps(scrub(report, token), indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
