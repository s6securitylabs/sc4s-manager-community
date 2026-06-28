#!/usr/bin/env python3
"""Capture sanitized browser-route acceptance evidence for SC4S Manager.

This runner is intentionally stdlib-only so it can execute on controller hosts,
CI runners, or via SSH tunnels without extra browser packages. It captures:

- public-route boundary checks against the Authentik-protected public URL;
- authenticated SPA route shell loads against the internal/local manager URL;
- route-specific API read-back summaries for each authenticated route; and
- per-route structured artifacts safe to commit.

It does not store live credentials, cookies, or raw Authorization headers in the
resulting evidence files.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = ROOT / "docs" / "acceptance"
DEFAULT_PUBLIC_OUTPUT = ACCEPTANCE / "browser-public-route-live.json"
DEFAULT_AUTH_OUTPUT = ACCEPTANCE / "browser-authenticated-route-live.json"
DEFAULT_JOURNEY_OUTPUT = ACCEPTANCE / "e2e-ui-user-journeys-live.json"
DEFAULT_JOURNEY_MARKDOWN = ACCEPTANCE / "e2e-ui-user-journeys.md"
DEFAULT_ARTIFACT_ROOT = ACCEPTANCE / "evidence" / "browser-routes"
DEFAULT_PUBLIC_URL = "https://sc4s-manager.s6securitylabs.com/"
DEFAULT_INTERNAL_BASE = "http://127.0.0.1:8090"
REDACTED = "[REDACTED]"

SECRET_KEY_PATTERN = re.compile(r"(?i)(authorization|cookie|set-cookie|token|session|secret|password|passwd|hec[_-]?token)")
SECRET_VALUE_PATTERN = re.compile(r"(?i)(bearer\s+[a-z0-9._~+\-/]+=*|x-sc4s-[a-z-]*token\s*[:=]\s*\S+|sc4s_manual_session=[^;\s]+)")
OAUTH_AUTHORIZE_URL_PATTERN = re.compile(r"(?i)(https://login\.s6ops\.com/application/o/authorize/)\?[^\"'\s<>]+")
OAUTH_QUERY_VALUE_PATTERN = re.compile(r"(?i)([?&](?:client_id|redirect_uri|response_type|scope|state|code)=)[^&\"'\s<>]+")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
HEADING_RE = re.compile(r"<(h1|h2)[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
TEXT_RE = re.compile(r"<[^>]+>")
SCRIPT_SRC_RE = re.compile(r"<script[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)


def repo_relative(path: str | Path) -> str:
    candidate = Path(path)
    try:
        return str(candidate.resolve().relative_to(ROOT))
    except (OSError, ValueError):
        return str(path)


STATIC_ROUTE_SPECS = [
    {"route": "/", "label": "Dashboard", "api_path": "/api/stats", "api_kind": "stats"},
    {
        "route": "/library",
        "label": "SecHub Resources",
        "api_path": "/api/library/catalogue?source_id=official",
        "api_kind": "library_catalogue",
        "api_fallbacks": [
            {
                "path": "/api/catalogue",
                "kind": "catalogue_list",
                "reason": "library API unavailable on this control-plane build; falling back to catalogue read-back",
            }
        ],
    },
    {"route": "/catalogue", "label": "Source Catalogue", "api_path": "/api/catalogue", "api_kind": "catalogue_list"},
    {"route": "/packs", "label": "Packs", "api_path": "/api/packs", "api_kind": "packs_list"},
    {"route": "/exports", "label": "Exports", "api_path": "/api/packs", "api_kind": "packs_list"},
]
PUBLIC_CHECKS = [
    {"name": "public_root", "path": "/", "expect_status": {302, 303, 403}},
    {"name": "public_health", "path": "/health", "expect_status": {302, 303, 403}},
    {"name": "public_api_stats", "path": "/api/stats", "expect_status": {302, 303, 403}},
]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


@dataclass
class FetchResult:
    url: str
    status: int
    final_url: str
    headers: dict[str, str]
    body_text: str
    content_type: str
    redirected_to: str | None = None
    error: str | None = None


class AcceptanceError(RuntimeError):
    pass


class BrowserRouteRunner:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.timeout = args.timeout
        self.user_agent = args.user_agent
        self.public_url = normalize_base_url(args.public_url)
        self.internal_base_url = normalize_base_url(args.internal_base_url)
        self.public_output = Path(args.public_output)
        self.auth_output = Path(args.auth_output)
        self.journey_output = Path(args.journey_output)
        self.journey_markdown = Path(args.journey_markdown)
        self.artifact_root = Path(args.artifact_root)
        self.timestamp = utc_now()
        self.run_slug = self.timestamp.replace(":", "").replace("-", "")
        self.artifact_dir = self.artifact_root / self.run_slug
        self.public_opener = build_opener()
        self.auth_cookie_jar = CookieJar()
        self.auth_opener = build_opener(self.auth_cookie_jar)
        self.auth_mode = args.auth_mode
        self.auth_source = "unauthenticated"
        self.auth_headers: dict[str, str] = {}

    def run(self) -> dict[str, Any]:
        public_payload = self.capture_public_boundary()
        auth_payload = self.capture_authenticated_routes()
        journey_payload = build_journey_matrix(public_payload, auth_payload, self.timestamp)
        write_json(self.public_output, public_payload)
        write_json(self.auth_output, auth_payload)
        write_json(self.journey_output, journey_payload)
        write_text(self.journey_markdown, render_journey_markdown(journey_payload))
        return {
            "ok": True,
            "captured_at_utc": self.timestamp,
            "public_output": str(self.public_output),
            "authenticated_output": str(self.auth_output),
            "journey_output": str(self.journey_output),
            "journey_markdown": str(self.journey_markdown),
            "artifact_dir": repo_relative(self.artifact_dir),
            "route_count": len(auth_payload.get("route_inventory", [])),
            "journey_count": len(journey_payload.get("journeys", [])),
            "auth_mode": self.auth_mode,
            "auth_source": self.auth_source,
        }

    def capture_public_boundary(self) -> dict[str, Any]:
        checks = []
        for item in PUBLIC_CHECKS:
            result = self.fetch_absolute(self.public_url, item["path"], opener=self.public_opener)
            check = summarize_public_result(item["name"], result, self.public_url)
            checks.append(check)
        return {
            "checked_at_utc": self.timestamp,
            "public_url": self.public_url,
            "results": checks,
            "notes": [
                "Statuses 302/303 prove Authentik redirect posture; 403 is accepted because some edge paths deny automated clients before redirect.",
                "Public evidence never includes cookies, Authorization headers, or authenticated page content.",
            ],
        }

    def capture_authenticated_routes(self) -> dict[str, Any]:
        auth_context = self.prepare_authenticated_session()
        stats_result = self.fetch_json(self.internal_base_url, "/api/stats")
        packs_result = self.fetch_json(self.internal_base_url, "/api/packs")
        catalogue_result = self.fetch_json(self.internal_base_url, "/api/catalogue")
        route_specs = build_route_specs(packs_result[1], catalogue_result[1])
        route_entries = []
        for spec in route_specs:
            route_entries.append(self.capture_route_entry(spec))

        unauthenticated_api_stats = summarize_public_result(
            "unauthenticated_api_stats_redirect",
            self.fetch_absolute(self.public_url, "/api/stats", opener=self.public_opener),
            self.public_url,
        )

        first_route = next((entry for entry in route_entries if entry["route"] == "/"), route_entries[0] if route_entries else {})
        stats_summary = summarize_api_payload(stats_result[1], kind="stats")
        payload = {
            "public_url": self.public_url,
            "authenticated_base_url": self.internal_base_url,
            "captured_at_utc": self.timestamp,
            "auth_context_redacted": True,
            "auth_mode": self.auth_mode,
            "auth_source": self.auth_source,
            "artifact_dir": repo_relative(self.artifact_dir),
            "route_inventory": route_entries,
            "api_inventory": {
                "packs": summarize_api_payload(packs_result[1], kind="packs_list"),
                "catalogue": summarize_api_payload(catalogue_result[1], kind="catalogue_list"),
            },
            "checks": {
                "authenticated_ui_load": {
                    "status": first_route.get("status"),
                    "title": first_route.get("title"),
                    "main_heading": first_route.get("main_heading"),
                    "contains": [value for value in [first_route.get("title"), first_route.get("main_heading")] if value],
                    "artifact_path": first_route.get("artifact_path"),
                    "body_prefix": first_route.get("body_excerpt"),
                    "route": "/",
                },
                "authenticated_api_stats": {
                    "status": stats_result[0].status,
                    "control_provider": stats_summary.get("control_provider"),
                    "health": stats_summary.get("health"),
                    "sc4s_image": stats_summary.get("sc4s_image"),
                    "artifact_path": self.write_artifact("api-stats", stats_summary),
                    "body_prefix": json.dumps(stats_summary, sort_keys=True)[:1200],
                    "content_type": stats_result[0].content_type,
                },
                "unauthenticated_api_stats_redirect": {
                    "status": unauthenticated_api_stats.get("status"),
                    "redirect_url": unauthenticated_api_stats.get("redirect_url"),
                    "body_prefix": unauthenticated_api_stats.get("body_prefix"),
                },
            },
            "identity": auth_context,
            "redactions": [
                "authorization",
                "cookie",
                "set-cookie",
                "password",
                "token",
                "session",
                "proxy_secret",
            ],
        }
        return sanitize_payload(payload)

    def prepare_authenticated_session(self) -> dict[str, Any]:
        if self.auth_mode == "auto":
            try:
                self.auth_mode = detect_auth_mode(self.args)
            except AcceptanceError:
                if self.internal_base_supports_direct_access():
                    self.auth_mode = "direct"
                else:
                    raise
        if self.auth_mode == "direct":
            self.auth_source = "internal-base-direct"
            self.auth_headers = {}
            return {
                "mode": "direct",
                "source": self.auth_source,
                "base_url": self.internal_base_url,
                "secrets": REDACTED,
            }
        if self.auth_mode == "manual-token":
            token = require_env(self.args.manual_token_env)
            login_url = self.internal_base_url + "/?login_token=" + urllib.parse.quote(token, safe="")
            self.fetch_raw(login_url, opener=self.auth_opener)
            self.auth_source = self.args.manual_token_env
            self.auth_headers = {}
            return {"mode": "manual-token", "source": self.auth_source, "username": self.args.proxy_username, "secrets": REDACTED}
        if self.auth_mode == "api-token":
            token = require_env(self.args.api_token_env)
            self.auth_headers = {"X-SC4S-Manager-Token": token}
            self.auth_source = self.args.api_token_env
            return {"mode": "api-token", "source": self.auth_source, "username": self.args.proxy_username, "secrets": REDACTED}
        if self.auth_mode == "proxy":
            secret = require_env(self.args.proxy_secret_env)
            groups = require_env(self.args.proxy_groups_env)
            self.auth_headers = {
                "X-SC4S-Manager-Proxy": secret,
                "X-Authentik-Username": self.args.proxy_username,
                "X-Authentik-Groups": groups,
            }
            self.auth_source = f"{self.args.proxy_secret_env}+{self.args.proxy_groups_env}"
            return {
                "mode": "proxy",
                "source": self.auth_source,
                "username": self.args.proxy_username,
                "groups": group_summary(groups),
                "secrets": REDACTED,
            }
        raise AcceptanceError(f"unsupported auth mode {self.auth_mode!r}")

    def internal_base_supports_direct_access(self) -> bool:
        probe_root = self.fetch_absolute(self.internal_base_url, "/", opener=self.auth_opener)
        if probe_root.status != 200 or extract_title(probe_root.body_text) != "SC4S Manager":
            return False
        probe_stats = self.fetch_absolute(self.internal_base_url, "/api/stats", opener=self.auth_opener)
        if probe_stats.status != 200:
            return False
        try:
            payload = json.loads(probe_stats.body_text)
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, dict):
            return False
        return bool(payload.get("health") or payload.get("control_provider") or payload.get("docker"))

    def capture_route_entry(self, spec: dict[str, Any]) -> dict[str, Any]:
        page = self.fetch_absolute(self.internal_base_url, spec["route"], opener=self.auth_opener, extra_headers=self.auth_headers)
        artifact_payload = {
            "route": spec["route"],
            "label": spec["label"],
            "kind": spec["kind"],
            "status": page.status,
            "final_url": page.final_url,
            "content_type": page.content_type,
            "title": extract_title(page.body_text),
            "main_heading": extract_heading(page.body_text),
            "body_excerpt": excerpt(page.body_text),
            "script_assets": extract_script_assets(page.body_text),
        }
        api_summary = None
        if spec.get("api_path"):
            api_result, api_payload, api_path, api_kind, fallback_reason = self.fetch_route_api(spec)
            api_summary = summarize_api_payload(api_payload, kind=api_kind)
            artifact_payload["api_path"] = api_path
            artifact_payload["api_requested_path"] = spec["api_path"]
            artifact_payload["api_status"] = api_result.status
            artifact_payload["api_kind"] = api_kind
            if fallback_reason:
                artifact_payload["api_fallback_reason"] = fallback_reason
            artifact_payload["api_summary"] = api_summary
        artifact_path = self.write_artifact(route_slug(spec["route"]), artifact_payload)
        return sanitize_payload({
            "route": spec["route"],
            "label": spec["label"],
            "kind": spec["kind"],
            "status": page.status,
            "final_url": page.final_url,
            "content_type": page.content_type,
            "title": artifact_payload["title"],
            "main_heading": artifact_payload["main_heading"],
            "body_excerpt": artifact_payload["body_excerpt"],
            "script_assets": artifact_payload["script_assets"],
            "artifact_path": artifact_path,
            "api_path": artifact_payload.get("api_path"),
            "api_requested_path": artifact_payload.get("api_requested_path"),
            "api_kind": artifact_payload.get("api_kind"),
            "api_fallback_reason": artifact_payload.get("api_fallback_reason"),
            "api_summary": api_summary,
        })

    def fetch_route_api(self, spec: dict[str, Any]) -> tuple[FetchResult, Any, str, str, str | None]:
        candidates: list[tuple[str, str, str | None]] = []
        primary_path = str(spec.get("api_path") or "").strip()
        primary_kind = str(spec.get("api_kind") or "generic")
        if primary_path:
            candidates.append((primary_path, primary_kind, None))
        for fallback in spec.get("api_fallbacks") or []:
            if not isinstance(fallback, dict):
                continue
            path = str(fallback.get("path") or "").strip()
            if not path:
                continue
            kind = str(fallback.get("kind") or primary_kind)
            reason = str(fallback.get("reason") or "fallback API path used")
            candidates.append((path, kind, reason))

        errors = []
        for path, kind, reason in candidates:
            result = self.fetch_absolute(self.internal_base_url, path, opener=self.auth_opener, extra_headers=self.auth_headers)
            if (result.status == 404 or result.status >= 500) and len(candidates) > 1:
                # 404: API absent on this build. 5xx: API present but its
                # upstream (e.g. remote SecHub source) is unreachable. Both
                # are recorded as a fallback, never rounded up to success.
                errors.append(f"{path} returned {result.status}")
                continue
            if result.status != 200:
                raise AcceptanceError(f"{path} returned unexpected status {result.status}")
            try:
                payload = json.loads(result.body_text)
            except json.JSONDecodeError as exc:
                raise AcceptanceError(f"{path} returned invalid JSON: {exc}") from exc
            return result, payload, path, kind, reason
        joined = "; ".join(errors) if errors else "no API candidates configured"
        raise AcceptanceError(f"could not capture route API evidence for {spec.get('route')}: {joined}")

    def fetch_json(self, base_url: str, path: str) -> tuple[FetchResult, Any]:
        result = self.fetch_absolute(base_url, path, opener=self.auth_opener, extra_headers=self.auth_headers)
        try:
            payload = json.loads(result.body_text)
        except json.JSONDecodeError as exc:
            raise AcceptanceError(f"{path} returned invalid JSON: {exc}") from exc
        return result, payload

    def fetch_absolute(
        self,
        base_url: str,
        path: str,
        *,
        opener: urllib.request.OpenerDirector,
        extra_headers: dict[str, str] | None = None,
    ) -> FetchResult:
        url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/")) if not path.startswith("http") else path
        return self.fetch_raw(url, opener=opener, extra_headers=extra_headers)

    def fetch_raw(
        self,
        url: str,
        *,
        opener: urllib.request.OpenerDirector,
        extra_headers: dict[str, str] | None = None,
    ) -> FetchResult:
        headers = {"User-Agent": self.user_agent, "Accept": "application/json, text/html;q=0.9, */*;q=0.8"}
        headers.update(extra_headers or {})
        request = urllib.request.Request(url, headers=headers)
        try:
            with opener.open(request, timeout=self.timeout) as response:
                body_text = response.read(self.args.max_response_bytes).decode("utf-8", "replace")
                headers_map = {k: v for k, v in response.headers.items()}
                return FetchResult(
                    url=url,
                    status=getattr(response, "status", 200),
                    final_url=response.geturl(),
                    headers=headers_map,
                    body_text=body_text,
                    content_type=response.headers.get("Content-Type", ""),
                )
        except urllib.error.HTTPError as exc:
            body_text = exc.read(self.args.max_response_bytes).decode("utf-8", "replace")
            headers_map = {k: v for k, v in exc.headers.items()}
            return FetchResult(
                url=url,
                status=exc.code,
                final_url=exc.geturl(),
                headers=headers_map,
                body_text=body_text,
                content_type=exc.headers.get("Content-Type", ""),
                redirected_to=headers_map.get("Location"),
                error=str(exc),
            )
        except Exception as exc:
            raise AcceptanceError(f"request failed for {url}: {type(exc).__name__}: {exc}") from exc

    def write_artifact(self, stem: str, payload: dict[str, Any]) -> str:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifact_dir / f"{stem}.json"
        write_json(path, sanitize_payload(payload))
        return repo_relative(path)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_opener(cookie_jar: CookieJar | None = None) -> urllib.request.OpenerDirector:
    handlers: list[Any] = [NoRedirectHandler()]
    if cookie_jar is not None:
        handlers.append(urllib.request.HTTPCookieProcessor(cookie_jar))
    return urllib.request.build_opener(*handlers)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture sanitized SC4S Manager browser route acceptance evidence.")
    parser.add_argument("--public-url", default=os.environ.get("SC4S_BROWSER_PUBLIC_URL", DEFAULT_PUBLIC_URL))
    parser.add_argument("--internal-base-url", default=os.environ.get("SC4S_MANAGER_BASE_URL", DEFAULT_INTERNAL_BASE))
    parser.add_argument("--public-output", default=str(DEFAULT_PUBLIC_OUTPUT))
    parser.add_argument("--auth-output", default=str(DEFAULT_AUTH_OUTPUT))
    parser.add_argument("--journey-output", default=str(DEFAULT_JOURNEY_OUTPUT))
    parser.add_argument("--journey-markdown", default=str(DEFAULT_JOURNEY_MARKDOWN))
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--auth-mode", choices=["auto", "direct", "manual-token", "api-token", "proxy"], default=os.environ.get("SC4S_BROWSER_AUTH_MODE", "auto"))
    parser.add_argument("--manual-token-env", default="SC4S_MANAGER_MANUAL_LOGIN_TOKEN")
    parser.add_argument("--api-token-env", default="SC4S_MANAGER_API_TOKEN")
    parser.add_argument("--proxy-secret-env", default="SC4S_MANAGER_PROXY_SECRET")
    parser.add_argument("--proxy-groups-env", default="SC4S_MANAGER_ADMIN_GROUPS")
    parser.add_argument("--proxy-username", default=os.environ.get("SC4S_BROWSER_PROXY_USERNAME", "acceptance.browser"))
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument(
        "--max-response-bytes",
        type=int,
        default=int(os.environ.get("SC4S_BROWSER_MAX_RESPONSE_BYTES", "5000000")),
        help="Maximum bytes to read per route/API response before parsing or summarising.",
    )
    parser.add_argument("--user-agent", default="sc4s-browser-acceptance/1.0")
    return parser.parse_args(argv)


def detect_auth_mode(args: argparse.Namespace) -> str:
    if os.environ.get(args.manual_token_env):
        return "manual-token"
    if os.environ.get(args.api_token_env):
        return "api-token"
    if os.environ.get(args.proxy_secret_env) and os.environ.get(args.proxy_groups_env):
        return "proxy"
    raise AcceptanceError(
        "no authenticated route mechanism available; set SC4S_MANAGER_MANUAL_LOGIN_TOKEN, "
        "or SC4S_MANAGER_API_TOKEN (via localhost/SSH tunnel), or SC4S_MANAGER_PROXY_SECRET + SC4S_MANAGER_ADMIN_GROUPS"
    )


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise AcceptanceError(f"required environment variable {name} is not set")
    return value


def normalize_base_url(value: str) -> str:
    text = value.rstrip("/")
    return text if text.endswith("/") else text + "/"


def build_route_specs(packs_payload: Any, catalogue_payload: Any) -> list[dict[str, Any]]:
    routes = [dict(item, kind="static") for item in STATIC_ROUTE_SPECS]
    packs = packs_payload.get("packs", []) if isinstance(packs_payload, dict) else []
    if packs:
        first = packs[0]
        pack_id = str(first.get("id") or "").strip()
        if pack_id:
            routes.append({
                "route": f"/packs/{urllib.parse.quote(pack_id, safe='')}",
                "label": f"Pack detail: {first.get('display_name') or pack_id}",
                "kind": "pack_detail",
                "api_path": f"/api/packs/{urllib.parse.quote(pack_id, safe='')}",
                "api_kind": "pack_detail",
            })
    entries = catalogue_payload.get("entries", []) if isinstance(catalogue_payload, dict) else []
    if entries:
        first = entries[0]
        entry_id = str(first.get("id") or "").strip()
        if entry_id:
            routes.append({
                "route": f"/catalogue/{urllib.parse.quote(entry_id, safe='')}",
                "label": f"Catalogue detail: {first.get('display_name') or entry_id}",
                "kind": "catalogue_detail",
                "api_path": f"/api/catalogue/{urllib.parse.quote(entry_id, safe='')}",
                "api_kind": "catalogue_detail",
            })
    return routes


def extract_title(body: str) -> str:
    match = TITLE_RE.search(body or "")
    return clean_text(match.group(1)) if match else ""


def extract_heading(body: str) -> str:
    for _, inner in HEADING_RE.findall(body or ""):
        text = clean_text(inner)
        if text:
            return text
    return ""


def extract_script_assets(body: str) -> list[str]:
    assets = []
    for src in SCRIPT_SRC_RE.findall(body or ""):
        clean = src.strip()
        if clean:
            assets.append(clean)
    return assets[:10]


def clean_text(value: str) -> str:
    text = html.unescape(TEXT_RE.sub(" ", value or ""))
    return re.sub(r"\s+", " ", text).strip()


def excerpt(body: str, limit: int = 800) -> str:
    return sanitize_text((body or "")[:limit])


def route_slug(route: str) -> str:
    if route == "/":
        return "root"
    text = route.strip("/").replace("/", "-")
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", text)
    return text or "route"


def sanitize_text(value: str) -> str:
    text = value or ""
    text = SECRET_VALUE_PATTERN.sub(REDACTED, text)
    text = OAUTH_AUTHORIZE_URL_PATTERN.sub(r"\1?[REDACTED_OAUTH_QUERY]", text)
    text = OAUTH_QUERY_VALUE_PATTERN.sub(r"\1[REDACTED]", text)
    lines = []
    for line in text.splitlines():
        parts = re.split(r"([:=])", line, maxsplit=1)
        if len(parts) >= 3:
            key_text = parts[0].strip().strip('"\'')
            if SECRET_KEY_PATTERN.search(key_text):
                line = parts[0] + parts[1] + REDACTED
        lines.append(line)
    return "\n".join(lines)


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            if SECRET_KEY_PATTERN.search(str(key)) and item not in (True, False, None):
                output[key] = REDACTED
            else:
                output[key] = sanitize_payload(item)
        return output
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def summarize_public_result(name: str, result: FetchResult, public_base: str) -> dict[str, Any]:
    location = result.headers.get("Location") or result.redirected_to or ""
    return sanitize_payload({
        "name": name,
        "url": result.url,
        "status": result.status,
        "redirect_url": location,
        "final_url": result.final_url,
        "content_type": result.content_type,
        "body_prefix": excerpt(result.body_text, limit=500),
        "login_boundary_seen": ("login.s6ops.com" in location.lower()) or ("application/o/authorize" in result.body_text.lower()),
        "public_base": public_base,
    })


def summarize_api_payload(payload: Any, *, kind: str) -> dict[str, Any]:
    if kind == "stats" and isinstance(payload, dict):
        docker = cast(dict[str, Any], payload.get("docker")) if isinstance(payload.get("docker"), dict) else {}
        metrics = cast(dict[str, Any], payload.get("metrics_summary")) if isinstance(payload.get("metrics_summary"), dict) else {}
        running_version = payload.get("running_sc4s_version") or docker.get("image_version")
        supported_version = payload.get("supported_sc4s_version")
        return sanitize_payload({
            "health": payload.get("health"),
            "control_provider": payload.get("control_provider"),
            "sc4s_image": docker.get("image"),
            "running_sc4s_version": running_version,
            "supported_sc4s_version": supported_version,
            "version_drift": bool(running_version and supported_version and running_version != supported_version),
            "disk": payload.get("disk"),
            "metrics_summary": {
                "processed": metrics.get("processed"),
                "matched": metrics.get("matched"),
                "discarded": metrics.get("discarded"),
            } if metrics else None,
            "warning_count": payload.get("log_findings", {}).get("warning_count") if isinstance(payload.get("log_findings"), dict) else None,
            "error_count": payload.get("log_findings", {}).get("error_count") if isinstance(payload.get("log_findings"), dict) else None,
        })
    if kind == "packs_list" and isinstance(payload, dict):
        packs = payload.get("packs") or []
        first = packs[0] if packs else {}
        return sanitize_payload({
            "count": payload.get("count", len(packs)),
            "first_pack": {
                "id": first.get("id"),
                "display_name": first.get("display_name"),
                "vendor": first.get("vendor"),
                "product": first.get("product"),
                "recommended_transport": first.get("recommended_transport"),
                "test_event_set_count": len(first.get("test_event_sets") or []),
            } if isinstance(first, dict) else None,
        })
    if kind == "catalogue_list" and isinstance(payload, dict):
        entries = payload.get("entries") or []
        first = entries[0] if entries else {}
        facets = cast(dict[str, Any], payload.get("facets")) if isinstance(payload.get("facets"), dict) else {}

        def facet_count(name: str, value: str) -> int | None:
            items = facets.get(name)
            if not isinstance(items, list):
                return None
            for item in items:
                if isinstance(item, dict) and item.get("value") == value:
                    count = item.get("count")
                    if isinstance(count, bool):
                        return int(count)
                    if isinstance(count, (int, float, str)):
                        try:
                            return int(count)
                        except Exception:
                            return None
                    return None
            return 0

        return sanitize_payload({
            "count": payload.get("count", len(entries)),
            "validated_count": facet_count("quality_statuses", "validated"),
            "community_candidate_count": facet_count("source_statuses", "candidate"),
            "curated_origin_count": facet_count("origins", "sechub-resource"),
            "first_entry": {
                "id": first.get("id"),
                "display_name": first.get("display_name"),
                "vendor": first.get("vendor"),
                "product": first.get("product"),
                "source_status": first.get("source_status"),
                "quality_status": first.get("quality_status"),
            } if isinstance(first, dict) else None,
        })
    if kind == "library_catalogue" and isinstance(payload, dict):
        entries = payload.get("entries") or []
        first = entries[0] if entries else {}
        return sanitize_payload({
            "source_id": payload.get("source_id"),
            "count": len(entries),
            "filters": payload.get("filters"),
            "first_entry": {
                "id": first.get("id"),
                "display_name": first.get("display_name"),
                "vendor": first.get("vendor"),
                "product": first.get("product"),
                "download_available": first.get("download_available"),
            } if isinstance(first, dict) else None,
        })
    if kind == "pack_detail" and isinstance(payload, dict):
        export_artifacts = payload.get("export_artifacts") or []
        groups = sorted({str(item.get("group")) for item in export_artifacts if isinstance(item, dict) and item.get("group")})
        transports = payload.get("supported_transports") or []
        first_transport = transports[0] if transports else {}
        test_event_sets = payload.get("test_event_sets") or []
        first_test_event = test_event_sets[0] if test_event_sets else {}
        return sanitize_payload({
            "id": payload.get("id"),
            "display_name": payload.get("display_name"),
            "vendor": payload.get("vendor"),
            "product": payload.get("product"),
            "recommended_transport": payload.get("recommended_transport"),
            "first_transport": {
                "transport": first_transport.get("transport"),
                "default_port": first_transport.get("default_port"),
                "payload_format": first_transport.get("payload_format"),
            } if isinstance(first_transport, dict) else None,
            "event_family_count": len(payload.get("event_families") or []),
            "test_event_set_count": len(payload.get("test_event_sets") or []),
            "first_test_event_path": first_test_event.get("path") if isinstance(first_test_event, dict) else None,
            "export_artifact_groups": groups,
            "export_artifact_count": len(export_artifacts),
        })
    if kind == "catalogue_detail" and isinstance(payload, dict):
        provenance = cast(dict[str, Any], payload.get("provenance")) if isinstance(payload.get("provenance"), dict) else {}
        validation = cast(dict[str, Any], payload.get("validation")) if isinstance(payload.get("validation"), dict) else {}
        field_contract = cast(dict[str, Any], payload.get("field_contract")) if isinstance(payload.get("field_contract"), dict) else {}
        comparison = cast(dict[str, Any], payload.get("comparison_to_upstream")) if isinstance(payload.get("comparison_to_upstream"), dict) else {}
        return sanitize_payload({
            "id": payload.get("id"),
            "display_name": payload.get("display_name"),
            "vendor": payload.get("vendor"),
            "product": payload.get("product"),
            "effective_origin": payload.get("effective_origin"),
            "source_status": payload.get("source_status"),
            "quality_status": payload.get("quality_status"),
            "candidate_warning_count": len(payload.get("candidate_warnings") or []),
            "provenance_url": payload.get("provenance_url") or provenance.get("url"),
            "provenance_kind": provenance.get("source_kind"),
            "validation_state": validation.get("state"),
            "validation_evidence_count": len(validation.get("evidence_paths") or []),
            "field_contract_mapping_status": field_contract.get("mapping_status"),
            "relationship": comparison.get("relationship") or payload.get("relationship_to_upstream"),
            "event_family_delta_count": len(comparison.get("event_family_delta") or []),
            "field_extraction_delta_count": len(comparison.get("field_extraction_delta") or []),
            "preset_count": len(payload.get("presets") or []),
            "known_limitations_count": len(payload.get("known_limitations") or []),
        })
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {"kind": kind, "sha256": digest}


def group_summary(groups: str) -> dict[str, Any]:
    items = [item.strip() for item in re.split(r"[,;|]", groups or "") if item.strip()]
    return {"count": len(items), "sample": items[:3]}


def build_journey_matrix(public_payload: dict[str, Any], auth_payload: dict[str, Any], captured_at: str) -> dict[str, Any]:
    routes = {entry.get("route"): entry for entry in auth_payload.get("route_inventory", []) if isinstance(entry, dict)}
    route_keys = [str(route) for route in routes if route]
    checks = auth_payload.get("checks", {}) if isinstance(auth_payload.get("checks"), dict) else {}
    public_checks = {entry.get("name"): entry for entry in public_payload.get("results", []) if isinstance(entry, dict)}
    library_entry = routes.get("/library") if isinstance(routes.get("/library"), dict) else {}
    unauthenticated_redirect = cast(dict[str, Any], checks.get("unauthenticated_api_stats_redirect")) if isinstance(checks.get("unauthenticated_api_stats_redirect"), dict) else {}

    def route_entry(route: str) -> dict[str, Any]:
        entry = routes.get(route)
        return entry if isinstance(entry, dict) else {}

    def route_status(route: str) -> str:
        entry = route_entry(route)
        if not entry:
            return "missing"
        if entry.get("status") == 200 and entry.get("api_status") == 200 and entry.get("artifact_path") and entry.get("api_summary"):
            return "covered"
        if entry.get("status") == 200 and entry.get("artifact_path"):
            return "partial"
        return "failed"

    def evidence_for(*route_names: str) -> list[str]:
        artifacts: list[str] = []
        for route in route_names:
            entry = routes.get(route)
            if isinstance(entry, dict) and entry.get("artifact_path"):
                artifacts.append(str(entry["artifact_path"]))
        return artifacts

    journeys = [
        {
            "id": "J01-public-protection",
            "persona": "Unauthenticated visitor",
            "goal": "Confirm the private Manager is not usable from the public edge without identity.",
            "ui_routes": ["/", "/health", "/api/stats"],
            "api_readback": ["public_root", "public_health", "public_api_stats"],
            "expected_evidence": "Public checks return 302/303 to Authentik or 403 edge denial; this is not counted as authenticated UI proof.",
            "status": "covered" if public_checks and all((item.get("status") in {302, 303, 403}) for item in public_checks.values()) else "failed",
            "artifact_paths": [repo_relative(DEFAULT_PUBLIC_OUTPUT)],
            "test_names": [
                "tests/test_acceptance_evidence.py::test_browser_validator_rejects_redirect_only_authenticated_claim",
                "tests/test_browser_route_acceptance.py::test_build_journey_matrix_maps_user_journeys_to_route_and_api_evidence",
            ],
        },
        {
            "id": "J02-dashboard-operator-landing",
            "persona": "SC4S operator",
            "goal": "Land on the Dashboard and see control-plane health/runtime context plus navigation to the main work areas.",
            "ui_routes": ["/"],
            "api_readback": ["/api/stats"],
            "expected_evidence": "Dashboard route shell loads from the authenticated/internal path and /api/stats readback is present; component tests separately prove the nav includes Catalogue/Packs/Exports/Library.",
            "status": "partial" if route_status("/") == "covered" else route_status("/"),
            "artifact_paths": evidence_for("/"),
            "test_names": [
                "frontend/src/components/AppLayout.test.tsx",
                "frontend/src/routes/UserJourneyCoverage.test.tsx",
            ],
        },
        {
            "id": "J03-source-catalogue-browse-detail",
            "persona": "SC4S content reviewer",
            "goal": "Browse Source Catalogue and open a detail page with provenance, validation status, CIM/common honesty, and candidate labels.",
            "ui_routes": ["/catalogue", next((route for route in route_keys if route.startswith("/catalogue/")), "/catalogue/<first-entry>")],
            "api_readback": ["/api/catalogue", "/api/catalogue/<first-entry>"],
            "expected_evidence": "Catalogue list and first detail route both have API readback artifacts; status language remains evidence-based.",
            "status": "covered" if route_status("/catalogue") == "covered" and any(route_status(route) == "covered" for route in route_keys if route.startswith("/catalogue/")) else "partial",
            "artifact_paths": evidence_for("/catalogue", *[route for route in route_keys if route.startswith("/catalogue/")]),
            "test_names": [
                "frontend/src/routes/CatalogueList.test.tsx",
                "frontend/src/routes/CatalogueDetail.test.tsx",
            ],
        },
        {
            "id": "J04-pack-detail-inspection",
            "persona": "SC4S implementer",
            "goal": "Inspect Packs and a pack detail without confusing source/pack data with applied live state.",
            "ui_routes": ["/packs", next((route for route in route_keys if route.startswith("/packs/")), "/packs/<first-pack>")],
            "api_readback": ["/api/packs", "/api/packs/<first-pack>"],
            "expected_evidence": "Pack list and first detail route have API readback artifacts containing parser/source/test-event context summary.",
            "status": "covered" if route_status("/packs") == "covered" and any(route_status(route) == "covered" for route in route_keys if route.startswith("/packs/")) else "partial",
            "artifact_paths": evidence_for("/packs", *[route for route in route_keys if route.startswith("/packs/")]),
            "test_names": [
                "frontend/src/routes/UserJourneyCoverage.test.tsx",
            ],
        },
        {
            "id": "J05-library-import-validate-apply-separation",
            "persona": "SC4S operator importing Library content",
            "goal": "Use SecHub Resources while preserving source refresh, checksum/manifest validation, import record, and explicit validate/apply separation.",
            "ui_routes": ["/library"],
            "api_readback": ["/api/library/catalogue?source_id=official"],
            "expected_evidence": "Library route is present, has API readback or explicit fallback reason, and does not promote community candidates or silently apply artifacts.",
            "status": "partial" if library_entry.get("api_fallback_reason") or route_status("/library") == "covered" else route_status("/library"),
            "artifact_paths": evidence_for("/library"),
            "test_names": [
                "frontend/src/components/AppLayout.test.tsx",
                "frontend/src/routes/Library.test.tsx",
            ],
        },
        {
            "id": "J06-export-validation-evidence",
            "persona": "SC4S operator preparing handoff evidence",
            "goal": "Reach Exports/validation evidence and confirm exported/pack evidence is visible without claiming skipped runtime proof passed.",
            "ui_routes": ["/exports"],
            "api_readback": ["/api/packs"],
            "expected_evidence": "Exports route loads with pack API readback; final release validation remains separately gated by runtime/Splunk proof.",
            "status": route_status("/exports"),
            "artifact_paths": evidence_for("/exports"),
            "test_names": [
                "frontend/src/routes/UserJourneyCoverage.test.tsx",
            ],
        },
        {
            "id": "J07-negative-auth-and-mutation-safety",
            "persona": "Security reviewer",
            "goal": "Ensure unauthenticated API redirect/denial is not misreported as authenticated UI success and that evidence capture does not execute dangerous mutations.",
            "ui_routes": ["/api/stats", "read-only route capture"],
            "api_readback": ["unauthenticated_api_stats_redirect", "authenticated route GETs only"],
            "expected_evidence": "Unauthenticated API status is 302/303/403; authenticated route artifacts come from internal/trusted path; mutation/apply/restart endpoints are not invoked.",
            "status": "covered" if unauthenticated_redirect.get("status") in {302, 303, 403} else "failed",
            "artifact_paths": [repo_relative(DEFAULT_PUBLIC_OUTPUT), repo_relative(DEFAULT_AUTH_OUTPUT)],
            "test_names": [
                "tests/test_acceptance_evidence.py::test_browser_validator_rejects_redirect_only_authenticated_claim",
                "python3 scripts/validate_acceptance_evidence.py --require-e2e-ui",
            ],
        },
    ]
    return sanitize_payload({
        "captured_at_utc": captured_at,
        "scope": "SC4S Manager protected-route split: public denial proof plus authenticated/internal UI+API readback evidence.",
        "public_url": public_payload.get("public_url"),
        "authenticated_base_url": auth_payload.get("authenticated_base_url"),
        "artifact_dir": auth_payload.get("artifact_dir"),
        "auth_mode": auth_payload.get("auth_mode"),
        "auth_source": auth_payload.get("auth_source"),
        "limitations": [
            "A full browser SSO login flow is not required for this proof; public Authentik/edge protection is proved separately from authenticated/internal route evidence.",
            "The runner captures GET route shells and API readback only; it deliberately does not execute apply/restart/mutation actions.",
        ],
        "journeys": journeys,
    })


def render_journey_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# E2E UI user-journey validation",
        "",
        f"Captured: `{payload.get('captured_at_utc')}`",
        "",
        "This evidence uses the protected-route split pattern: public unauthenticated protection is proved separately, then authenticated/internal Manager UI routes are paired with API readback artifacts. Authentik redirects are not counted as authenticated UI success.",
        "",
        "## Current run",
        "",
        f"- Public URL: `{payload.get('public_url')}`",
        f"- Authenticated/internal base: `{payload.get('authenticated_base_url')}`",
        f"- Artifact directory: `{payload.get('artifact_dir')}`",
        f"- Auth mode/source: `{payload.get('auth_mode')}` / `{payload.get('auth_source')}`",
        "",
        "## Journey matrix",
        "",
    ]
    for journey in payload.get("journeys", []):
        lines.extend([
            f"### {journey.get('id')} — {journey.get('persona')}",
            "",
            f"- Goal: {journey.get('goal')}",
            f"- UI routes: {', '.join(journey.get('ui_routes') or [])}",
            f"- API/readback: {', '.join(journey.get('api_readback') or [])}",
            f"- Expected evidence: {journey.get('expected_evidence')}",
            f"- Current status: **{journey.get('status')}**",
            "- Artifacts:",
        ])
        for artifact in journey.get("artifact_paths") or ["None captured"]:
            lines.append(f"  - `{artifact}`")
        lines.append("- Test names:")
        for test_name in journey.get("test_names") or ["None recorded"]:
            lines.append(f"  - `{test_name}`")
        lines.append("")
    lines.extend([
        "## Limitations and safety",
        "",
    ])
    for item in payload.get("limitations") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Runnable command:")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 scripts/validate_e2e_ui_user_journeys.py --auth-mode auto --internal-base-url http://127.0.0.1:18090")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = BrowserRouteRunner(args).run()
    except AcceptanceError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
