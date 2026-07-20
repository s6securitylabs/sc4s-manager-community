#!/usr/bin/env python3
"""Narrow SC4S control daemon.

Local Unix-socket API for allowlisted SC4S operations. It intentionally does not
expose arbitrary Docker, shell, path, container, or compose controls.
"""
from __future__ import annotations

import json
import os
import re
import socket
import socketserver
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SECRET_KEY_RE = re.compile(r"(TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL|AUTH)", re.I)


def _redact_log_line(line: str) -> str:
    return re.sub(
        r"\b([A-Za-z0-9_]*(?:TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL|AUTH)[A-Za-z0-9_]*)\s*=\s*(\S+)",
        lambda m: f"{m.group(1)}=[REDACTED]",
        line,
        flags=re.I,
    )

SOCKET_PATH = Path(os.environ.get("SC4S_CONTROL_SOCKET", "/run/sc4s-manager/control.sock"))
SC4S_CONTAINER = os.environ.get("SC4S_CONTAINER", "SC4S")
COMPOSE_FILE_DEFAULT = "/opt/sc4s/compose.yaml" if Path("/opt/sc4s/compose.yaml").exists() else "/opt/sc4s/docker-compose.yml"
COMPOSE_FILE = Path(os.environ.get("SC4S_COMPOSE_FILE", COMPOSE_FILE_DEFAULT))
COMPOSE_CWD = Path(os.environ.get("SC4S_COMPOSE_CWD", "/opt/sc4s"))
AUDIT_LOG = Path(os.environ.get("SC4S_CONTROL_AUDIT", "/opt/sc4s-manager/state/control-audit.jsonl"))
SOCKET_GROUP = os.environ.get("SC4S_CONTROL_GROUP", "sc4s-manager")
MAX_LOG_LINES = 500


def run(cmd: list[str], timeout: int = 30, stdout_limit: int | None = 12000, cwd: Path | None = None) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, cwd=str(cwd) if cwd else None)
        stdout = p.stdout if stdout_limit is None else p.stdout[-stdout_limit:]
        return {"ok": p.returncode == 0, "code": p.returncode, "stdout": stdout, "stderr": p.stderr[-12000:]}
    except Exception as e:
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(e)}


def audit(action: str, ok: bool, detail: dict[str, Any] | None = None) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "action": action, "ok": ok, "detail": detail or {}}
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def ensure_fixed_runtime() -> None:
    resolved = COMPOSE_FILE.resolve()
    allowed_paths = {Path("/opt/sc4s/docker-compose.yml"), Path("/opt/sc4s/compose.yaml")}
    if not COMPOSE_FILE.exists() or resolved not in allowed_paths:
        raise RuntimeError("invalid fixed compose file")
    if COMPOSE_CWD.resolve() != Path("/opt/sc4s"):
        raise RuntimeError("invalid fixed compose cwd")


def action_status(_req: dict[str, Any]) -> dict[str, Any]:
    inspect = run(["docker", "inspect", SC4S_CONTAINER], timeout=10, stdout_limit=None)
    if not inspect["ok"]:
        return {"ok": False, "error": inspect["stderr"], "docker": inspect}
    try:
        info = json.loads(inspect["stdout"])[0]
        state = info.get("State", {})
        labels = info.get("Config", {}).get("Labels", {}) or {}
        return {"ok": True, "status": {
            "running": bool(state.get("Running")),
            "status": state.get("Status"),
            "health": (state.get("Health") or {}).get("Status"),
            "started_at": state.get("StartedAt"),
            "restart_count": info.get("RestartCount"),
            "image": info.get("Config", {}).get("Image"),
            "image_version": labels.get("org.opencontainers.image.version"),
            "image_revision": labels.get("org.opencontainers.image.revision"),
        }}
    except Exception as e:
        return {"ok": False, "error": str(e), "docker": inspect}


def action_logs(req: dict[str, Any]) -> dict[str, Any]:
    lines = req.get("lines", 80)
    try:
        lines = int(lines)
    except Exception:
        lines = 80
    lines = max(1, min(lines, MAX_LOG_LINES))
    r = run(["docker", "logs", "--tail", str(lines), SC4S_CONTAINER], timeout=15, stdout_limit=200000)
    return {"ok": r["ok"], "stdout": r["stdout"], "stderr": r["stderr"], "code": r["code"]}


def action_metrics(_req: dict[str, Any]) -> dict[str, Any]:
    r = run(["docker", "exec", SC4S_CONTAINER, "syslog-ng-ctl", "stats"], timeout=20, stdout_limit=None)
    return {"ok": r["ok"], "stdout": r["stdout"], "stderr": r["stderr"], "code": r["code"]}


def action_validate(_req: dict[str, Any]) -> dict[str, Any]:
    script = "while IFS= read -r -d '' e; do export \"$e\"; done </proc/$(pidof syslog-ng)/environ; . /var/lib/python-venv/bin/activate; export PYTHONPATH=/etc/syslog-ng/pylib; syslog-ng -s --no-caps"
    r = run(["docker", "exec", SC4S_CONTAINER, "bash", "-lc", script], timeout=45)
    return {"ok": r["ok"], "stdout": r["stdout"], "stderr": r["stderr"], "code": r["code"]}


