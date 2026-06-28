"""Typed runtime state aggregator for SC4S Manager /api/runtime/state.

Pure functions that accept raw control daemon responses and return a stable
typed runtime-state contract. No side effects; testable without a running daemon.
"""
from __future__ import annotations

import csv
import io
import re
from typing import Any

SECRET_KEY_RE = re.compile(r"(TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL|AUTH)", re.I)


def classify_counter_component(source_name: str) -> str:
    n = source_name.lower()
    if n.startswith(("src.", "source.", "s_")):
        return "source"
    if n.startswith(("dst.", "d_", "destination.")):
        return "destination"
    if n.startswith(("parser.", "p_", "filter.", "f_")):
        return "parser"
    return "unknown"


def parse_metrics_to_counters(raw_csv: str) -> list[dict[str, Any]]:
    """Parse syslog-ng-ctl stats CSV into structured counter rows.

    Input is the semicolon-delimited output of syslog-ng-ctl stats.
    """
    counters: list[dict[str, Any]] = []
    if not raw_csv or not raw_csv.strip():
        return counters
    reader = csv.DictReader(io.StringIO(raw_csv), delimiter=";")
    for row in reader:
        name = row.get("SourceName", "")
        typ = row.get("Type", "")
        try:
            value = int(row.get("Number", 0) or 0)
        except (ValueError, TypeError):
            value = 0
        component = classify_counter_component(name)
        counters.append({
            "name": name,
            "component": component,
            "metric": typ,
            "value": value,
        })
    return counters


def parse_listeners_from_ss(raw_ss: str) -> list[dict[str, Any]]:
    """Parse ss -lntup / ss -lntupa output into structured listener rows.

    Handles both modern ss output (Netid State Recv-Q Send-Q Local:Port Peer:Port)
    and older format (State Recv-Q Send-Q Local:Port Peer:Port).
    Only LISTEN (tcp) and UNCONN (udp) rows are returned.
    """
    rows: list[dict[str, Any]] = []
    for line in raw_ss.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        # Modern format: Netid in parts[0], State in parts[1], Local:Port in parts[4]
        # Classic format: State in parts[0], Local:Port in parts[3]
        if len(parts) >= 6 and parts[1] in {"LISTEN", "UNCONN"}:
            state = parts[1]
            addr_port = parts[4]
        elif parts[0] in {"LISTEN", "UNCONN"}:
            state = parts[0]
            addr_port = parts[3]
        else:
            continue
        if ":" not in addr_port:
            continue
        last_colon = addr_port.rfind(":")
        bind = addr_port[:last_colon]
        port_str = addr_port[last_colon + 1:]
        try:
            port = int(port_str)
        except ValueError:
            continue
        proto = "udp" if state == "UNCONN" else "tcp"
        rows.append({"protocol": proto, "port": port, "bind": bind})
    return rows


def _desired_listeners(env: dict[str, str]) -> list[dict[str, Any]]:
    port_keys: dict[str, tuple[str, str]] = {
        "tcp": ("SC4S_LISTEN_DEFAULT_TCP_PORT", "SC4S_SOURCE_LISTEN_TCP_PORT"),
        "udp": ("SC4S_LISTEN_DEFAULT_UDP_PORT", "SC4S_SOURCE_LISTEN_UDP_PORT"),
        "tls": ("SC4S_LISTEN_DEFAULT_TLS_PORT", "SC4S_SOURCE_LISTEN_TLS_PORT"),
    }
    desired: list[dict[str, Any]] = []
    for proto, (listen_key, src_key) in port_keys.items():
        port_str = env.get(listen_key) or env.get(src_key)
        if port_str:
            for p in port_str.split(","):
                p = p.strip()
                if not p:
                    continue
                try:
                    desired.append({"protocol": proto, "port": int(p)})
                except ValueError:
                    pass
    return desired


