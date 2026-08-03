#!/usr/bin/env python3
"""Preflight a staged /opt/sc4s Compose deployment without exposing secrets."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

PLACEHOLDERS = {"change-me", "changeme", "change-me-with-random-value", "password", "secret", "latest"}


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def run_preflight(root: Path, *, offline: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str, action: str = "") -> None:
        item = {"name": name, "ok": bool(ok), "detail": detail}
        if action:
            item["action"] = action
        checks.append(item)

    required_files = ["compose.yaml", ".env", "env/env_file", "env_file", "manager.env"]
    missing = [name for name in required_files if not (root / name).is_file()]
    add("files", not missing, "all staged" if not missing else "missing: " + ", ".join(missing),
        "copy the released Compose examples and edit them" if missing else "")

    container_uid = 10001
    dirs = [root / "local", root / "tls", root / "archive", root / "manager" / "state",
            root / "manager" / "backups", root / "manager" / "templates"]
    env_path = root / "env" / "env_file"

    def writable_for_container(path: Path, *, is_file: bool = False) -> bool:
        """Check container UID 10001 can write without trusting root sudo alone.

        os.access as root is meaningless for the container UID. Require ownership by
        UID 10001 with owner-write, world-write, or matching euid with write access.
        """
        try:
            st = path.stat()
        except OSError:
            return False
        if is_file and not path.is_file():
            return False
        if not is_file and not path.is_dir():
            return False
        mode = st.st_mode
        owner_write = bool(mode & 0o200)
        world_write = bool(mode & 0o002)
        if st.st_uid == container_uid and owner_write:
            return True
        if world_write:
            return True
        if os.geteuid() == container_uid and os.access(path, os.W_OK):
            return True
        return False

    bad_dirs = [str(path) for path in dirs if not writable_for_container(path)]
    if not writable_for_container(env_path, is_file=True):
        bad_dirs.append(str(env_path))
    add("writability", not bad_dirs,
        "runtime paths writable for container UID 10001" if not bad_dirs else "not writable for UID 10001: " + ", ".join(bad_dirs),
        "create/chown runtime paths for container UID 10001 (or make them world-writable only in disposable lab paths)" if bad_dirs else "")
    conventional_env = root / "env_file"
    env_link_ok = conventional_env.is_symlink() and conventional_env.resolve() == env_path.resolve()
    add("env_layout", env_link_ok,
        "env_file links to env/env_file" if env_link_ok else "env_file is not the expected env/env_file symlink",
        "run: sudo ln -sfn env/env_file /opt/sc4s/env_file" if not env_link_ok else "")

    manager = parse_env(root / "manager.env")
    mode = manager.get("SC4S_MANAGER_AUTH_MODE", "").lower()
    manual = manager.get("SC4S_MANAGER_MANUAL_LOGIN_TOKEN", "")
    proxy = manager.get("SC4S_MANAGER_PROXY_SECRET", "")
    selected = {"standalone": manual, "proxy": proxy}.get(mode, "")
    other_empty = not proxy if mode == "standalone" else (not manual if mode == "proxy" else False)
    auth_ok = mode in {"standalone", "proxy"} and len(selected) >= 32 and selected.lower() not in PLACEHOLDERS and other_empty
    add("auth", auth_ok, f"mode={mode or 'unset'}; selected credential {'configured' if selected else 'missing'}",
        "choose standalone or proxy and generate exactly one 32+ character secret" if not auth_ok else "")

    compose_env = parse_env(root / ".env")
    version = compose_env.get("SC4S_MANAGER_VERSION", "")
    add("manager_version", bool(version) and version.lower() != "latest", f"version={version or 'unset'}",
        "set SC4S_MANAGER_VERSION to a released version" if not version or version.lower() == "latest" else "")

    sc4s_env = parse_env(env_path)
    hec_ok = bool(sc4s_env.get("SC4S_DEST_SPLUNK_HEC_DEFAULT_URL")) and bool(sc4s_env.get("SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN"))
    add("hec", hec_ok, "default HEC URL/token configured" if hec_ok else "default HEC URL or token missing",
        "configure Splunk HEC in env_file" if not hec_ok else "")

    compose_text = (root / "compose.yaml").read_text(encoding="utf-8") if (root / "compose.yaml").is_file() else ""
    docker_socket_mount = bool(
        re.search(r":\s*/var/run/docker\.sock(?:\s|$)", compose_text)
        or re.search(r"source:\s*/var/run/docker\.sock(?:\s|$)", compose_text)
    )
    add("docker_socket", not docker_socket_mount, "Docker socket is not mounted")

    # Default Compose mounts a named volume at /run/sc4s-manager inside the Manager
    # container. A host socket under /opt/sc4s/manager/control.sock is not proof the
    # container can use it.
    host_control = root / "manager" / "control.sock"
    if host_control.is_socket():
        control_detail = (
            "host socket present at manager/control.sock; default Compose still mounts "
            "/run/sc4s-manager inside the container - treat as observe_only unless that path is wired"
        )
    else:
        control_detail = "observe_only: narrow control socket not supplied for container path /run/sc4s-manager"
    add("control", True, control_detail)

    if offline:
        add("runtime", True, "skipped (--offline)")
    else:
        docker = shutil.which("docker")
        compose_ok = False
        detail = "docker command not found"
        if docker:
            result = subprocess.run([docker, "compose", "-f", str(root / "compose.yaml"), "config", "--quiet"],
                                    cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            compose_ok = result.returncode == 0
            detail = "Compose config valid" if compose_ok else result.stderr.strip()[:300]
        add("compose", compose_ok, detail, "install Docker Compose and fix compose.yaml" if not compose_ok else "")
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2) as response:
                sc4s_ok = response.status == 200
            add("sc4s", sc4s_ok, "SC4S health reachable")
        except Exception as exc:
            add("sc4s", False, f"SC4S health unavailable: {exc}", "start/fix SC4S and retry")
        bind = compose_env.get("SC4S_MANAGER_BIND_ADDRESS", "127.0.0.1")
        port = int(compose_env.get("SC4S_MANAGER_PORT", "8090"))
        sock = socket.socket()
        try:
            sock.bind((bind, port))
            port_ok = True
        except OSError as exc:
            port_ok = False
            detail = str(exc)
        else:
            detail = f"{bind}:{port} available"
        finally:
            sock.close()
        add("manager_port", port_ok, detail, "free or change the Manager port" if not port_ok else "")

    return {"ok": all(item["ok"] for item in checks), "root": str(root), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a staged SC4S Manager Compose installation")
    parser.add_argument("--root", default="/opt/sc4s", help="deployment root (default: /opt/sc4s)")
    parser.add_argument("--offline", action="store_true", help="skip Docker, port, and SC4S runtime probes")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_preflight(Path(args.root), offline=args.offline)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for item in report["checks"]:
            print(f"[{'PASS' if item['ok'] else 'FAIL'}] {item['name']}: {item['detail']}")
            if item.get("action"):
                print(f"       next: {item['action']}")
        print("preflight: " + ("PASS" if report["ok"] else "FAIL"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