def action_reload(_req: dict[str, Any]) -> dict[str, Any]:
    # SC4S entrypoint traps SIGHUP and forwards reload to syslog-ng.
    r = run(["docker", "kill", "--signal", "HUP", SC4S_CONTAINER], timeout=10)
    return {"ok": r["ok"], "stdout": r["stdout"], "stderr": r["stderr"], "code": r["code"], "reload_semantics": "SIGHUP sent to fixed SC4S container"}


def action_restart(_req: dict[str, Any]) -> dict[str, Any]:
    ensure_fixed_runtime()
    r = run(["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d"], timeout=120, cwd=COMPOSE_CWD)
    return {"ok": r["ok"], "stdout": r["stdout"], "stderr": r["stderr"], "code": r["code"]}


def _parse_ss_listeners(raw: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        # Modern ss: Netid State Recv-Q Send-Q Local:Port Peer:Port
        # Classic ss: State Recv-Q Send-Q Local:Port Peer:Port
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


def action_listeners(_req: dict[str, Any]) -> dict[str, Any]:
    """Return active listener ports. Uses fixed ss command; ignores all caller params."""
    # Try inside SC4S container first; fall back to host-side ss.
    r = run(["docker", "exec", SC4S_CONTAINER, "ss", "-lntup"], timeout=10)
    if not r["ok"]:
        r = run(["ss", "-lntup"], timeout=10)
    listeners = _parse_ss_listeners(r.get("stdout", ""))
    return {"ok": r["ok"], "listeners": listeners}


def action_warnings(req: dict[str, Any]) -> dict[str, Any]:
    """Return bounded warning/error log lines. Clamps to MAX_LOG_LINES; no arbitrary filter."""
    lines_req = req.get("lines", 200)
    try:
        lines_req = int(lines_req)
    except Exception:
        lines_req = 200
    lines_req = max(1, min(lines_req, MAX_LOG_LINES))
    r = run(["docker", "logs", "--tail", str(lines_req), SC4S_CONTAINER], timeout=15, stdout_limit=200000)
    if not r["ok"]:
        return {"ok": False, "error": r.get("stderr", "logs failed"), "warnings": [], "errors": [], "line_count": 0}
    warning_re = re.compile(r"\b(warn(?:ing)?)\b", re.I)
    error_re = re.compile(r"\b(err(?:or)?|critical|fatal|fallback)\b", re.I)
    raw_lines = r.get("stdout", "").splitlines()
    warnings: list[str] = []
    errors: list[str] = []
    for line in raw_lines:
        safe = _redact_log_line(line)
        if error_re.search(line):
            errors.append(safe)
        elif warning_re.search(line):
            warnings.append(safe)
    return {
        "ok": True,
        "line_count": len(raw_lines),
        "warnings": warnings[-50:],
        "errors": errors[-50:],
    }


ACTIONS = {
    "status": action_status,
    "logs": action_logs,
    "metrics": action_metrics,
    "validate": action_validate,
    "reload": action_reload,
    "restart": action_restart,
    "listeners": action_listeners,
    "warnings": action_warnings,
}


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(65536)
        try:
            req = json.loads(raw.decode("utf-8"))
            action = req.get("action")
            if action not in ACTIONS:
                raise ValueError("unsupported action")
            resp = ACTIONS[action](req)
            audit(action, bool(resp.get("ok")), {"remote": "unix"})
        except Exception as e:
            resp = {"ok": False, "error": str(e)}
            audit("invalid", False, {"error": str(e)})
        self.wfile.write((json.dumps(resp, sort_keys=True) + "\n").encode("utf-8"))


class UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class ActivatedUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    """A Unix server backed by the listener passed by systemd (fd 3)."""

    daemon_threads = True

    def __init__(self, listener: socket.socket):
        socketserver.BaseServer.__init__(self, listener.getsockname(), Handler)
        self.socket = listener
        self.server_address = listener.getsockname()


def take_systemd_socket() -> socket.socket | None:
    """Consume exactly one systemd-passed AF_UNIX stream listener, if present.

    The service deliberately fails closed for malformed activation metadata instead
    of falling back to unlinking/rebinding a socket systemd owns.
    """
    listen_pid = os.environ.get("LISTEN_PID")
    listen_fds = os.environ.get("LISTEN_FDS")
    if listen_pid is None and listen_fds is None:
        return None
    if listen_pid != str(os.getpid()) or listen_fds != "1":
        raise RuntimeError("invalid systemd socket activation metadata")

    listener = socket.socket(fileno=3)
    os.environ.pop("LISTEN_PID", None)
    os.environ.pop("LISTEN_FDS", None)
    if listener.family != socket.AF_UNIX or (listener.type & 0xF) != socket.SOCK_STREAM:
        listener.close()
        raise RuntimeError("systemd activation socket must be an AF_UNIX stream listener")
    if not listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN):
        listener.close()
        raise RuntimeError("systemd activation socket is not listening")
    return listener


def main() -> None:
    activated_listener = take_systemd_socket()
    activated = activated_listener is not None
    if activated:
        server = ActivatedUnixServer(activated_listener)
        print(f"sc4s-control listening on {SOCKET_PATH} (systemd socket activation)", flush=True)
    else:
        SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        server = UnixServer(str(SOCKET_PATH), Handler)
        os.chmod(SOCKET_PATH, 0o660)
        try:
            import grp
            gid = grp.getgrnam(SOCKET_GROUP).gr_gid
            os.chown(SOCKET_PATH, 0, gid)
        except Exception:
            pass
        print(f"sc4s-control listening on {SOCKET_PATH}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if not activated:
            try:
                SOCKET_PATH.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    main()
