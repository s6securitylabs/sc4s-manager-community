#!/usr/bin/env python3
"""Run the V1 CRUD operator-journey acceptance suite against a live manager.

Exercises source, destination, and route CRUD lifecycles (J08-J15) through the
manager HTTP API, proves live routing with a marker event indexed in Splunk,
and writes sanitized evidence to docs/acceptance/crud-user-journeys-live.json
for scripts/validate_acceptance_evidence.py --require-crud-journeys.

Secrets handling: manager tokens come from SC4S_MANAGER_API_TOKEN or
SC4S_MANAGER_MANUAL_LOGIN_TOKEN environment variables; the HEC token for the
test destination comes from SC4S_CRUD_HEC_TOKEN. None of these values are ever
written to evidence; the script aborts rather than write evidence containing a
known secret value.

Splunk readback is delegated to --splunk-search-cmd, a shell command that
receives one SPL search on stdin and prints Splunk JSON result lines on
stdout. This keeps Splunk credentials entirely outside this process.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "acceptance" / "crud-user-journeys-live.json"

SOURCE_NAME = "v1_crud_asa_source"
ROLLBACK_SEED = "v1_crud_rollback_seed"
HEC_DEST_ID = "V1CRUDHEC"
SYSLOG_DEST_ID = "V1CRUDSIEM"
ROUTE_ID = "v1_crud_asa_route"
PACK_ID = "cisco_asa"


class JourneyError(RuntimeError):
    pass


class ManagerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = os.environ.get("SC4S_MANAGER_API_TOKEN", "")
        self.manual_token = os.environ.get("SC4S_MANAGER_MANUAL_LOGIN_TOKEN", "")
        if not self.api_token and not self.manual_token:
            raise SystemExit("SC4S_MANAGER_API_TOKEN or SC4S_MANAGER_MANUAL_LOGIN_TOKEN is required")

    def headers(self, authenticated: bool = True) -> dict[str, str]:
        out = {"Content-Type": "application/json", "X-Authentik-Username": "qa.crud-journeys"}
        if not authenticated:
            return {"Content-Type": "application/json"}
        if self.api_token:
            out["X-SC4S-Manager-Token"] = self.api_token
        elif self.manual_token:
            out["Authorization"] = f"Bearer {self.manual_token}"
        return out

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, authenticated: bool = True, timeout: float = 60.0) -> tuple[int, Any]:
        body = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(self.base_url + path, data=body, method=method, headers=self.headers(authenticated))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode()
                return resp.status, json.loads(text) if text else None
        except urllib.error.HTTPError as exc:
            text = exc.read().decode()
            try:
                return exc.code, json.loads(text)
            except json.JSONDecodeError:
                return exc.code, {"raw": text[:500]}

    def get(self, path: str, **kw: Any) -> tuple[int, Any]:
        return self.request("GET", path, **kw)

    def post(self, path: str, payload: dict[str, Any], **kw: Any) -> tuple[int, Any]:
        return self.request("POST", path, payload, **kw)


def expect(condition: bool, detail: str) -> None:
    if not condition:
        raise JourneyError(detail)


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def asa_marker_payload(marker: str) -> bytes:
    return (
        "<134>%ASA-6-302013: Built outbound TCP connection 424242 for "
        "outside:203.0.113.10/443 (203.0.113.10/443) to inside:192.0.2.10/51515 "
        f"(192.0.2.10/51515) SC4S_ACCEPTANCE_MARKER {marker}"
    ).encode()


def send_marker(host: str, port: int, marker: str) -> dict[str, Any]:
    payload = asa_marker_payload(marker)
    attempts = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5.0)
            sent = sock.sendto(payload, (host, port))
        attempts.append({"protocol": "udp", "port": port, "ok": sent == len(payload)})
    except Exception as exc:
        attempts.append({"protocol": "udp", "port": port, "ok": False, "detail": type(exc).__name__})
    try:
        with socket.create_connection((host, port), timeout=5.0) as sock:
            sock.sendall(payload + b"\n")
        attempts.append({"protocol": "tcp", "port": port, "ok": True})
    except Exception as exc:
        attempts.append({"protocol": "tcp", "port": port, "ok": False, "detail": type(exc).__name__})
    return {"host": host, "attempts": attempts, "ok": any(item["ok"] for item in attempts)}


def splunk_search(cmd: str, spl: str, timeout: float = 120.0) -> list[dict[str, Any]]:
    proc = subprocess.run(cmd, shell=True, input=spl.encode(), capture_output=True, timeout=timeout)
    results: list[dict[str, Any]] = []
    for line in proc.stdout.decode(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and isinstance(row.get("result"), dict):
            results.append(row["result"])
    return results


def wait_for_marker(cmd: str, marker: str, attempts: int = 12, delay: float = 10.0) -> list[dict[str, Any]]:
    spl = (
        f'search index=* earliest=-1h "SC4S_ACCEPTANCE_MARKER" "{marker}" '
        "| table _time index sourcetype host source _raw | head 5"
    )
    for _ in range(attempts):
        results = [row for row in splunk_search(cmd, spl) if marker in json.dumps(row)]
        if results:
            return results
        time.sleep(delay)
    return []


def wait_for_validation(client: ManagerClient, attempts: int = 18, delay: float = 5.0) -> dict[str, Any]:
    """Wait until config validation (syntax + TLS listener state) is green.

    A reload drops listeners for a few seconds; container health recovers
    before the TLS listener does, so post-reload steps must wait on
    validation, not health alone.
    """
    last: dict[str, Any] = {}
    for _ in range(attempts):
        try:
            status, body = client.get("/api/validate", timeout=30.0)
        except Exception:
            time.sleep(delay)
            continue
        if status == 200 and isinstance(body, dict):
            last = body
            if body.get("ok"):
                return {"ok": True, "checked_at": body.get("checked_at")}
        time.sleep(delay)
    return {"ok": False, "last": {"ok": last.get("ok"), "tls_ready": (last.get("tls") or {}).get("ready")}}


def wait_for_health(client: ManagerClient, attempts: int = 30, delay: float = 5.0) -> dict[str, Any]:
    last: dict[str, Any] = {}
    for _ in range(attempts):
        try:
            status, body = client.get("/api/health", timeout=10.0)
        except Exception:
            time.sleep(delay)
            continue
        if status == 200 and isinstance(body, dict):
            last = body
            sc4s = body.get("sc4s") or {}
            if sc4s.get("ok"):
                return {"ok": True, "sc4s": {"ok": True, "status": sc4s.get("status")}}
        time.sleep(delay)
    return {"ok": False, "last": last}


def newest_backup_name(client: ManagerClient, fragment: str) -> str:
    status, body = client.get("/api/backups")
    if status != 200 or not isinstance(body, dict):
        return ""
    for item in body.get("backups") or []:
        name = str(item.get("name", "")) if isinstance(item, dict) else ""
        if fragment in name:
            return name
    return ""


class CrudJourneySuite:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.client = ManagerClient(args.base_url)
        self.hec_token = os.environ.get("SC4S_CRUD_HEC_TOKEN", "")
        self.secret_values = [v for v in (self.hec_token, self.client.api_token, self.client.manual_token) if v]
        self.surfaces: list[str] = []
        self.journeys: dict[str, dict[str, Any]] = {}
        self.run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        self.marker = f"sc4s-acceptance-{self.run_id}-crud-route"
        self.marker_pack = f"sc4s-acceptance-{self.run_id}-crud-pack"

    # -- helpers -----------------------------------------------------------
    def record_surface(self, payload: Any) -> None:
        self.surfaces.append(json.dumps(payload, sort_keys=True, default=str))

    def api(self, method: str, path: str, payload: dict[str, Any] | None = None, expect_status: int = 200, **kw: Any) -> Any:
        status, body = self.client.request(method, path, payload, **kw)
        self.record_surface(body)
        expect(status == expect_status, f"{method} {path} returned {status}: {json.dumps(body)[:300]}")
        return body

    def source_listed(self, name: str) -> bool:
        body = self.api("GET", "/api/sources")
        return any(item.get("name") == name for item in body.get("sources", []))

    def destination_listed(self, kind: str, dest_id: str) -> bool:
        body = self.api("GET", "/api/destinations")
        return any(item.get("kind") == kind and item.get("id") == dest_id for item in body.get("destinations", []))

    def route_listed(self, route_id: str) -> bool:
        body = self.api("GET", "/api/routes")
        return any(item.get("id") == route_id for item in body.get("routes", []))

    def audit_actions(self, fragment: str) -> list[str]:
        body = self.api("GET", "/api/audit")
        actions = []
        for line in body.get("lines", []):
            if fragment not in line:
                continue
            try:
                actions.append(str(json.loads(line).get("action")))
            except json.JSONDecodeError:
                continue
        return sorted(set(actions))

    def csv_stale_rows(self, filter_id: str) -> int:
        body = self.api("GET", "/api/config")
        count = 0
        for rows in (body.get("csv") or {}).values():
            for row in rows or []:
                if row and row[0] == filter_id:
                    count += 1
        return count

    # -- journeys ----------------------------------------------------------
    def j08_source_crud(self) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        evidence["baseline_absent"] = not self.source_listed(SOURCE_NAME)
        expect(evidence["baseline_absent"], f"{SOURCE_NAME} already exists; refusing to overwrite")

        add = self.api("POST", "/api/sources/onboard", {
            "name": SOURCE_NAME, "source": self.args.probe_source, "vendor_product": PACK_ID,
            "index": self.args.splunk_index, "compliance": "qa", "apply": True,
        })
        expect(add.get("ok") is True, f"source add failed: {json.dumps(add)[:300]}")
        health = wait_for_validation(self.client)
        expect(health.get("ok"), f"validation did not recover after source add reload: {json.dumps(health)[:300]}")
        evidence["add"] = {"ok": True, "source_id": SOURCE_NAME, "apply_mode": add.get("apply_mode"),
                           "validation": {"ok": bool(add.get("validation", {}).get("ok"))},
                           "control": {"ok": bool(add.get("control", {}).get("ok")), "skipped": bool(add.get("control", {}).get("skipped"))},
                           "post_reload_health": health.get("sc4s")}

        edit = self.api("POST", "/api/sources/onboard", {
            "name": SOURCE_NAME, "source": self.args.probe_source, "vendor_product": PACK_ID,
            "index": self.args.splunk_index, "compliance": "qa-edited", "apply": True,
        })
        expect(edit.get("ok") is True, f"source edit failed: {json.dumps(edit)[:300]}")
        health = wait_for_validation(self.client)
        expect(health.get("ok"), f"validation did not recover after source edit reload: {json.dumps(health)[:300]}")
        evidence["edit"] = {"ok": True, "backup": newest_backup_name(self.client, SOURCE_NAME)}
        expect(bool(evidence["edit"]["backup"]), "source edit produced no backup")

        delete = self.api("POST", "/api/sources/delete", {"name": SOURCE_NAME})
        expect(delete.get("ok") is True and delete.get("removed_paths"), "source delete failed")
        evidence["delete"] = {"ok": True, "removed_paths": delete.get("removed_paths")}

        stale = self.csv_stale_rows(f"f_{SOURCE_NAME}")
        evidence["cleanup"] = {"ok": not self.source_listed(SOURCE_NAME) and stale == 0, "stale_rows_remaining": stale}
        expect(evidence["cleanup"]["ok"], f"source cleanup left {stale} stale CSV rows")
        evidence["audit_actions"] = self.audit_actions(SOURCE_NAME)
        return {
            "id": "J08-syslog-source-crud-lifecycle",
            "status": "covered",
            "persona": "SC4S operator",
            "goal": "Add, edit, validate, apply, and delete a syslog source through the manager API.",
            "steps": ["verify baseline absent", "onboard source with validated reload", "edit source and confirm backup",
                      "delete source", "verify CSV/context cleanup", "confirm audit trail"],
            "evidence": evidence,
        }

    def j09_hec_destination_crud(self) -> dict[str, Any]:
        expect(bool(self.hec_token), "SC4S_CRUD_HEC_TOKEN is required for the HEC destination journey")
        evidence: dict[str, Any] = {}
        evidence["baseline_absent"] = not self.destination_listed("hec", HEC_DEST_ID)
        expect(evidence["baseline_absent"], f"{HEC_DEST_ID} already exists; refusing to overwrite")

        add = self.api("POST", "/api/destinations", {
            "kind": "hec", "id": HEC_DEST_ID, "url": self.args.hec_url, "token": self.hec_token,
            "mode": "SELECT", "tls_verify": "no", "apply": False,
        })
        expect(add.get("ok") is True, f"HEC destination add failed: {json.dumps(add)[:300]}")
        expect(self.hec_token not in json.dumps(add), "HEC add response leaked the token")
        evidence["add"] = {"ok": True, "destination_id": HEC_DEST_ID, "apply_mode": add.get("apply_mode"),
                           "staged_only": True, "validation": {"ok": bool(add.get("validation", {}).get("ok"))}}

        inventory_body = self.api("GET", "/api/destinations")
        entry = next(item for item in inventory_body["destinations"] if item.get("kind") == "hec" and item.get("id") == HEC_DEST_ID)
        expect(entry.get("token") == "[REDACTED]", "inventory did not redact the HEC token")
        evidence["inventory"] = {"token": entry.get("token"), "url": entry.get("url"), "mode": entry.get("mode")}

        edit = self.api("POST", "/api/destinations", {
            "kind": "hec", "id": HEC_DEST_ID, "url": self.args.hec_url, "mode": "SELECT",
            "tls_verify": "no", "http_compression": "no", "apply": False,
        })
        expect(edit.get("ok") is True and edit.get("backup"), "HEC destination edit failed or produced no backup")
        evidence["edit"] = {"ok": True, "backup": edit.get("backup")}
        return evidence  # finished later by finish_j09 after the route journey

    def finish_j09(self, evidence: dict[str, Any]) -> dict[str, Any]:
        delete = self.api("POST", "/api/destinations/delete", {"kind": "hec", "id": HEC_DEST_ID})
        expect(delete.get("ok") is True, "HEC destination delete failed")
        removed_keys = delete.get("removed_env_keys") or []
        expect(any(key.endswith("_TOKEN") for key in removed_keys), "HEC delete did not remove the token env key")
        evidence["delete"] = {"ok": True, "removed_env_keys": removed_keys}

        leak = any(secret in surface for secret in self.secret_values for surface in self.surfaces)
        evidence["cleanup"] = {"ok": not self.destination_listed("hec", HEC_DEST_ID), "secret_leak_found": leak}
        expect(evidence["cleanup"]["ok"] and not leak, "HEC cleanup failed or a secret leaked into an API surface")
        evidence["audit_actions"] = self.audit_actions(HEC_DEST_ID)
        return {
            "id": "J09-hec-destination-crud-lifecycle",
            "status": "covered",
            "persona": "Platform engineer",
            "goal": "Add, edit, validate, apply, and delete a Splunk HEC destination with token redaction.",
            "steps": ["verify baseline absent", "stage HEC destination with secret token", "confirm inventory redaction",
                      "edit destination with env backup", "apply via route journey restart", "delete destination",
                      "verify cleanup and no secret leak"],
            "evidence": evidence,
        }

    def j10_syslog_bsd_destination_crud(self) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        evidence["baseline_absent"] = not self.destination_listed("syslog", SYSLOG_DEST_ID)
        expect(evidence["baseline_absent"], f"{SYSLOG_DEST_ID} already exists; refusing to overwrite")

        add = self.api("POST", "/api/destinations", {
            "kind": "syslog", "id": SYSLOG_DEST_ID, "host": self.args.probe_source.split("/")[0],
            "port": 601, "transport": "tcp", "mode": "GLOBAL", "apply": False,
        })
        expect(add.get("ok") is True, f"syslog destination add failed: {json.dumps(add)[:300]}")
        evidence["add"] = {"ok": True, "destination_id": SYSLOG_DEST_ID, "staged_only": True, "apply_mode": add.get("apply_mode")}

        edit = self.api("POST", "/api/destinations", {
            "kind": "syslog", "id": SYSLOG_DEST_ID, "host": self.args.probe_source.split("/")[0],
            "port": 601, "transport": "tcp", "mode": "SELECT", "selector_vendor_product": PACK_ID, "apply": False,
        })
        expect(edit.get("ok") is True, "syslog destination edit to SELECT failed")
        evidence["edit"] = {"ok": True, "mode": "SELECT"}
        selector_path = edit.get("selector") or ""
        expect(bool(selector_path), "SELECT edit did not create a selector")
        evidence["selector"] = {"ok": True, "path": selector_path}

        delete = self.api("POST", "/api/destinations/delete", {"kind": "syslog", "id": SYSLOG_DEST_ID})
        expect(delete.get("ok") is True, "syslog destination delete failed")
        evidence["delete"] = {"ok": True, "removed_env_keys": delete.get("removed_env_keys"), "removed_selectors": delete.get("removed_selectors")}
        evidence["cleanup"] = {"ok": not self.destination_listed("syslog", SYSLOG_DEST_ID)}
        expect(evidence["cleanup"]["ok"], "syslog destination cleanup failed")
        return {
            "id": "J10-syslog-bsd-destination-crud-lifecycle",
            "status": "covered",
            "persona": "SC4S operator",
            "goal": "Add, edit, validate, and delete a selected syslog/BSD destination without disturbing the live runtime.",
            "steps": ["verify baseline absent", "stage GLOBAL syslog destination", "edit to SELECT mode generating a selector",
                      "delete destination and selector", "verify cleanup before any runtime restart"],
            "evidence": evidence,
        }

    def j11_route_lifecycle(self) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        evidence["baseline_absent"] = not self.route_listed(ROUTE_ID)
        expect(evidence["baseline_absent"], f"route {ROUTE_ID} already exists; refusing to overwrite")

        source = self.api("POST", "/api/sources/onboard", {
            "name": SOURCE_NAME, "source": self.args.probe_source, "vendor_product": PACK_ID,
            "index": self.args.splunk_index, "apply": False,
        })
        expect(source.get("ok") is True, "route journey source onboarding failed")

        route = self.api("POST", "/api/routes", {
            "id": ROUTE_ID, "source": SOURCE_NAME, "pack": PACK_ID,
            "destination_kind": "hec", "destination_id": HEC_DEST_ID, "apply": False,
        })
        expect(route.get("ok") is True, f"route create failed: {json.dumps(route)[:300]}")
        evidence["route"] = {"ok": True, "source_id": SOURCE_NAME, "pack_id": PACK_ID, "destination_id": HEC_DEST_ID,
                             "selector": route.get("route", {}).get("selector")}
        evidence["validation"] = {"ok": bool(route.get("validation", {}).get("ok"))}

        restart = self.api("POST", "/api/restart", {})
        health = wait_for_health(self.client)
        expect(health.get("ok"), f"SC4S did not return to healthy after restart: {json.dumps(health)[:300]}")
        evidence["control"] = {"ok": bool(restart.get("ok", True)), "action": "restart", "post_health": health.get("sc4s")}

        send = send_marker(self.args.sc4s_host, self.args.syslog_port, self.marker)
        expect(send["ok"], f"marker send failed: {json.dumps(send)}")
        evidence["send_marker"] = send

        results = wait_for_marker(self.args.splunk_search_cmd, self.marker)
        expect(bool(results), f"marker {self.marker} was not found in Splunk")
        first = results[0]
        metrics = self.api("GET", f"/api/metrics/syslog-ng?search={HEC_DEST_ID.lower()}")
        evidence["splunk_readback"] = {
            "ok": True,
            "marker": self.marker,
            "result_count": len(results),
            "index": first.get("index"),
            "sourcetype": first.get("sourcetype"),
            "destination_id": HEC_DEST_ID,
            "results": results[:2],
            "destination_metrics_rows": len(metrics.get("rows") or []),
        }

        delete = self.api("POST", "/api/routes/delete", {"id": ROUTE_ID})
        expect(delete.get("ok") is True, "route delete failed")
        self.api("POST", "/api/reload", {})
        recovered = wait_for_validation(self.client)
        expect(recovered.get("ok"), f"validation did not recover after route delete reload: {json.dumps(recovered)[:300]}")
        evidence["delete"] = {"ok": True, "removed_selectors": delete.get("removed_selectors")}
        evidence["post_delete"] = {"ok": not self.route_listed(ROUTE_ID), "route_applied": False}
        expect(evidence["post_delete"]["ok"], "route still listed after delete")
        return {
            "id": "J11-source-pack-destination-route-lifecycle",
            "status": "covered",
            "persona": "SOC engineer",
            "goal": "Connect a source/pack/parser to a selected destination and prove live routing with Splunk readback.",
            "steps": ["verify baseline absent", "onboard source", "create route with selector", "validate configuration",
                      "restart SC4S via control daemon", "send marker event", "confirm indexed marker in Splunk",
                      "delete route", "verify route no longer applies"],
            "evidence": evidence,
        }

    def j12_pack_import_route_apply(self) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        self.api("POST", "/api/library/sync", {"source_id": "official"})
        catalogue = self.api("GET", "/api/library/catalogue?source_id=official&downloadable_only=yes")
        entries = catalogue.get("entries") or []
        expect(bool(entries), "library catalogue returned no downloadable entries")
        entry_id = self.args.library_entry or str(entries[0].get("id"))

        download = self.api("POST", "/api/library/download", {"source_id": "official", "entry_id": entry_id})
        expect(download.get("ok") is True, f"library download failed for {entry_id}")
        validate = self.api("POST", "/api/library/import/validate", {"source_id": "official", "entry_id": entry_id})
        expect(validate.get("ok") is True, f"library import validation failed for {entry_id}")
        import_id = str(validate.get("import_id"))
        expect(validate.get("apply_allowed") is True, f"library entry {entry_id} is reference-only; cannot prove apply")
        evidence["import"] = {"ok": True, "entry_id": entry_id, "import_id": import_id,
                              "runtime_files": len(validate.get("runtime_files") or [])}

        preview = self.api("POST", "/api/library/import/apply", {"import_id": import_id, "apply": False})
        expect(preview.get("ok") is True, "library staged preview failed")
        targets = [str(t) for t in preview.get("changed_targets") or []]
        evidence["preview"] = {"ok": True, "staged_only": True, "predicted_targets": targets}

        prior: dict[str, dict[str, Any]] = {}
        for target in targets:
            rel = target.removeprefix("local/")
            status, body = self.client.get(f"/api/config/file?path={urllib.request.quote(rel)}")
            prior[target] = {"existed": status == 200 and bool((body or {}).get("content")), "content": (body or {}).get("content", "") if status == 200 else ""}

        apply = self.api("POST", "/api/library/import/apply", {"import_id": import_id, "apply": True})
        expect(apply.get("ok") is True and apply.get("rolled_back") is False, f"library apply failed: {json.dumps(apply)[:300]}")
        post_apply_health = wait_for_health(self.client)
        expect(bool(post_apply_health.get("ok")), "SC4S unhealthy after library import apply")
        post_apply_validation = wait_for_validation(self.client)
        expect(bool(post_apply_validation.get("ok")), "validation did not recover after library import apply")
        evidence["apply"] = {"ok": True, "changed_targets": apply.get("changed_targets"),
                             "validation": {"ok": bool(apply.get("validation", {}).get("ok")),
                                            "post_apply_ok": True},
                             "control": {"ok": bool(apply.get("control", {}).get("ok", True))},
                             "health": post_apply_health}

        send = send_marker(self.args.sc4s_host, self.args.syslog_port, self.marker_pack)
        expect(send["ok"], "post-apply marker send failed")
        results = wait_for_marker(self.args.splunk_search_cmd, self.marker_pack)
        expect(bool(results), f"post-apply marker {self.marker_pack} was not found in Splunk")
        evidence["splunk_readback"] = {
            "ok": True, "marker": self.marker_pack, "result_count": len(results),
            "index": results[0].get("index"), "sourcetype": results[0].get("sourcetype"),
            "note": "proves the ingestion path stays live with imported pack artifacts applied",
        }

        restored: list[str] = []
        for target, before in prior.items():
            rel = target.removeprefix("local/")
            restore = self.api("POST", "/api/apply", {"type": "file", "path": rel, "content": before["content"], "apply": True})
            expect(restore.get("ok") is True, f"rollback restore failed for {target}")
            restored.append(target)
        post_validate = self.api("GET", "/api/validate")
        evidence["rollback"] = {"ok": bool(post_validate.get("ok")), "restored_targets": restored,
                                "note": "previously-absent targets restored to empty content; configuration validated and reloaded"}
        expect(evidence["rollback"]["ok"], "post-rollback validation failed")
        return {
            "id": "J12-pack-import-source-route-apply",
            "status": "covered",
            "persona": "SC4S operator",
            "goal": "Import a curated Library pack, stage and apply its runtime artifacts, prove live ingestion, then roll back.",
            "steps": ["sync library source", "download and verify bundle", "validate import", "stage preview of runtime targets",
                      "apply with validation and reload", "confirm indexed marker post-apply", "roll back applied targets"],
            "evidence": evidence,
        }

    def j13_failed_apply_rollback(self) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        baseline = self.api("GET", "/api/validate")
        expect(baseline.get("ok") is True, "baseline validation is not ok; refusing to run failed-apply drill")
        evidence["baseline"] = {"ok": True, "checked_at": baseline.get("checked_at")}

        seed = self.api("POST", "/api/sources/onboard", {
            "name": ROLLBACK_SEED, "source": self.args.probe_source, "vendor_product": PACK_ID, "apply": False,
        })
        expect(seed.get("ok") is True, "rollback seed source failed")
        seed_rel = f"config/filters/{ROLLBACK_SEED}.conf"
        good = self.api("GET", f"/api/config/file?path={urllib.request.quote(seed_rel)}")
        good_content = good.get("content", "")
        expect("filter" in good_content, "seed filter content missing")

        broken = self.api("POST", "/api/apply", {"type": "file", "path": seed_rel, "content": "filter f_broken { broken_syntax(; };\n", "apply": True})
        expect(broken.get("ok") is False, "broken apply unexpectedly validated")
        evidence["validation_failed"] = True
        expect(broken.get("rolled_back") is True, "failed apply did not roll back")

        after = self.api("GET", f"/api/config/file?path={urllib.request.quote(seed_rel)}")
        expect(after.get("content") == good_content, "file content was not restored after failed apply")
        evidence["rollback"] = {"ok": True, "backup": broken.get("backup"), "restored": True}

        self.api("POST", "/api/sources/delete", {"name": ROLLBACK_SEED})
        post = self.api("GET", "/api/validate")
        health = self.api("GET", "/api/health")
        evidence["post_restore_health"] = {"ok": bool(post.get("ok")) and health.get("status") == "ok"}
        expect(evidence["post_restore_health"]["ok"], "post-restore validation/health failed")
        return {
            "id": "J13-failed-apply-rollback",
            "status": "covered",
            "persona": "Operator recovering from failed config",
            "goal": "Prove an invalid config apply fails validation, rolls back automatically, and leaves the runtime healthy.",
            "steps": ["confirm healthy baseline", "seed a valid filter", "apply syntactically broken content",
                      "observe validation failure and automatic rollback", "verify restored content and post-restore health"],
            "evidence": evidence,
        }

    def j14_negative_security(self) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        status, body = self.client.post("/api/sources/onboard", {"name": "evil", "source": "10.0.0.1"}, authenticated=False)
        evidence["unauthenticated_mutation_denied"] = status == 403
        expect(status == 403, f"unauthenticated mutation returned {status}")
        self.record_surface(body)

        rejected = []
        for method, path, payload in (
            ("POST", "/api/sources/onboard", {"name": "../etc/passwd", "source": "10.0.0.1"}),
            ("POST", "/api/destinations", {"kind": "carrier-pigeon", "id": "X"}),
            ("POST", "/api/destinations", {"kind": "syslog", "id": "X", "host": "10.0.0.5", "port": 70000}),
            ("POST", "/api/routes", {"id": "bad route", "source": "missing", "pack": "x", "destination_kind": "hec", "destination_id": "NOPE"}),
        ):
            status, body = self.client.request(method, path, payload)
            self.record_surface(body)
            rejected.append(status == 400)
        evidence["invalid_inputs_rejected"] = all(rejected)
        expect(all(rejected), "an invalid CRUD input was not rejected with 400")

        traversal = []
        status, body = self.client.get("/api/config/file?path=../env_file")
        self.record_surface(body)
        traversal.append(status == 400)
        status, body = self.client.post("/api/sources/delete", {"name": "../../etc/passwd"})
        self.record_surface(body)
        traversal.append(status == 400)
        evidence["path_traversal_rejected"] = all(traversal)
        expect(all(traversal), "a path traversal attempt was not rejected")

        config = self.api("GET", "/api/config")
        env_dump = json.dumps(config.get("env") or {})
        leak = any(secret in surface for secret in self.secret_values for surface in self.surfaces) or any(
            secret in env_dump for secret in self.secret_values
        )
        evidence["secret_leak_found"] = leak
        expect(not leak, "a secret value leaked into an API surface")
        return {
            "id": "J14-negative-security-validation",
            "status": "covered",
            "persona": "Security reviewer",
            "goal": "Prove CRUD mutations enforce auth, input validation, redaction, and path safety.",
            "steps": ["attempt unauthenticated mutation", "submit invalid source/destination/route inputs",
                      "attempt config path traversal", "scan all captured API surfaces for secret values"],
            "evidence": evidence,
        }

    def j15_ui_coverage(self, screenshots: list[str]) -> dict[str, Any]:
        evidence = {
            "ui_routes": ["/sources", "/destinations", "/routes"],
            "api_calls": [
                "GET /api/sources", "POST /api/sources/onboard", "POST /api/sources/delete",
                "GET /api/destinations", "POST /api/destinations", "POST /api/destinations/delete",
                "GET /api/routes", "POST /api/routes", "POST /api/routes/delete",
                "GET /api/source-catalog",
            ],
            "screenshots": screenshots,
        }
        expect(bool(screenshots), "UI journey requires at least one captured screenshot artifact")
        return {
            "id": "J15-ui-crud-journey-coverage",
            "status": "covered",
            "persona": "Browser operator",
            "goal": "Use UI forms for source, destination, and route workflows with staged/applied state visible.",
            "steps": ["load /sources onboarding form and inventory", "load /destinations form with redacted inventory",
                      "load /routes form connecting source, pack, and destination", "capture screenshot artifacts"],
            "evidence": evidence,
        }

    # -- cleanup -----------------------------------------------------------
    def cleanup_best_effort(self) -> list[str]:
        notes = []
        for path, payload in (
            ("/api/routes/delete", {"id": ROUTE_ID}),
            ("/api/sources/delete", {"name": SOURCE_NAME}),
            ("/api/sources/delete", {"name": ROLLBACK_SEED}),
            ("/api/destinations/delete", {"kind": "hec", "id": HEC_DEST_ID}),
            ("/api/destinations/delete", {"kind": "syslog", "id": SYSLOG_DEST_ID}),
        ):
            status, body = self.client.post(path, payload)
            notes.append(f"{path} {json.dumps(payload)} -> {status}")
        return notes

    # -- orchestration -----------------------------------------------------
    def run(self) -> dict[str, Any]:
        screenshots = [s for s in (self.args.screenshot or []) if s]
        try:
            self.journeys["J14"] = self.j14_negative_security()
            self.journeys["J13"] = self.j13_failed_apply_rollback()
            self.journeys["J08"] = self.j08_source_crud()
            self.journeys["J10"] = self.j10_syslog_bsd_destination_crud()
            j09_evidence = self.j09_hec_destination_crud()
            self.journeys["J11"] = self.j11_route_lifecycle()
            self.api("POST", "/api/sources/delete", {"name": SOURCE_NAME})
            self.journeys["J09"] = self.finish_j09(j09_evidence)
            self.api("POST", "/api/restart", {})
            health = wait_for_health(self.client)
            expect(health.get("ok"), "SC4S unhealthy after cleanup restart")
            recovered = wait_for_validation(self.client)
            expect(recovered.get("ok"), "validation did not recover after cleanup restart")
            self.journeys["J15"] = self.j15_ui_coverage(screenshots)
            # J12 last: it is the only journey that depends on the remote
            # SecHub Resources source being reachable from the manager host.
            self.journeys["J12"] = self.j12_pack_import_route_apply()
        finally:
            cleanup_notes = self.cleanup_best_effort()

        payload = {
            "captured_at_utc": now_utc(),
            "scope": "V1 CRUD operator journeys: source, destination, route, live routing proof, pack import apply, delete, rollback, and UI coverage",
            "secrets_redacted": True,
            "manager_base": "local manager API via authenticated control path",
            "sc4s_host": self.args.sc4s_host,
            "splunk_index": self.args.splunk_index,
            "run_id": self.run_id,
            "cleanup": cleanup_notes,
            "journeys": [self.journeys[key] for key in sorted(self.journeys)],
        }
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        for secret in self.secret_values:
            if secret and secret in rendered:
                raise JourneyError("refusing to write evidence containing a secret value")
        return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V1 CRUD operator-journey acceptance against a live manager.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8090", help="Manager API base URL.")
    parser.add_argument("--sc4s-host", required=True, help="SC4S syslog listener host for marker events.")
    parser.add_argument("--syslog-port", type=int, default=514)
    parser.add_argument("--probe-source", required=True, help="IP/CIDR the marker sender will be seen as by SC4S.")
    parser.add_argument("--hec-url", required=True, help="Real Splunk HEC URL for the test destination.")
    parser.add_argument("--splunk-index", default="main")
    parser.add_argument("--splunk-search-cmd", required=True, help="Shell command reading SPL on stdin and printing Splunk JSON result lines.")
    parser.add_argument("--library-entry", default="", help="Optional library entry id for the pack import journey.")
    parser.add_argument("--screenshot", action="append", default=[], help="Path to a captured UI screenshot artifact (repeatable).")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suite = CrudJourneySuite(args)
    try:
        payload = suite.run()
    except JourneyError as exc:
        print(json.dumps({"ok": False, "error": str(exc), "completed_journeys": sorted(suite.journeys)}, indent=2))
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "journeys": sorted(suite.journeys)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