def _build_listener_summary(
    desired: list[dict[str, Any]],
    live_listeners: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    live_set = {(r["protocol"], r["port"]) for r in live_listeners}
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for d in desired:
        proto = d["protocol"]
        port = d["port"]
        key = (proto, port)
        if key in seen:
            continue
        seen.add(key)
        live_match = next(
            (r for r in live_listeners if r["protocol"] == proto and r["port"] == port),
            None,
        )
        result.append({
            "protocol": proto,
            "port": port,
            "desired": True,
            "live": key in live_set,
            "bind": live_match.get("bind", "") if live_match else "",
        })
    for r in live_listeners:
        key = (r["protocol"], r["port"])
        if key not in seen:
            seen.add(key)
            result.append({
                "protocol": r["protocol"],
                "port": r["port"],
                "desired": False,
                "live": True,
                "bind": r.get("bind", ""),
            })
    return result


def _build_destination_summary(counters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dests: dict[str, dict[str, Any]] = {}
    for c in counters:
        if c["component"] != "destination":
            continue
        name = c["name"]
        dest_id = re.sub(r"^(dst\.|d_|destination\.)", "", name).split(",")[0] or name
        kind = "splunk_hec" if "hec" in dest_id.lower() else "syslog"
        rec = dests.setdefault(dest_id, {
            "id": dest_id,
            "kind": kind,
            "written": 0,
            "dropped": 0,
            "queued": None,
        })
        metric = c["metric"].lower()
        val = c["value"]
        if metric == "written":
            rec["written"] = (rec.get("written") or 0) + val
        elif metric == "dropped":
            rec["dropped"] = (rec.get("dropped") or 0) + val
        elif metric in {"queued", "memory_usage"}:
            rec["queued"] = (rec.get("queued") or 0) + val
    return sorted(dests.values(), key=lambda x: x["id"])


def redact_secrets_check(env: dict[str, str]) -> dict[str, bool]:
    """Report whether secret-bearing env keys are present (without leaking values)."""
    return {"secrets_present": any(SECRET_KEY_RE.search(k) for k in env)}


def build_runtime_state(
    *,
    control_status: dict[str, Any],
    control_metrics: dict[str, Any],
    control_listeners: dict[str, Any],
    control_warnings: dict[str, Any],
    env: dict[str, str],
    app_version: str,
    supported_sc4s_version: str,
    generated_at: str,
) -> dict[str, Any]:
    """Assemble /api/runtime/state from raw control daemon responses.

    Control daemon failures are captured as ok=false fields, never raised
    as HTTP 500 from this function. Secrets from env are never included in
    the output; their presence is reported via redaction.secrets_present.
    """
    warnings: list[dict[str, Any]] = []

    # Control daemon reachability
    daemon_ok = bool(control_status.get("ok") or control_metrics.get("ok"))
    control_daemon: dict[str, Any] = {
        "ok": daemon_ok,
        "provider": "unix_socket",
    }
    if not daemon_ok:
        err = (
            control_status.get("error")
            or control_metrics.get("error")
            or "control daemon unavailable"
        )
        control_daemon["error"] = err

    # SC4S process state from container inspect
    sc4s_status_raw = control_status.get("status", {}) if control_status.get("ok") else {}
    running_version = sc4s_status_raw.get("image_version")
    version_drift = bool(running_version and running_version != supported_sc4s_version)
    sc4s: dict[str, Any] = {
        "running": bool(sc4s_status_raw.get("running")),
        "status": sc4s_status_raw.get("status") or ("unknown" if not control_status.get("ok") else "unknown"),
        "health": sc4s_status_raw.get("health"),
        "image": sc4s_status_raw.get("image"),
        "image_version": running_version,
        "supported_version": supported_sc4s_version,
        "version_drift": version_drift,
    }

    if version_drift:
        warnings.append({
            "severity": "warning",
            "code": "version_drift",
            "message": (
                f"Running SC4S {running_version} differs from "
                f"Manager-supported SC4S {supported_sc4s_version}"
            ),
        })

    if not sc4s["running"] and control_status.get("ok"):
        warnings.append({
            "severity": "warning",
            "code": "sc4s_not_running",
            "message": f"SC4S container status: {sc4s['status']}",
        })

    # syslog-ng metrics
    metrics_raw = control_metrics.get("stdout", "") if control_metrics.get("ok") else ""
    counters = parse_metrics_to_counters(metrics_raw) if metrics_raw else []

    # Listener comparison: desired (from env) vs live (from control daemon)
    live_listeners_raw = (
        control_listeners.get("listeners", []) if control_listeners.get("ok") else []
    )
    desired = _desired_listeners(env)
    listeners = _build_listener_summary(desired, live_listeners_raw)

    for lst in listeners:
        if lst["desired"] and not lst["live"]:
            warnings.append({
                "severity": "warning",
                "code": "listener_not_live",
                "message": (
                    f"Desired {lst['protocol'].upper()} port {lst['port']} "
                    "has no live listener"
                ),
            })

    # Destination counter summary
    destinations = _build_destination_summary(counters)

    # Bounded log warnings from control daemon (already redacted by control.py)
    if control_warnings.get("ok"):
        for line in (control_warnings.get("errors") or [])[-20:]:
            warnings.append({
                "severity": "error",
                "code": "sc4s_log_error",
                "message": line[:200],
            })
        for line in (control_warnings.get("warnings") or [])[-10:]:
            warnings.append({
                "severity": "warning",
                "code": "sc4s_log_warning",
                "message": line[:200],
            })

    # Secrets: report presence, never include values
    redaction = redact_secrets_check(env)

    overall_ok = bool(
        daemon_ok
        and sc4s["running"]
        and not any(w["severity"] == "error" for w in warnings)
    )

    return {
        "ok": overall_ok,
        "generated_at": generated_at,
        "manager": {
            "version": app_version,
            "health": "ok",
        },
        "control_daemon": control_daemon,
        "sc4s": sc4s,
        "listeners": listeners,
        "counters": counters,
        "destinations": destinations,
        "warnings": warnings,
        "redaction": redaction,
    }
