#!/usr/bin/env python3
"""SC4S Manager: dependency-free GUI/API for controlled SC4S operations.

Designed for reverse-proxy protected deployments. Unsafe actions require a
trusted proxy header secret, local API token, or explicit manual login token.
Health is intentionally open.
"""
from __future__ import annotations

import base64
import csv
import datetime as dt
import difflib
import hashlib
import hmac
import html
import ipaddress
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlencode, urlparse, unquote

APP_VERSION = "1.0.2"
SUPPORTED_SC4S_VERSION = "3.43.0"
SC4S_DOCS_BASE = "https://splunk.github.io/splunk-connect-for-syslog/3.43.0"
ROOT = Path(os.environ.get("SC4S_ROOT", "/opt/sc4s"))
LOCAL_ROOT = ROOT / "local"
ENV_FILE = ROOT / "env_file"
MANAGER_ROOT = Path(os.environ.get("SC4S_MANAGER_ROOT", "/opt/sc4s-manager"))
STATE_DIR = MANAGER_ROOT / "state"
BACKUP_DIR = MANAGER_ROOT / "backups"
TEMPLATE_DIR = MANAGER_ROOT / "templates"
PACK_DIR = MANAGER_ROOT / "packs"
FRONTEND_DIST = MANAGER_ROOT / "frontend" / "dist"
TLS_DIR = ROOT / "tls"
AUDIT_LOG = STATE_DIR / "audit.jsonl"
STATE_FILE = STATE_DIR / "state.json"
HOST = os.environ.get("SC4S_MANAGER_HOST", "0.0.0.0")
PORT = int(os.environ.get("SC4S_MANAGER_PORT", "8090"))
PROXY_SECRET = os.environ.get("SC4S_MANAGER_PROXY_SECRET", "")
API_TOKEN = os.environ.get("SC4S_MANAGER_API_TOKEN", "")
MANUAL_LOGIN_TOKEN = os.environ.get("SC4S_MANAGER_MANUAL_LOGIN_TOKEN", "")
SC4S_CONTAINER = os.environ.get("SC4S_CONTAINER", "SC4S")
CONTROL_SOCKET = os.environ.get("SC4S_CONTROL_SOCKET", "/run/sc4s-manager/control.sock")

INDEX_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>SC4S Manager</title>
</head>
<body>
  <main>
    <h1>SC4S Manager</h1>
    <p>Static frontend bundle not found. Build the frontend or install a release package with frontend assets.</p>
    <h2>Operations</h2>
    <p>Use the packaged UI or API to validate, stage, apply, and verify SC4S changes.</p>
    <h2>Metrics Explorer</h2>
    <p>Runtime counters are available from /api/metrics/syslog-ng when authenticated.</p>
  </main>
</body>
</html>
"""

SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
FILTER_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
ENV_KEY_RE = re.compile(r"^[A-Z0-9_]{2,120}$")
SECRET_KEY_RE = re.compile(r"(TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL|AUTH)", re.I)
PORT_KEYS = {
    "tcp": "SC4S_SOURCE_LISTEN_TCP_PORT",
    "udp": "SC4S_SOURCE_LISTEN_UDP_PORT",
    "tls": "SC4S_SOURCE_LISTEN_TLS_PORT",
}
LISTEN_KEYS = {
    "tcp": "SC4S_LISTEN_DEFAULT_TCP_PORT",
    "udp": "SC4S_LISTEN_DEFAULT_UDP_PORT",
    "tls": "SC4S_LISTEN_DEFAULT_TLS_PORT",
}


OPTION_REGISTRY = [
    {"key":"SC4S_SOURCE_LISTEN_TCP_PORT","label":"Default TCP syslog port","category":"listeners","type":"port_csv","default":"514","description":"Comma-separated TCP listener ports for the DEFAULT SC4S source.","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_LISTEN_UDP_PORT","label":"Default UDP syslog port","category":"listeners","type":"port_csv","default":"514","description":"Comma-separated UDP listener ports for the DEFAULT SC4S source.","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_LISTEN_TLS_PORT","label":"Default TLS syslog port","category":"listeners","type":"port_csv","default":"6514","description":"Comma-separated TLS listener ports for the DEFAULT SC4S source. Requires TLS enabled and a matching server certificate/private key bundle.","requires":["SC4S_SOURCE_TLS_ENABLE=yes","/etc/syslog-ng/tls/server.pem","/etc/syslog-ng/tls/server.key"],"restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_TLS_ENABLE","label":"Enable TLS listeners","category":"tls","type":"boolean","default":"no","description":"Enables syslog-ng TLS sources. Without this, a TLS port value alone will not create a live TLS listener.","requires":["/etc/syslog-ng/tls/server.pem","/etc/syslog-ng/tls/server.key"],"restart_required":True,"secret":False},
    {"key":"SC4S_TLS","label":"TLS directory inside container","category":"tls","type":"path","default":"/etc/syslog-ng/tls","description":"Container path containing server.pem, server.key and optional CA material for SC4S TLS listeners.","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_TLS_OPTIONS","label":"TLS protocol options","category":"tls","type":"string","default":"no-sslv2, no-sslv3, no-tlsv1","description":"syslog-ng ssl-options for TLS listeners.","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_TLS_CIPHER_SUITE","label":"TLS cipher suite","category":"tls","type":"string","default":"HIGH:!aNULL:!eNULL:!kECDH:!aDH:!RC4:!3DES:!CAMELLIA:!MD5:!PSK:!SRP:!KRB5:@STRENGTH","description":"OpenSSL cipher suite string for TLS listeners.","restart_required":True,"secret":False},
    {"key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_URL","label":"Default Splunk HEC URL","category":"destinations","type":"url","description":"Destination Splunk HEC collector URL used by the DEFAULT destination group.","restart_required":True,"secret":False},
    {"key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN","label":"Default Splunk HEC token","category":"destinations","type":"secret","description":"Secret HEC token. Managed through a credential flow, never displayed or edited as plaintext in the normal GUI.","restart_required":True,"secret":True},
    {"key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_TLS_VERIFY","label":"Verify Splunk HEC TLS","category":"destinations","type":"boolean","default":"yes","description":"Controls TLS verification for outbound Splunk HEC traffic.","restart_required":True,"secret":False},
    {"key":"SC4S_GLOBAL_OPTIONS_STATS_FREQ","label":"Stats frequency","category":"metrics","type":"integer","default":"60","description":"syslog-ng statistics update frequency in seconds.","restart_required":True,"secret":False},
    {"key":"SC4S_GLOBAL_OPTIONS_STATS_LEVEL","label":"Stats level","category":"metrics","type":"integer","default":"1","description":"syslog-ng statistics verbosity level.","restart_required":True,"secret":False},
]

# V1 docs-backed common option catalog for supported SC4S 3.43.0. This is
# intentionally static for the pinned release; future upgrade flow regenerates it
# from the matching upstream SC4S docs/tag before changing SUPPORTED_SC4S_VERSION.
OPTION_REGISTRY.extend([
    {"key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_WORKERS","label":"Default HEC workers","category":"destinations","type":"integer","default":"10","description":"Number of worker threads used by the default Splunk HEC destination.","docs":"configuration/#configure-your-splunk-hec-destination","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_HTTP_COMPRESSION","label":"Default HEC HTTP compression","category":"destinations","type":"boolean","default":"no","description":"Enable gzip compression for outbound default HEC traffic.","docs":"destinations/#http-compression","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_DISKBUFF_ENABLE","label":"Default HEC disk buffer","category":"disk_buffer","type":"boolean","default":"yes","description":"Enable local syslog-ng disk buffering for the default Splunk HEC destination.","docs":"configuration/#disk-buffer-variables","apply_mode":"restart_required","restart_required":True,"secret":False,"warning":"Disk buffer sizing is per destination worker; undersizing can drop data during HEC outages."},
    {"key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_DISKBUFF_RELIABLE","label":"Reliable disk buffer","category":"disk_buffer","type":"boolean","default":"no","description":"Use reliable disk buffering. SC4S docs recommend normal buffering for performance unless a specific need exists.","docs":"configuration/#about-disk-buffering","apply_mode":"restart_required","restart_required":True,"secret":False,"warning":"Reliable disk buffering has a significant performance penalty."},
    {"key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_DISKBUFF_MEMBUFSIZE","label":"Disk buffer memory size","category":"disk_buffer","type":"bytes","default":"10241024","description":"Worker memory buffer size in bytes for reliable disk buffering.","docs":"configuration/#disk-buffer-variables","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_DISKBUFF_DISKBUFSIZE","label":"Disk buffer disk size","category":"disk_buffer","type":"bytes","default":"53687091200","description":"Local disk buffer size in bytes for each worker.","docs":"configuration/#disk-buffer-variables","apply_mode":"restart_required","restart_required":True,"secret":False,"warning":"Total disk use can be workers multiplied by this value."},
    {"key":"SC4S_LISTEN_DEFAULT_RFC5426_PORT","label":"RFC5426 UDP listener port","category":"listeners","type":"port_csv","default":"601","description":"Default RFC5426 syslog-over-UDP listener port.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_LISTEN_DEFAULT_RFC6587_PORT","label":"RFC6587 TCP listener port","category":"listeners","type":"port_csv","default":"601","description":"Default RFC6587 framed syslog-over-TCP listener port.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_LISTEN_DEFAULT_RFC5425_PORT","label":"RFC5425 TLS listener port","category":"listeners","type":"port_csv","default":"5425","description":"Default RFC5425 syslog-over-TLS listener port.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_LISTEN_UDP_SOCKETS","label":"UDP listener sockets","category":"performance","type":"integer","default":"4","description":"Number of kernel sockets per active UDP port.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_LISTEN_TCP_SOCKETS","label":"TCP listener sockets","category":"performance","type":"integer","default":"1","description":"Number of sockets per active TCP port.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_LISTEN_TLS_SOCKETS","label":"TLS listener sockets","category":"performance","type":"integer","default":"1","description":"Number of sockets per active TLS port.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_UDP_FETCH_LIMIT","label":"UDP fetch limit","category":"performance","type":"integer","default":"1000","description":"Number of UDP events fetched from server buffer at one time.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_TCP_FETCH_LIMIT","label":"TCP fetch limit","category":"performance","type":"integer","default":"2000","description":"Number of TCP events fetched from server buffer at one time.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_TLS_FETCH_LIMIT","label":"TLS fetch limit","category":"performance","type":"integer","default":"2000","description":"Number of TLS events fetched from server buffer at one time.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_UDP_SO_RCVBUFF","label":"UDP receive buffer","category":"performance","type":"bytes","default":"17039360","description":"Requested UDP socket receive buffer size in bytes; host kernel must allow at least this value.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False,"warning":"Kernel rmem settings must be aligned or syslog-ng will warn and use a smaller buffer."},
    {"key":"SC4S_SOURCE_TCP_SO_RCVBUFF","label":"TCP receive buffer","category":"performance","type":"bytes","default":"17039360","description":"Requested TCP socket receive buffer size in bytes.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_TLS_SO_RCVBUFF","label":"TLS receive buffer","category":"performance","type":"bytes","default":"17039360","description":"Requested TLS socket receive buffer size in bytes.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_TCP_MAX_CONNECTIONS","label":"TCP max connections","category":"performance","type":"integer","default":"2000","description":"Maximum TCP source connections.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_SOURCE_TLS_MAX_CONNECTIONS","label":"TLS max connections","category":"tls","type":"integer","default":"2000","description":"Maximum TLS source connections.","docs":"configuration/#syslog-source-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_ENABLE_EBPF","label":"Enable eBPF UDP scaling","category":"performance","type":"boolean","default":"no","description":"Use eBPF to leverage multithreading when consuming from a single heavy UDP stream.","docs":"configuration/#about-ebpf","apply_mode":"restart_required","restart_required":True,"secret":False,"warning":"Requires host support and privileged/container capability design."},
    {"key":"SC4S_EBPF_NO_SOCKETS","label":"eBPF socket count","category":"performance","type":"integer","default":"4","description":"Number of eBPF threads/sockets to use.","docs":"configuration/#about-ebpf","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_ENABLE_PARALLELIZE","label":"Enable TCP parallelize","category":"performance","type":"boolean","default":"no","description":"Use parallelize to leverage multithreading when consuming from a single TCP stream.","docs":"configuration/#parallelize","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_PARALLELIZE_NO_PARTITION","label":"Parallelize partitions","category":"performance","type":"integer","default":"4","description":"Number of partitions used by SC4S TCP parallelize.","docs":"configuration/#parallelize","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_USE_REVERSE_DNS","label":"Use reverse DNS","category":"dns","type":"boolean","default":"no","description":"Use reverse DNS to identify hosts when HOST is not valid in the syslog header.","docs":"configuration/#global-configuration-variables","apply_mode":"restart_required","restart_required":True,"secret":False,"warning":"Can significantly affect performance if DNS is slow."},
    {"key":"SC4S_REVERSE_DNS_KEEP_FQDN","label":"Keep reverse DNS FQDN","category":"dns","type":"boolean","default":"no","description":"Keep full FQDN from reverse DNS rather than truncating to hostname.","docs":"configuration/#global-configuration-variables","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_ARCHIVE_GLOBAL","label":"Global archive","category":"archive","type":"boolean_or_unset","default":"unset","description":"Enable archiving for all vendor_products.","docs":"configuration/#archive-file-configuration","apply_mode":"restart_required","restart_required":True,"secret":False,"warning":"SC4S does not prune archive files; external retention is required."},
    {"key":"SC4S_GLOBAL_ARCHIVE_MODE","label":"Archive mode","category":"archive","type":"enum","default":"compliance","allowed_values":["compliance","diode"],"description":"Folder/path layout mode for archived messages.","docs":"configuration/#archive-file-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_LISTEN_STATUS_PORT","label":"SC4S status port","category":"operations","type":"port","default":"8080","description":"Status/health port used by SC4S internal health check service.","docs":"configuration/#change-your-status-port","apply_mode":"restart_required","restart_required":True,"secret":False},
    {"key":"SC4S_DEBUG_LOGS","label":"Debug logs","category":"operations","type":"boolean","default":"no","description":"Run syslog-ng with debug/verbose/stderr flags for troubleshooting.","docs":"troubleshooting/troubleshoot_SC4S_server/#enable-debug-logging","apply_mode":"restart_required","restart_required":True,"secret":False,"warning":"Debug logging is verbose; do not leave enabled in production."},
    {"key":"SC4S_SEND_METRICS_TERMINAL","label":"Send metrics to terminal","category":"operations","type":"boolean","default":"yes","description":"Control whether metrics/internal processing messages are emitted to terminal in some runtimes.","docs":"troubleshooting/troubleshoot_SC4S_server/#issue-terminal-is-overwhelmed-by-metrics-and-internal-processing-messages-in-a-custom-environment-configuration","apply_mode":"restart_required","restart_required":True,"secret":False},
])


CSV_FILES = {
    "vendor_product": LOCAL_ROOT / "context" / "vendor_product_by_source.csv",
    "splunk_metadata": LOCAL_ROOT / "context" / "splunk_metadata.csv",
    "compliance_meta": LOCAL_ROOT / "context" / "compliance_meta_by_source.csv",
    "host": LOCAL_ROOT / "context" / "host.csv",
}
EDITABLE_ROOTS = [LOCAL_ROOT / "context", LOCAL_ROOT / "config"]
EDITABLE_SUFFIXES = {".csv", ".conf", ".md", ".txt"}

SOURCE_CATALOG = [
    {"vendor_product":"cisco_asa","label":"Cisco ASA","default_index":"netfw","docs":"sources/vendor/Cisco/asa/","notes":"Common firewall source; SC4S can usually identify ASA messages, but source mapping helps disambiguation."},
    {"vendor_product":"cisco_ios","label":"Cisco IOS","default_index":"netops","docs":"sources/vendor/Cisco/ios/","notes":"Network device syslog source."},
    {"vendor_product":"paloalto_panos","label":"Palo Alto PAN-OS","default_index":"netfw","docs":"sources/vendor/PaloAltoNetworks/panos/","notes":"Firewall source. Confirm sourcetype/index requirements in Splunk."},
    {"vendor_product":"fortinet_fortigate","label":"Fortinet FortiGate","default_index":"netfw","docs":"sources/vendor/Fortinet/fortigate/","notes":"Firewall source. Verify Fortinet sourcetype prefix settings if customised."},
    {"vendor_product":"vmware_vsphere","label":"VMware vSphere","default_index":"vmware","docs":"sources/vendor/VMWare/vsphere/","notes":"Often benefits from source mapping or dedicated port due generic program names."},
    {"vendor_product":"linux_messages_syslog","label":"Linux syslog/messages","default_index":"osnix","docs":"sources/simple/","notes":"Generic/simple syslog source."},
]
_lock = threading.RLock()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def ensure_dirs() -> None:
    for p in [STATE_DIR, BACKUP_DIR, TEMPLATE_DIR, TLS_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def startup_permission_error_message(error: PermissionError) -> str:
    return (
        "SC4S Manager cannot create its required runtime directories. "
        f"SC4S_ROOT={ROOT} and SC4S_MANAGER_ROOT={MANAGER_ROOT}. "
        f"The operating system refused access while creating {getattr(error, 'filename', None) or 'a runtime path'}. "
        "Run Manager with a service account that can write those paths, create/chown the directories first, "
        "or set SC4S_ROOT and SC4S_MANAGER_ROOT to writable locations for local/dev runs."
    )


def run(cmd: list[str], timeout: int = 20, stdout_limit: int | None = 12000) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        stdout = p.stdout if stdout_limit is None else p.stdout[-stdout_limit:]
        return {"ok": p.returncode == 0, "code": p.returncode, "stdout": stdout, "stderr": p.stderr[-12000:]}
    except Exception as e:
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(e)}



def control_request(action: str, **params: Any) -> dict[str, Any]:
    """Call the narrow SC4S control daemon. No Docker socket access here."""
    req = {"action": action, **params}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(60)
            s.connect(CONTROL_SOCKET)
            s.sendall((json.dumps(req) + "\n").encode("utf-8"))
            chunks = []
            while True:
                data = s.recv(65536)
                if not data:
                    break
                chunks.append(data)
                if b"\n" in data:
                    break
        raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
        return json.loads(raw) if raw else {"ok": False, "error": "empty control response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"disabled_ports": {}, "created_at": now()}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"disabled_ports": {}, "state_error": "invalid state file"}


def save_state(state: dict[str, Any]) -> None:
    atomic_write(STATE_FILE, json.dumps(state, indent=2, sort_keys=True) + "\n")


def audit(action: str, actor: str, details: dict[str, Any]) -> None:
    ensure_dirs()
    redacted = redact(details)
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps({"ts": now(), "actor": actor or "unknown", "action": action, "details": redacted}, sort_keys=True) + "\n")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            ks = str(k)
            # Do not redact structural fields named "key"/"secret" in option metadata.
            # Redact actual credential-bearing fields only.
            # removed_env_keys carries env var *names* (never values) so API
            # consumers can verify credential cleanup after a destination delete.
            sensitive = SECRET_KEY_RE.search(ks) and ks.lower() not in {"key", "listen_key", "secret", "contains_secrets", "removed_env_keys", "authenticated"}
            out[k] = "[REDACTED]" if sensitive else redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def safe_actor(actor: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_@-]", "_", actor or "unknown")[:80]
    return cleaned or "unknown"


def resolved_under(path: Path, roots: tuple[Path, ...], *, label: str = "path") -> Path:
    candidate = path.resolve(strict=False)
    for root in roots:
        try:
            candidate.relative_to(root.resolve(strict=False))
            return candidate
        except ValueError:
            continue
    raise ValueError(f"{label} is outside the allowed roots")


def backup(path: Path, actor: str) -> Path:
    ensure_dirs()
    path = resolved_under(path, (ROOT,), label="backup source")
    rel = path.relative_to(ROOT.resolve(strict=False))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    target = BACKUP_DIR / f"{str(rel).replace('/', '__')}.{stamp}.{safe_actor(actor)}.bak"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return target


def atomic_write(path: Path, content: str) -> None:
    path = resolved_under(path, (ROOT, MANAGER_ROOT), label="write target")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path = resolved_under(path, (ROOT, MANAGER_ROOT), label="write target")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def parse_env() -> dict[str, str]:
    data: dict[str, str] = {}
    if not ENV_FILE.exists():
        return data
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def render_env(new_values: dict[str, str | None]) -> str:
    seen = set()
    lines = []
    original = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
    for line in original:
        stripped = line.strip()
        key = None
        target = stripped[1:].strip() if stripped.startswith("#") else stripped
        if "=" in target:
            k = target.split("=", 1)[0].strip()
            if ENV_KEY_RE.match(k):
                key = k
        if key and key in new_values:
            seen.add(key)
            val = new_values[key]
            if val is None:
                lines.append(f"# {key}=")
            else:
                lines.append(f"{key}={val}")
        else:
            lines.append(line)
    for k, v in new_values.items():
        if k not in seen and v is not None:
            lines.append(f"{k}={v}")
    return "\n".join(lines).rstrip() + "\n"


def validate_port(value: Any) -> int:
    try:
        port = int(value)
    except Exception:
        raise ValueError("port must be an integer")
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    return port


def set_port(kind: str, enabled: bool, port: int | None, actor: str) -> dict[str, Any]:
    if kind not in PORT_KEYS:
        raise ValueError("unknown port kind")
    key = PORT_KEYS[kind]
    state = load_state()
    env = parse_env()
    updates: dict[str, str | None] = {}
    if enabled:
        if port is None:
            port = int(state.get("disabled_ports", {}).get(kind) or env.get(key) or (6514 if kind == "tls" else 514))
        port = validate_port(port)
        updates[key] = str(port)
        updates[LISTEN_KEYS[kind]] = str(port)
        state.setdefault("disabled_ports", {}).pop(kind, None)
    else:
        current = env.get(key)
        if current:
            state.setdefault("disabled_ports", {})[kind] = current
        updates[key] = None
        updates[LISTEN_KEYS[kind]] = None
    with _lock:
        if ENV_FILE.exists():
            b = backup(ENV_FILE, actor)
        else:
            b = None
        atomic_write(ENV_FILE, render_env(updates))
        save_state(state)
    audit("set_port", actor, {"kind": kind, "enabled": enabled, "port": port, "backup": str(b) if b else None})
    return {"kind": kind, "enabled": enabled, "port": port, "backup": str(b) if b else None, "restart_required": True}


def set_env_value(key: str, value: str, actor: str) -> dict[str, Any]:
    if not ENV_KEY_RE.match(key):
        raise ValueError("invalid environment key")
    if SECRET_KEY_RE.search(key):
        raise ValueError("secret keys cannot be edited through the GUI")
    if "\n" in value or "\r" in value:
        raise ValueError("value must be single-line")
    with _lock:
        b = backup(ENV_FILE, actor) if ENV_FILE.exists() else None
        atomic_write(ENV_FILE, render_env({key: value}))
    audit("set_env", actor, {"key": key, "value": value, "backup": str(b) if b else None})
    return {"key": key, "value": value, "backup": str(b) if b else None, "restart_required": True}


def restart_sc4s(actor: str) -> dict[str, Any]:
    b = backup(ENV_FILE, actor) if ENV_FILE.exists() else None
    result = control_request("restart")
    audit("restart_sc4s", actor, {"result": result, "backup": str(b) if b else None, "provider": "narrow-control"})
    return result


def reload_sc4s(actor: str) -> dict[str, Any]:
    result = control_request("reload")
    audit("reload_sc4s", actor, {"result": result, "provider": "narrow-control"})
    return result


def docker_status() -> dict[str, Any]:
    resp = control_request("status")
    if not resp.get("ok"):
        return {"running": False, "error": resp.get("error") or resp.get("stderr") or "control status failed", "provider": "narrow-control"}
    status = resp.get("status", {})
    status["provider"] = "narrow-control"
    return status


def health_probe() -> dict[str, Any]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=3) as r:
            body = r.read(4096).decode(errors="replace")
            return {"ok": r.status == 200, "status": r.status, "body": body}
    except Exception as e:
        return {"ok": False, "error": str(e)}



def cert_fingerprint(path: Path) -> str | None:
    if not path.exists():
        return None
    r = run(["openssl", "x509", "-noout", "-fingerprint", "-sha256", "-in", str(path)], timeout=10)
    if not r["ok"]:
        return None
    return r["stdout"].strip()


def listener_active(port: str | int, proto: str = "tcp") -> bool:
    r = run(["ss", "-lntup" if proto == "tcp" else "-lnuap"], timeout=10)
    if not r["ok"]:
        return False
    needle = f":{port}"
    return any(needle in line for line in r["stdout"].splitlines())



def cert_expiry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"not_after": None, "days_remaining": None}
    r = run(["openssl", "x509", "-enddate", "-noout", "-in", str(path)], timeout=10)
    if not r["ok"]:
        return {"not_after": None, "days_remaining": None, "error": r["stderr"]}
    line = r["stdout"].strip()
    if line.startswith("notAfter="):
        raw = line.split("=", 1)[1]
        try:
            expires = dt.datetime.strptime(raw, "%b %d %H:%M:%S %Y GMT").replace(tzinfo=dt.timezone.utc)
            days = int((expires - dt.datetime.now(dt.timezone.utc)).total_seconds() // 86400)
            return {"not_after": expires.isoformat(), "days_remaining": days}
        except Exception as e:
            return {"not_after": raw, "days_remaining": None, "error": str(e)}
    return {"not_after": line, "days_remaining": None}


def set_secret_env_value(key: str, value: str, actor: str) -> dict[str, Any]:
    if not ENV_KEY_RE.match(key):
        raise ValueError("invalid environment key")
    if not SECRET_KEY_RE.search(key):
        raise ValueError("this endpoint only accepts secret-like keys")
    if not value or "\n" in value or "\r" in value:
        raise ValueError("secret value must be non-empty and single-line")
    with _lock:
        b = backup(ENV_FILE, actor) if ENV_FILE.exists() else None
        atomic_write(ENV_FILE, render_env({key: value}))
    audit("set_secret_env", actor, {"key": key, "value": "[REDACTED]", "backup": str(b) if b else None})
    return {"key": key, "value": "[REDACTED]", "backup": str(b) if b else None, "restart_required": True}


def redact_line(line: str) -> str:
    if "=" in line:
        k, _ = line.split("=", 1)
        if SECRET_KEY_RE.search(k):
            return k + "=[REDACTED]"
    return line


def redact_log_line(line: str) -> str:
    return re.sub(
        r"\b([A-Za-z0-9_]*(?:TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL|AUTH)[A-Za-z0-9_]*)\s*=\s*(\"[^\"]*\"|'[^']*'|\S+)",
        lambda m: f"{m.group(1)}=[REDACTED]",
        line,
        flags=re.I,
    )


def backup_target_from_name(name: str) -> Path:
    safe = Path(name).name
    if not safe.endswith(".bak"):
        raise ValueError("backup not found")
    stem = safe[:-4]
    match = re.match(r"^(?P<rel>.+)\.\d{8}T\d{6}\.\d+Z\.[A-Za-z0-9_@-]+$", stem)
    rel_token = match.group("rel") if match else safe.split(".", 1)[0]
    if rel_token == "env_file":
        return ENV_FILE
    if rel_token.startswith("local__"):
        dest = resolved_under(ROOT / rel_token.replace("__", "/"), tuple(EDITABLE_ROOTS), label="backup target")
        if dest.suffix not in EDITABLE_SUFFIXES:
            raise ValueError("invalid backup target")
        return dest
    if rel_token.startswith("tls__"):
        dest = resolved_under(ROOT / rel_token.replace("__", "/"), (TLS_DIR,), label="backup target")
        if dest.name not in {"server.pem", "server.key", "ca.pem"}:
            raise ValueError("invalid backup target")
        return dest
    # Backward compatibility for legacy backup names created before backups used
    # ROOT-relative TLS paths.
    if safe.startswith(("server.pem.", "server.key.", "ca.pem.")):
        return TLS_DIR / safe.split(".", 2)[0]
    return ENV_FILE


def backup_diff(name: str) -> dict[str, Any]:
    ensure_dirs()
    safe = Path(name).name
    src = resolved_under(BACKUP_DIR / safe, (BACKUP_DIR,), label="backup name")
    if not src.exists() or src.suffix != ".bak":
        raise ValueError("backup not found")
    dest = backup_target_from_name(safe)
    old_raw = src.read_text(errors="replace").splitlines()
    new_raw = dest.read_text(errors="replace").splitlines() if dest.exists() else []
    old = [redact_line(x) for x in old_raw]
    new = [redact_line(x) for x in new_raw]
    diff = "\n".join(difflib.unified_diff(old, new, fromfile=f"backup/{safe}", tofile=str(dest), lineterm=""))
    if not diff and old_raw != new_raw:
        changed_secret_keys = []
        for a, b in zip(old_raw, new_raw):
            if a != b and "=" in a:
                k = a.split("=", 1)[0]
                if SECRET_KEY_RE.search(k):
                    changed_secret_keys.append(k)
        if changed_secret_keys:
            diff = "\n".join(f"{k}=[REDACTED]" for k in sorted(set(changed_secret_keys)))
    return {"backup": str(src), "target": str(dest), "diff": diff}



def option_by_key(key: str) -> dict[str, Any] | None:
    for opt in OPTION_REGISTRY:
        if opt.get("key") == key:
            return normalize_option(opt, parse_env())
    return None


def redacted_unified_diff(old_text: str, new_text: str, fromfile: str = "current", tofile: str = "proposed") -> str:
    old = [redact_line(x) for x in old_text.splitlines()]
    new = [redact_line(x) for x in new_text.splitlines()]
    diff = "\n".join(difflib.unified_diff(old, new, fromfile=fromfile, tofile=tofile, lineterm=""))
    if not diff and old_text != new_text:
        # Secret-only changes can redact to identical lines. Still show that the secret-bearing key changed.
        keys = []
        for line in new_text.splitlines():
            if "=" in line:
                k = line.split("=", 1)[0]
                if SECRET_KEY_RE.search(k):
                    keys.append(k)
        diff = "\n".join(f"{k}=[REDACTED]" for k in sorted(set(keys)))
    return diff


def proposed_change(payload: dict[str, Any]) -> dict[str, Any]:
    kind = str(payload.get("type", "env"))
    if kind == "env":
        key = str(payload.get("key", ""))
        value = str(payload.get("value", ""))
        if not ENV_KEY_RE.match(key):
            raise ValueError("invalid environment key")
        if "\n" in value or "\r" in value:
            raise ValueError("value must be single-line")
        current = ENV_FILE.read_text() if ENV_FILE.exists() else ""
        proposed = render_env({key: value})
        opt = option_by_key(key) or normalize_option({"key": key}, parse_env())
        return {"type": "env", "target": str(ENV_FILE), "content": proposed, "current": current, "apply_mode": opt.get("apply_mode", "restart_required"), "key": key, "secret": bool(opt.get("secret"))}
    if kind == "file":
        rel = str(payload.get("path", ""))
        content = str(payload.get("content", ""))
        path = safe_editable_path(rel)
        current = path.read_text() if path.exists() else ""
        return {"type": "file", "target": str(path), "content": content, "current": current, "apply_mode": "reloadable", "path": rel, "secret": False}
    raise ValueError("unsupported change type")


def preview_change(payload: dict[str, Any]) -> dict[str, Any]:
    change = proposed_change(payload)
    diff = redacted_unified_diff(change["current"], change["content"], "current", "proposed")
    return {"ok": True, "type": change["type"], "target": change["target"], "apply_mode": change["apply_mode"], "diff": diff, "validation": {"skipped": True, "reason": "preview only; apply performs validation before reload/restart"}}


def apply_change(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    change = proposed_change(payload)
    diff = redacted_unified_diff(change["current"], change["content"], "current", "proposed")
    target = Path(change["target"])
    with _lock:
        b = backup(target, actor) if target.exists() else None
        atomic_write(target, change["content"])
    validation = validate_config()
    if not validation.get("ok"):
        rolled_back = False
        if b:
            shutil.copy2(b, target)
            rolled_back = True
        elif change["type"] == "file":
            # New file with no prior backup: remove it so a failed apply cannot
            # leave broken config behind for the next restart.
            target.unlink(missing_ok=True)
            rolled_back = True
        audit("apply_change_failed", actor, {"target": str(target), "type": change["type"], "validation": validation, "backup": str(b) if b else None, "rolled_back": rolled_back})
        return {"ok": False, "target": str(target), "type": change["type"], "apply_mode": change["apply_mode"], "diff": diff, "backup": str(b) if b else None, "validation": validation, "rolled_back": rolled_back}
    control = {"ok": True, "skipped": True}
    if payload.get("apply", True):
        control = reload_sc4s(actor) if change["apply_mode"] == "reloadable" else restart_sc4s(actor)
    post = {"docker": docker_status(), "health": health_probe(), "ports": port_summary(parse_env())}
    ok = bool(validation.get("ok") and control.get("ok", True))
    audit("apply_change", actor, {"target": str(target), "type": change["type"], "apply_mode": change["apply_mode"], "ok": ok, "backup": str(b) if b else None, "control": control})
    return {"ok": ok, "target": str(target), "type": change["type"], "apply_mode": change["apply_mode"], "diff": diff, "backup": str(b) if b else None, "validation": validation, "control": control, "post_check": post}

def prom_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def prometheus_metrics(metrics: dict[str, Any] | None = None) -> str:
    metrics = metrics or syslog_ng_metrics()
    lines = [
        "# HELP sc4s_manager_syslogng_counter syslog-ng counter summary from SC4S Manager",
        "# TYPE sc4s_manager_syslogng_counter counter",
    ]
    for k, v in sorted((metrics.get("summary") or {}).items()):
        try:
            n = int(v)
        except Exception:
            continue
        lines.append(f"sc4s_manager_syslogng_{k} {n}")
    lines.extend([
        "# HELP sc4s_manager_syslogng_source_rows Number of raw syslog-ng stat rows by source name",
        "# TYPE sc4s_manager_syslogng_source_rows gauge",
    ])
    for source, count in sorted((metrics.get("by_source") or {}).items()):
        lines.append(f'sc4s_manager_syslogng_source_rows{{source="{prom_escape(source)}"}} {int(count)}')
    lines.append(f"sc4s_manager_metrics_up {1 if metrics.get('ok') else 0}")
    return "\n".join(lines) + "\n"


def tls_inventory() -> dict[str, Any]:
    ensure_dirs()
    env = parse_env()
    cert = TLS_DIR / "server.pem"
    key = TLS_DIR / "server.key"
    ca_files = sorted([p for p in TLS_DIR.iterdir() if p.is_file() and p.name not in {"server.pem", "server.key"}]) if TLS_DIR.exists() else []
    port = env.get("SC4S_SOURCE_LISTEN_TLS_PORT") or env.get("SC4S_LISTEN_DEFAULT_TLS_PORT") or "6514"
    enabled = env.get("SC4S_SOURCE_TLS_ENABLE", "no").lower() in {"yes","true","1","y","t"}
    active = listener_active(port, "tcp")
    problems = []
    if not enabled:
        problems.append("TLS source is not enabled")
    if not cert.exists():
        problems.append("missing certificate")
    if not key.exists():
        problems.append("missing private key")
    if enabled and cert.exists() and key.exists() and not active:
        problems.append("TLS desired but listener is not active")
    return {
        "enabled": enabled,
        "expected_port": str(port),
        "listener_active": active,
        "ready": enabled and cert.exists() and key.exists() and active,
        "cert": {"path": str(cert), "exists": cert.exists(), "size": cert.stat().st_size if cert.exists() else 0, "fingerprint": cert_fingerprint(cert), **cert_expiry(cert)},
        "key": {"path": str(key), "exists": key.exists(), "size": key.stat().st_size if key.exists() else 0},
        "ca_files": [{"name": p.name, "size": p.stat().st_size} for p in ca_files],
        "problems": problems,
    }


def _write_temp_text(content: str, suffix: str) -> Path:
    fd, name = tempfile.mkstemp(prefix="sc4s-manager-", suffix=suffix)
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return Path(name)


def validate_pem_bundle(cert: str, key: str, ca: str = "") -> None:
    if "BEGIN CERTIFICATE" not in cert:
        raise ValueError("certificate must be PEM encoded")
    if "BEGIN" not in key or "PRIVATE KEY" not in key:
        raise ValueError("private key must be PEM encoded")
    cert_tmp = _write_temp_text(cert, ".crt")
    key_tmp = _write_temp_text(key, ".key")
    try:
        c1 = run(["openssl", "x509", "-noout", "-modulus", "-in", str(cert_tmp)], timeout=10)
        k1 = run(["openssl", "rsa", "-noout", "-modulus", "-in", str(key_tmp)], timeout=10)
        if not c1["ok"] or not k1["ok"]:
            raise ValueError("certificate or private key failed openssl validation")
        if c1["stdout"].strip() and k1["stdout"].strip() and c1["stdout"].strip() != k1["stdout"].strip():
            raise ValueError("certificate and private key do not match")
    finally:
        cert_tmp.unlink(missing_ok=True)
        key_tmp.unlink(missing_ok=True)


def install_tls_bundle(cert: str, key: str, ca: str, actor: str) -> dict[str, Any]:
    validate_pem_bundle(cert, key, ca)
    ensure_dirs()
    with _lock:
        for p in [TLS_DIR / "server.pem", TLS_DIR / "server.key", TLS_DIR / "ca.pem"]:
            if p.exists():
                backup(p, actor)
        atomic_write(TLS_DIR / "server.pem", cert)
        atomic_write(TLS_DIR / "server.key", key)
        os.chmod(TLS_DIR / "server.key", 0o600)
        if ca.strip():
            if "BEGIN CERTIFICATE" not in ca:
                raise ValueError("CA bundle must be PEM encoded")
            atomic_write(TLS_DIR / "ca.pem", ca)
        b = backup(ENV_FILE, actor) if ENV_FILE.exists() else None
        atomic_write(ENV_FILE, render_env({"SC4S_SOURCE_TLS_ENABLE": "yes", "SC4S_TLS": "/etc/syslog-ng/tls"}))
    audit("install_tls_bundle", actor, {"cert": str(TLS_DIR / "server.pem"), "key": str(TLS_DIR / "server.key"), "ca": bool(ca.strip()), "backup": str(b) if b else None})
    return {"tls": tls_inventory(), "backup": str(b) if b else None, "restart_required": True}


def delete_tls_bundle(actor: str) -> dict[str, Any]:
    removed = []
    with _lock:
        for p in [TLS_DIR / "server.pem", TLS_DIR / "server.key", TLS_DIR / "ca.pem"]:
            if p.exists():
                backup(p, actor)
                p.unlink()
                removed.append(str(p))
        b = backup(ENV_FILE, actor) if ENV_FILE.exists() else None
        atomic_write(ENV_FILE, render_env({"SC4S_SOURCE_TLS_ENABLE": None}))
    audit("delete_tls_bundle", actor, {"removed": removed, "backup": str(b) if b else None})
    return {"removed": removed, "backup": str(b) if b else None, "restart_required": True}


def _counter_groups(rows: list[dict[str, Any]], group_key: str) -> dict[str, dict[str, int]]:
    groups: dict[str, dict[str, int]] = {}
    for row in rows:
        name = str(row.get(group_key) or "unknown")
        typ = str(row.get("Type") or "unknown")
        try:
            n = int(row.get("Number") or 0)
        except Exception:
            n = 0
        bucket = groups.setdefault(name, {})
        bucket[typ] = bucket.get(typ, 0) + n
    return groups


def _matches_metric_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    names = {
        "source_name": "SourceName",
        "source_id": "SourceId",
        "source_instance": "SourceInstance",
        "state": "State",
        "type": "Type",
    }
    for user_key, row_key in names.items():
        expected = str(filters.get(user_key, "")).strip().lower()
        if expected and str(row.get(row_key, "")).lower() != expected:
            return False
    search = str(filters.get("search", "")).strip().lower()
    if search:
        haystack = " ".join(str(v) for v in row.values()).lower()
        if search not in haystack:
            return False
    return True


def syslog_ng_metrics(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    r = control_request("metrics")
    if not r.get("ok"):
        return {"ok": False, "error": r.get("stderr") or r.get("error", "metrics failed"), "rows": [], "summary": {}}
    rows = []
    reader = csv.DictReader(r.get("stdout", "").splitlines(), delimiter=";")
    summary: dict[str, int] = {"processed": 0, "dropped": 0, "discarded": 0, "queued": 0, "written": 0, "matched": 0, "not_matched": 0, "connections": 0}
    by_source: dict[str, int] = {}
    for row in reader:
        try:
            n = int(row.get("Number") or 0)
        except Exception:
            n = 0
        row["Number"] = n
        rows.append(row)
        typ = row.get("Type", "")
        if typ in summary:
            summary[typ] += n
        sn = row.get("SourceName", "unknown")
        by_source[sn] = by_source.get(sn, 0) + 1
    try:
        limit = int(filters.get("limit", 5000))
    except Exception:
        limit = 5000
    limit = max(1, min(limit, 5000))
    filtered = [row for row in rows if _matches_metric_filters(row, filters)]
    return {
        "ok": True,
        "row_count": len(rows),
        "filtered_row_count": len(filtered),
        "summary": summary,
        "summaries": {
            "by_source_name": _counter_groups(rows, "SourceName"),
            "by_source_id": _counter_groups(rows, "SourceId"),
            "by_type": {k: v for k, v in summary.items() if v},
            "by_state": _counter_groups(rows, "State"),
        },
        "by_source": by_source,
        "filters": {k: v for k, v in filters.items() if v not in {"", None}},
        "rows": filtered[:limit],
    }


def normalize_option(opt: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    item = dict(opt)
    key = item["key"]
    item.setdefault("label", key)
    item.setdefault("category", "advanced")
    item.setdefault("type", "secret" if SECRET_KEY_RE.search(key) else "string")
    item.setdefault("description", "SC4S configuration option.")
    item.setdefault("docs", "configuration/")
    item.setdefault("secret", bool(SECRET_KEY_RE.search(key)))
    item.setdefault("restart_required", item.get("apply_mode") != "reloadable")
    item.setdefault("apply_mode", "restart_required" if item.get("restart_required", True) else "reloadable")
    if item["docs"] and str(item["docs"]).startswith(("configuration", "destinations", "troubleshooting", "sources", "architecture")):
        item["docs_url"] = f"{SC4S_DOCS_BASE}/{item['docs']}"
    item["current"] = "[REDACTED]" if item.get("secret") and key in env else env.get(key, item.get("default"))
    item["set"] = key in env
    return item


def sc4s_version_status() -> dict[str, Any]:
    status = control_request("status")
    running = None
    image = None
    if status.get("ok"):
        s = status.get("status", {})
        running = s.get("image_version")
        image = s.get("image")
    drift = bool(running and running != SUPPORTED_SC4S_VERSION)
    return {
        "supported_sc4s_version": SUPPORTED_SC4S_VERSION,
        "running_sc4s_version": running,
        "running_sc4s_image": image,
        "version_drift": {
            "drift": drift,
            "message": "" if not drift else f"Running SC4S {running} differs from Manager-supported SC4S {SUPPORTED_SC4S_VERSION}",
        },
    }


def sc4s_version_status_from_docker(status: dict[str, Any]) -> dict[str, Any]:
    running = status.get("image_version")
    image = status.get("image")
    drift = bool(running and running != SUPPORTED_SC4S_VERSION)
    return {
        "supported_sc4s_version": SUPPORTED_SC4S_VERSION,
        "running_sc4s_version": running,
        "running_sc4s_image": image,
        "version_drift": {
            "drift": drift,
            "message": "" if not drift else f"Running SC4S {running} differs from Manager-supported SC4S {SUPPORTED_SC4S_VERSION}",
        },
    }


def option_schema() -> dict[str, Any]:
    env = parse_env()
    options = []
    known = {o["key"] for o in OPTION_REGISTRY}
    for opt in OPTION_REGISTRY:
        options.append(normalize_option(opt, env))
    for k, v in sorted(env.items()):
        if k not in known:
            options.append(normalize_option({"key": k, "label": k, "category": "advanced", "description": "Discovered SC4S environment option not yet in the curated registry.", "current": v, "set": True}, env))
    meta = sc4s_version_status()
    return {"version": APP_VERSION, **meta, "options": options, "categories": sorted({o.get("category", "advanced") for o in options})}


def validate_config() -> dict[str, Any]:
    syntax = control_request("validate")
    tls = tls_inventory()
    env = parse_env()
    tls_enabled = env.get("SC4S_SOURCE_TLS_ENABLE", "no").lower() in {"yes","true","1","y","t"}
    tls_ok = tls["ready"] if tls_enabled else True
    ok = bool(syntax.get("ok") and tls_ok)
    return {"ok": ok, "syntax": {"ok": bool(syntax.get("ok")), "stdout": syntax.get("stdout", ""), "stderr": syntax.get("stderr", ""), "code": syntax.get("code", 0 if syntax.get("ok") else 1)}, "tls": tls, "checked_at": now()}


def backups() -> list[dict[str, Any]]:
    ensure_dirs()
    return [{"name": p.name, "path": str(p), "size": p.stat().st_size, "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat()} for p in sorted(BACKUP_DIR.glob("*.bak"), key=lambda x: x.stat().st_mtime, reverse=True)]


def restore_backup(name: str, actor: str) -> dict[str, Any]:
    ensure_dirs()
    safe = Path(name).name
    src = resolved_under(BACKUP_DIR / safe, (BACKUP_DIR,), label="backup name")
    if not src.exists() or src.suffix != ".bak":
        raise ValueError("backup not found")
    # Backup filenames are relpath.timestamp.actor.bak where / became __.
    dest = backup_target_from_name(safe)
    if dest.exists():
        backup(dest, actor)
    atomic_write(dest, src.read_text())
    audit("restore_backup", actor, {"backup": str(src), "dest": str(dest)})
    return {"backup": str(src), "restored_to": str(dest), "restart_required": True}


def recent_log_findings(lines: int = 80) -> dict[str, Any]:
    try:
        requested = max(1, min(int(lines), 500))
    except Exception:
        requested = 80
    resp = control_request("logs", lines=requested)
    raw_lines = resp.get("stdout", "").splitlines()[-requested:] if resp.get("ok") else []
    warnings = []
    errors = []
    warning_re = re.compile(r"\b(warn|warning)\b", re.I)
    error_re = re.compile(r"\b(err|error|critical|fatal)\b", re.I)
    for line in raw_lines:
        safe = redact_log_line(line)
        if error_re.search(line):
            errors.append(safe)
        elif warning_re.search(line):
            warnings.append(safe)
    return {
        "ok": bool(resp.get("ok")),
        "provider": "narrow-control",
        "line_count": len(raw_lines),
        "warning_count": len(warnings),
        "error_count": len(errors),
        "warnings": warnings[-50:],
        "errors": errors[-50:],
        "error": None if resp.get("ok") else resp.get("stderr") or resp.get("error", "logs failed"),
    }


def service_stats() -> dict[str, Any]:
    env = parse_env()
    docker = docker_status()
    version = sc4s_version_status_from_docker(docker)
    log_findings = recent_log_findings(80)
    ss = run(["ss", "-lntup"], timeout=10)
    du = run(["du", "-sh", str(ROOT)], timeout=10)
    return {
        "version": APP_VERSION,
        **version,
        "time": now(),
        "docker": docker,
        "control_provider": {
            "provider": "narrow-control",
            "ok": not bool(docker.get("error")),
            "health": docker.get("health"),
            "socket": CONTROL_SOCKET,
        },
        "health": health_probe(),
        "ports": port_summary(env),
        "tls": tls_inventory(),
        "metrics_summary": syslog_ng_metrics().get("summary", {}),
        "csv_counts": {name: count_csv(path) for name, path in CSV_FILES.items()},
        "disk": du["stdout"].strip(),
        "listening": [line for line in ss["stdout"].splitlines() if "514" in line or "6514" in line or "8090" in line or "8080" in line],
        "log_findings": log_findings,
        "recent_logs": [redact_log_line(line) for line in control_request("logs", lines=80).get("stdout", "").splitlines()[-80:]],
    }


def port_summary(env: dict[str, str]) -> dict[str, Any]:
    state = load_state()
    out = {}
    for kind, key in PORT_KEYS.items():
        live_key = LISTEN_KEYS.get(kind)
        desired_port = env.get(live_key) or env.get(key)
        active = listener_active(desired_port, "tcp" if kind in {"tcp", "tls"} else "udp") if desired_port else False
        out[kind] = {"key": key, "listen_key": live_key, "enabled": bool(desired_port), "port": desired_port, "listener_active": active, "last_disabled_port": state.get("disabled_ports", {}).get(kind)}
    return out


def count_csv(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for row in csv.reader(path.open()) if row and not str(row[0]).startswith("#"))


def read_csv(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return [row for row in csv.reader(f) if row]


def append_csv(path: Path, row: list[str], actor: str) -> None:
    with _lock:
        if path.exists():
            backup(path, actor)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = read_csv(path)
        if row not in rows:
            with path.open("a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(row)


def remove_csv_rows(path: Path, predicate: Callable[[list[str]], bool], actor: str) -> int:
    with _lock:
        rows = read_csv(path)
        kept = [row for row in rows if not predicate(row)]
        removed = len(rows) - len(kept)
        if removed:
            if path.exists():
                backup(path, actor)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(kept)
        return removed


def remove_filter_conf(path: Path, filter_id: str, actor: str) -> bool:
    with _lock:
        if not path.exists():
            return False
        backup(path, actor)
        lines = [line for line in path.read_text().splitlines() if not line.strip().startswith(f"filter {filter_id} ")]
        atomic_write(path, "\n".join(lines).rstrip() + ("\n" if lines else ""))
        return True


def merge_filter_conf(path: Path, filter_id: str, expr: str, actor: str) -> None:
    """Ensure SC4S selector-context filters exist where add-contextual-data loads them.

    SC4S loads source selector filters for vendor_product_by_source.csv and
    compliance_meta_by_source.csv from local/context/*.conf, not only from
    local/config/filters/*.conf. Keeping the per-filter file is useful for human
    browsing, but these context conf files are the effective runtime path.
    """
    line = f"filter {filter_id} {{ {expr}; }};"
    with _lock:
        if path.exists():
            backup(path, actor)
            lines = [existing for existing in path.read_text().splitlines() if not existing.strip().startswith(f"filter {filter_id} ")]
        else:
            lines = []
        lines.append(line)
        atomic_write(path, "\n".join(lines).rstrip() + "\n")


def restore_mutation_snapshot(snapshot: dict[str, Any]) -> None:
    env_text = snapshot.get("env_text")
    if env_text is None:
        ENV_FILE.unlink(missing_ok=True)
    else:
        atomic_write(ENV_FILE, env_text)

    local_copy = snapshot.get("local_copy")
    # Restore contents in place. LOCAL_ROOT is bind-mounted into the SC4S
    # container; removing the directory itself would replace its inode and
    # silently detach the runtime's view of local config until the container
    # is recreated, so only its children may be replaced.
    LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
    for child in LOCAL_ROOT.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    if local_copy and Path(local_copy).exists():
        for child in Path(local_copy).iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.copytree(child, LOCAL_ROOT / child.name)
            else:
                shutil.copy2(child, LOCAL_ROOT / child.name)
    else:
        (LOCAL_ROOT / "context").mkdir(parents=True, exist_ok=True)
        (LOCAL_ROOT / "config" / "filters").mkdir(parents=True, exist_ok=True)

    state_text = snapshot.get("state_text")
    if state_text is None:
        STATE_FILE.unlink(missing_ok=True)
    else:
        atomic_write(STATE_FILE, state_text)


def mutation_snapshot() -> dict[str, Any]:
    ensure_dirs()
    snap_dir = Path(tempfile.mkdtemp(prefix="mutation-snapshot.", dir=str(STATE_DIR)))
    local_copy = snap_dir / "local"
    if LOCAL_ROOT.exists():
        shutil.copytree(LOCAL_ROOT, local_copy)
    return {
        "dir": snap_dir,
        "local_copy": local_copy if local_copy.exists() else None,
        "env_text": ENV_FILE.read_text() if ENV_FILE.exists() else None,
        "state_text": STATE_FILE.read_text() if STATE_FILE.exists() else None,
    }


def cleanup_mutation_snapshot(snapshot: dict[str, Any]) -> None:
    snap_dir = snapshot.get("dir")
    if snap_dir:
        shutil.rmtree(snap_dir, ignore_errors=True)


def rollback_if_invalid(validation: dict[str, Any], snapshot: dict[str, Any], actor: str, action: str) -> bool:
    if validation.get("ok"):
        cleanup_mutation_snapshot(snapshot)
        return False
    restore_mutation_snapshot(snapshot)
    cleanup_mutation_snapshot(snapshot)
    audit(f"{action}_rollback", actor, {"validation": validation, "rolled_back": True})
    return True


def validate_filter(filter_name: str) -> str:
    if not FILTER_RE.match(filter_name):
        raise ValueError("filter name must match ^[A-Za-z0-9_]{1,64}$")
    return filter_name


def validate_network_or_host(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("source match is required")
    try:
        if "/" in value:
            ipaddress.ip_network(value, strict=False)
        else:
            ipaddress.ip_address(value)
        return value
    except ValueError:
        if not re.match(r"^[A-Za-z0-9_.:*?-]{1,120}$", value):
            raise ValueError("source match must be an IP/CIDR or safe hostname/glob")
        return value


def add_service(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    filter_name = validate_filter(payload.get("filter", ""))
    source_match = validate_network_or_host(payload.get("source", ""))
    vendor_product = payload.get("vendor_product", "").strip()
    index = payload.get("index", "").strip()
    compliance = payload.get("compliance", "").strip()
    if vendor_product and not SAFE_NAME_RE.match(vendor_product):
        raise ValueError("vendor_product contains unsafe characters")
    if index and not SAFE_NAME_RE.match(index):
        raise ValueError("index contains unsafe characters")
    filt_file = LOCAL_ROOT / "config" / "filters" / f"{filter_name}.conf"
    filter_id = f"f_{filter_name}"
    expr = f"netmask(\"{source_match}\")" if re.match(r"^[0-9a-fA-F:.]+(/\d+)?$", source_match) else f"host(\"{source_match}\" type(glob))"
    conf = f"filter {filter_id} {{ {expr}; }};\n"
    with _lock:
        if filt_file.exists():
            backup(filt_file, actor)
        atomic_write(filt_file, conf)
        if vendor_product:
            merge_filter_conf(LOCAL_ROOT / "context" / "vendor_product_by_source.conf", filter_id, expr, actor)
            append_csv(CSV_FILES["vendor_product"], [filter_id, "sc4s_vendor_product", vendor_product], actor)
        if index:
            append_csv(CSV_FILES["splunk_metadata"], [filter_id, ".splunk.index", index], actor)
            # Source-scoped Splunk index overrides are evaluated by SC4S through
            # compliance_meta_by_source, whose selector is the same filter id.
            # Keep the legacy splunk_metadata row for export compatibility, but
            # write the effective runtime row here as well.
            merge_filter_conf(LOCAL_ROOT / "context" / "compliance_meta_by_source.conf", filter_id, expr, actor)
            append_csv(CSV_FILES["compliance_meta"], [filter_id, ".splunk.index", index], actor)
        if compliance:
            merge_filter_conf(LOCAL_ROOT / "context" / "compliance_meta_by_source.conf", filter_id, expr, actor)
            append_csv(CSV_FILES["compliance_meta"], [filter_id, "fields.compliance", compliance], actor)
    result = {"filter": filter_id, "source": source_match, "vendor_product": vendor_product, "index": index, "compliance": compliance, "restart_required": True}
    audit("add_service", actor, result)
    return result




def normalize_dest_id(value: str) -> str:
    v = re.sub(r"[^A-Za-z0-9_]", "_", (value or "").upper()).strip("_")[:32]
    if not v or not re.match(r"^[A-Z][A-Z0-9_]{0,31}$", v):
        raise ValueError("destination id must start with a letter and contain only letters, numbers, and underscore")
    return v


def destination_inventory() -> dict[str, Any]:
    env = parse_env()
    found: dict[tuple[str, str], dict[str, Any]] = {}
    patterns = [
        ("hec", re.compile(r"^SC4S_DEST_SPLUNK_HEC_([A-Z0-9_]+)_(URL|TOKEN|MODE|TLS_VERIFY|HTTP_COMPRESSION)$")),
        ("syslog", re.compile(r"^SC4S_DEST_SYSLOG_([A-Z0-9_]+)_(HOST|PORT|TRANSPORT|MODE|IETF)$")),
        ("bsd", re.compile(r"^SC4S_DEST_BSD_([A-Z0-9_]+)_(HOST|PORT|TRANSPORT|MODE)$")),
    ]
    for key, value in env.items():
        for kind, pat in patterns:
            m = pat.match(key)
            if not m:
                continue
            did, field = m.group(1), m.group(2).lower()
            rec = found.setdefault((kind, did), {"kind": kind, "id": did})
            rec[field] = "[REDACTED]" if field == "token" else value
    if ("hec", "DEFAULT") not in found:
        found[("hec", "DEFAULT")] = {"kind": "hec", "id": "DEFAULT", "url": env.get("SC4S_DEST_SPLUNK_HEC_DEFAULT_URL"), "token": "[REDACTED]" if env.get("SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN") else None, "tls_verify": env.get("SC4S_DEST_SPLUNK_HEC_DEFAULT_TLS_VERIFY", "yes")}
    return {"supported_sc4s_version": SUPPORTED_SC4S_VERSION, "destinations": sorted(found.values(), key=lambda x: (x.get("kind",""), x.get("id","")))}


def selector_content(vendor_product: str, dest_ref: str) -> str:
    vp = vendor_product.strip()
    if not SAFE_NAME_RE.match(vp):
        raise ValueError("selector vendor_product contains unsafe characters")
    return (
        f"application sc4s-lp-{vp}_{dest_ref}[sc4s-lp-dest-select-{dest_ref}] {{\n"
        "    filter {\n"
        f"        '${{fields.sc4s_vendor_product}}' eq \"{vp}\"\n"
        "    };\n"
        "};\n"
    )


def configure_destination(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    kind = str(payload.get("kind", "")).lower()
    did = normalize_dest_id(str(payload.get("id", "DEFAULT")))
    updates: dict[str, str] = {}
    selector_file = None
    snapshot: dict[str, Any] | None = None
    if kind == "hec":
        url = str(payload.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("HEC url must start with http:// or https://")
        mode = str(payload.get("mode", "GLOBAL")).upper() if payload.get("mode") else "GLOBAL"
        if mode not in {"GLOBAL", "SELECT"}:
            raise ValueError("mode must be GLOBAL or SELECT")
        prefix = f"SC4S_DEST_SPLUNK_HEC_{did}"
        updates[f"{prefix}_URL"] = url
        if payload.get("token"):
            updates[f"{prefix}_TOKEN"] = str(payload.get("token"))
        if payload.get("mode"):
            updates[f"{prefix}_MODE"] = mode
        if payload.get("tls_verify"):
            updates[f"{prefix}_TLS_VERIFY"] = str(payload.get("tls_verify"))
        if payload.get("http_compression"):
            updates[f"{prefix}_HTTP_COMPRESSION"] = str(payload.get("http_compression"))
    elif kind in {"syslog", "bsd"}:
        host = str(payload.get("host", "")).strip()
        if not validate_network_or_host(host):
            raise ValueError("invalid destination host")
        port = validate_port(payload.get("port", 601 if kind == "syslog" else 514))
        transport = str(payload.get("transport", "tcp")).lower()
        if transport not in {"tcp", "udp", "tls"}:
            raise ValueError("transport must be tcp, udp, or tls")
        mode = str(payload.get("mode", "GLOBAL")).upper()
        if mode not in {"GLOBAL", "SELECT"}:
            raise ValueError("mode must be GLOBAL or SELECT")
        prefix = f"SC4S_DEST_{kind.upper()}_{did}"
        updates[f"{prefix}_HOST"] = host
        updates[f"{prefix}_PORT"] = str(port)
        updates[f"{prefix}_TRANSPORT"] = transport
        updates[f"{prefix}_MODE"] = mode
        if kind == "syslog" and payload.get("ietf") is not None:
            updates[f"{prefix}_IETF"] = str(payload.get("ietf"))
        if mode == "SELECT":
            vp = str(payload.get("selector_vendor_product", "")).strip()
            dest_ref = f"d_{kind}_{did.lower()}"
            selector_dir = LOCAL_ROOT / "config" / "app_parsers" / "selectors"
            selector_file = selector_dir / f"sc4s-lp-{vp}_{dest_ref}.conf"
            snapshot = mutation_snapshot()
            selector_dir.mkdir(parents=True, exist_ok=True)
            atomic_write(selector_file, selector_content(vp, dest_ref))
    else:
        raise ValueError("destination kind must be hec, syslog, or bsd")
    with _lock:
        if snapshot is None:
            snapshot = mutation_snapshot()
        b = backup(ENV_FILE, actor) if ENV_FILE.exists() else None
        atomic_write(ENV_FILE, render_env(updates))
    validation = validate_config()
    rolled_back = rollback_if_invalid(validation, snapshot, actor, "configure_destination")
    control = {"ok": True, "skipped": True}
    if payload.get("apply", False) and not rolled_back:
        control = restart_sc4s(actor)
    audit("configure_destination", actor, {"kind": kind, "id": did, "updates": redact(updates), "selector": str(selector_file) if selector_file else None, "ok": bool(validation.get("ok"))})
    safe_updates = {k: ("[REDACTED]" if SECRET_KEY_RE.search(k) else v) for k, v in updates.items()}
    return {"ok": bool(validation.get("ok") and control.get("ok", True)), "kind": kind, "id": did, "apply_mode": "restart_required", "updates": safe_updates, "selector": str(selector_file) if selector_file else None, "backup": str(b) if b else None, "validation": validation, "control": control}

def source_catalog() -> dict[str, Any]:
    sources = []
    for src in SOURCE_CATALOG:
        item = dict(src)
        if item.get("docs"):
            item["docs_url"] = f"{SC4S_DOCS_BASE}/{item['docs']}"
        sources.append(item)
    return {"supported_sc4s_version": SUPPORTED_SC4S_VERSION, "sources": sources}


def source_inventory() -> dict[str, Any]:
    filters_dir = LOCAL_ROOT / "config" / "filters"
    csv_rows = {key: read_csv(path) for key, path in CSV_FILES.items()}

    def csv_value(table: str, filter_id: str, field: str) -> str:
        for row in csv_rows.get(table, []):
            if len(row) >= 3 and row[0] == filter_id and row[1] == field:
                return row[2]
        return ""

    sources: list[dict[str, Any]] = []
    if filters_dir.exists():
        for path in sorted(filters_dir.glob("*.conf")):
            name = path.stem
            filter_id = f"f_{name}"
            match = re.search(r'netmask\("([^"]+)"\)|host\("([^"]+)"', path.read_text(errors="replace"))
            sources.append({
                "name": name,
                "filter": filter_id,
                "source": (match.group(1) or match.group(2)) if match else "",
                "vendor_product": csv_value("vendor_product", filter_id, "sc4s_vendor_product"),
                "index": csv_value("splunk_metadata", filter_id, ".splunk.index") or csv_value("compliance_meta", filter_id, ".splunk.index"),
                "compliance": csv_value("compliance_meta", filter_id, "fields.compliance"),
                "path": str(path.relative_to(LOCAL_ROOT)),
                "apply_mode": "reloadable",
            })
    return {"sources": sources}


def source_test_instructions(source: str, host: str = "<sc4s-host>", tls_port: str = "6514") -> dict[str, str]:
    safe_marker = re.sub(r"[^A-Za-z0-9_.-]", "_", source or "sc4s_source")[:80]
    return {
        "udp": f"logger -n {host} -P 514 -d -t {safe_marker} 'SC4S_MANAGER_SOURCE_TEST_UDP {safe_marker}'",
        "tcp": f"printf '<134>1 2026-01-01T00:00:00Z testhost {safe_marker} - - SC4S_MANAGER_SOURCE_TEST_TCP {safe_marker}\n' | nc {host} 514",
        "tls": f"printf '<134>1 2026-01-01T00:00:00Z testhost {safe_marker} - - SC4S_MANAGER_SOURCE_TEST_TLS {safe_marker}\n' | openssl s_client -quiet -connect {host}:{tls_port}",
        "splunk": f"Search Splunk for SC4S_MANAGER_SOURCE_TEST_* and sc4s_vendor_product={safe_marker} or the configured vendor_product/index.",
    }


def onboard_source(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    name = validate_filter(str(payload.get("name") or payload.get("filter") or ""))
    vendor_product = str(payload.get("vendor_product", "")).strip()
    known = {s["vendor_product"] for s in SOURCE_CATALOG}
    if vendor_product and vendor_product not in known and not SAFE_NAME_RE.match(vendor_product):
        raise ValueError("unknown or unsafe vendor_product")
    snapshot = mutation_snapshot()
    result = add_service({
        "filter": name,
        "source": payload.get("source", ""),
        "vendor_product": vendor_product,
        "index": payload.get("index", ""),
        "compliance": payload.get("compliance", ""),
    }, actor)
    validation = validate_config()
    rolled_back = rollback_if_invalid(validation, snapshot, actor, "onboard_source")
    control = {"ok": True, "skipped": True}
    if payload.get("apply", False) and not rolled_back:
        control = reload_sc4s(actor)
    out = {"ok": bool(validation.get("ok") and control.get("ok", True)), "apply_mode": "reloadable", "service": result, "validation": validation, "control": control, "test_instructions": source_test_instructions(vendor_product or name)}
    audit("onboard_source", actor, {"filter": name, "vendor_product": vendor_product, "index": payload.get("index", ""), "apply": bool(payload.get("apply", False)), "ok": out["ok"]})
    return out


def delete_source(name: str, actor: str) -> dict[str, Any]:
    filter_name = validate_filter(name.removeprefix("f_"))
    filter_id = f"f_{filter_name}"
    filt_file = LOCAL_ROOT / "config" / "filters" / f"{filter_name}.conf"
    removed_paths: list[str] = []
    snapshot = mutation_snapshot()
    with _lock:
        if filt_file.exists():
            backup(filt_file, actor)
            filt_file.unlink()
            removed_paths.append(str(filt_file))
    removed_rows = {
        key: remove_csv_rows(path, lambda row, fid=filter_id: bool(row and row[0] == fid), actor)
        for key, path in CSV_FILES.items()
    }
    removed_filters = {
        "vendor_product_by_source": remove_filter_conf(LOCAL_ROOT / "context" / "vendor_product_by_source.conf", filter_id, actor),
        "compliance_meta_by_source": remove_filter_conf(LOCAL_ROOT / "context" / "compliance_meta_by_source.conf", filter_id, actor),
    }
    validation = validate_config()
    rollback_if_invalid(validation, snapshot, actor, "delete_source")
    out = {"ok": bool(validation.get("ok")), "filter": filter_id, "removed_paths": removed_paths, "removed_rows": removed_rows, "removed_filters": removed_filters, "validation": validation, "apply_mode": "reloadable"}
    audit("delete_source", actor, out)
    return out


def delete_destination(kind: str, dest_id: str, actor: str) -> dict[str, Any]:
    dest_kind = str(kind).lower()
    if dest_kind not in {"hec", "syslog", "bsd"}:
        raise ValueError("destination kind must be hec, syslog, or bsd")
    did = normalize_dest_id(dest_id)
    if dest_kind == "hec":
        prefix = f"SC4S_DEST_SPLUNK_HEC_{did}_"
        dest_ref = f"d_hec_{did.lower()}"
    else:
        prefix = f"SC4S_DEST_{dest_kind.upper()}_{did}_"
        dest_ref = f"d_{dest_kind}_{did.lower()}"
    env = parse_env()
    updates: dict[str, str | None] = {key: None for key in env if key.startswith(prefix)}
    selector_dir = LOCAL_ROOT / "config" / "app_parsers" / "selectors"
    removed_selectors: list[str] = []
    snapshot = mutation_snapshot()
    with _lock:
        b = backup(ENV_FILE, actor) if ENV_FILE.exists() else None
        if updates:
            atomic_write(ENV_FILE, render_env(updates))
        if selector_dir.exists():
            for selector in selector_dir.glob(f"*{dest_ref}.conf"):
                backup(selector, actor)
                selector.unlink()
                removed_selectors.append(str(selector))
    # Routes referencing this destination are no longer valid.
    state = load_state()
    routes = [route for route in state.get("routes", []) if not (route.get("destination_kind") == dest_kind and route.get("destination_id") == did)]
    if routes != state.get("routes", []):
        state["routes"] = routes
        save_state(state)
    validation = validate_config()
    rollback_if_invalid(validation, snapshot, actor, "delete_destination")
    out = {"ok": bool(validation.get("ok")), "kind": dest_kind, "id": did, "removed_env_keys": sorted(updates), "removed_selectors": removed_selectors, "backup": str(b) if b else None, "validation": validation, "apply_mode": "restart_required"}
    audit("delete_destination", actor, out)
    return out


def route_inventory() -> dict[str, Any]:
    state = load_state()
    return {"routes": state.get("routes", []) if isinstance(state.get("routes"), list) else []}


def upsert_route(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    route_id = validate_filter(str(payload.get("id", "")))
    source = validate_filter(str(payload.get("source", "")))
    pack = str(payload.get("pack") or payload.get("vendor_product") or "").strip()
    if not SAFE_NAME_RE.match(pack):
        raise ValueError("pack contains unsafe characters")
    dest_kind = str(payload.get("destination_kind", "hec")).lower()
    if dest_kind not in {"hec", "syslog", "bsd"}:
        raise ValueError("destination kind must be hec, syslog, or bsd")
    did = normalize_dest_id(str(payload.get("destination_id", "")))
    if dest_kind == "hec":
        dest_ref = f"d_hec_{did.lower()}"
    else:
        dest_ref = f"d_{dest_kind}_{did.lower()}"
    env = parse_env()
    prefix = f"SC4S_DEST_SPLUNK_HEC_{did}_" if dest_kind == "hec" else f"SC4S_DEST_{dest_kind.upper()}_{did}_"
    if not any(key.startswith(prefix) for key in env):
        raise ValueError("destination is not configured")
    if not (LOCAL_ROOT / "config" / "filters" / f"{source}.conf").exists():
        raise ValueError("source is not configured")
    selector_dir = LOCAL_ROOT / "config" / "app_parsers" / "selectors"
    selector_dir.mkdir(parents=True, exist_ok=True)
    selector_file = selector_dir / f"sc4s-lp-{pack}_{dest_ref}.conf"
    snapshot = mutation_snapshot()
    with _lock:
        if selector_file.exists():
            backup(selector_file, actor)
        atomic_write(selector_file, selector_content(pack, dest_ref))
    route = {"id": route_id, "source": source, "pack": pack, "destination_kind": dest_kind, "destination_id": did, "selector": str(selector_file), "apply_mode": "reloadable"}
    state = load_state()
    routes = [item for item in state.get("routes", []) if isinstance(item, dict) and item.get("id") != route_id]
    routes.append(route)
    state["routes"] = sorted(routes, key=lambda item: item.get("id", ""))
    save_state(state)
    validation = validate_config()
    rolled_back = rollback_if_invalid(validation, snapshot, actor, "upsert_route")
    control = {"ok": True, "skipped": True}
    if payload.get("apply", False) and not rolled_back:
        control = reload_sc4s(actor)
    out = {"ok": bool(validation.get("ok") and control.get("ok", True)), "route": route, "validation": validation, "control": control}
    audit("upsert_route", actor, out)
    return out


def delete_route(route_id: str, actor: str) -> dict[str, Any]:
    rid = validate_filter(route_id)
    state = load_state()
    routes = state.get("routes", []) if isinstance(state.get("routes"), list) else []
    target = next((route for route in routes if isinstance(route, dict) and route.get("id") == rid), None)
    if not target:
        raise ValueError("route not found")
    selector_dir = LOCAL_ROOT / "config" / "app_parsers" / "selectors"
    selector = resolved_under(Path(str(target.get("selector", ""))), (selector_dir,), label="route selector")
    removed_selectors: list[str] = []
    snapshot = mutation_snapshot()
    with _lock:
        if selector.exists() and selector.is_file():
            backup(selector, actor)
            selector.unlink()
            removed_selectors.append(str(selector))
    state["routes"] = [route for route in routes if not (isinstance(route, dict) and route.get("id") == rid)]
    save_state(state)
    validation = validate_config()
    rollback_if_invalid(validation, snapshot, actor, "delete_route")
    out = {"ok": bool(validation.get("ok")), "id": rid, "removed_selectors": removed_selectors, "validation": validation, "apply_mode": "reloadable"}
    audit("delete_route", actor, out)
    return out

def safe_editable_path(rel: str) -> Path:
    rel = unquote(rel).lstrip("/")
    candidate = LOCAL_ROOT / rel if not rel.startswith("local/") else ROOT / rel
    path = resolved_under(candidate, tuple(EDITABLE_ROOTS), label="editable path")
    if path.suffix not in EDITABLE_SUFFIXES:
        raise ValueError("file is not in an editable SC4S config path")
    return path


def save_config_file(rel: str, content: str, actor: str) -> dict[str, Any]:
    if len(content) > 256_000:
        raise ValueError("file too large")
    if "\x00" in content:
        raise ValueError("binary content is not allowed")
    path = safe_editable_path(rel)
    with _lock:
        b = backup(path, actor) if path.exists() else None
        atomic_write(path, content)
    audit("save_config_file", actor, {"path": str(path), "backup": str(b) if b else None})
    return {"path": str(path), "backup": str(b) if b else None, "restart_required": True}


def list_config_files() -> list[dict[str, Any]]:
    files = []
    for root in EDITABLE_ROOTS:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix in EDITABLE_SUFFIXES:
                files.append({"rel": str(p.relative_to(LOCAL_ROOT)), "size": p.stat().st_size, "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat()})
    return files


def export_template(name: str, actor: str) -> dict[str, Any]:
    ensure_dirs()
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name or "sc4s-template")[:80]
    target = TEMPLATE_DIR / f"{safe}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for root in EDITABLE_ROOTS:
            if root.exists():
                for p in root.rglob("*"):
                    if p.is_file() and p.suffix in EDITABLE_SUFFIXES:
                        z.write(p, str(p.relative_to(ROOT)))
        z.writestr("manifest.json", json.dumps({"name": name, "created_at": now(), "version": APP_VERSION}, indent=2))
    audit("export_template", actor, {"template": str(target)})
    return {"template": str(target), "size": target.stat().st_size}


def import_template(path: str, actor: str) -> dict[str, Any]:
    ensure_dirs()
    src = resolved_under(Path(path), (TEMPLATE_DIR,), label="template")
    if src.suffix != ".zip" or not src.exists():
        raise ValueError("template must be an existing zip in the template directory")
    if src.stat().st_size > 10_000_000:
        raise ValueError("template zip too large")
    restored = []
    with zipfile.ZipFile(src) as z:
        infos = z.infolist()
        if len(infos) > 200:
            raise ValueError("template has too many files")
        total = sum(i.file_size for i in infos)
        if total > 20_000_000 or any(i.file_size > 1_000_000 for i in infos):
            raise ValueError("template uncompressed content too large")
        for info in infos:
            member = info.filename
            if member == "manifest.json" or member.endswith("/"):
                continue
            dest = resolved_under(ROOT / member, tuple(EDITABLE_ROOTS), label="template member")
            if dest.suffix not in EDITABLE_SUFFIXES:
                raise ValueError(f"unsafe template member: {member}")
        for info in infos:
            member = info.filename
            if member == "manifest.json" or member.endswith("/"):
                continue
            dest = resolved_under(ROOT / member, tuple(EDITABLE_ROOTS), label="template member")
            if dest.exists():
                backup(dest, actor)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as f:
                atomic_write(dest, f.read().decode("utf-8"))
            restored.append(str(dest))
    audit("import_template", actor, {"template": str(src), "restored": restored})
    return {"template": str(src), "restored": restored, "restart_required": True}


def templates() -> list[dict[str, Any]]:
    ensure_dirs()
    return [{"path": str(p), "name": p.name, "size": p.stat().st_size, "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat()} for p in sorted(TEMPLATE_DIR.glob("*.zip"))]


def template_path_by_name(name: str) -> Path:
    ensure_dirs()
    safe = Path(name).name
    path = resolved_under(TEMPLATE_DIR / safe, (TEMPLATE_DIR,), label="template name")
    if path.suffix != ".zip" or not path.exists():
        raise ValueError("template not found")
    return path


def import_template_upload(name: str, content_b64: str, actor: str) -> dict[str, Any]:
    ensure_dirs()
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(name or "upload.zip").name)[:80]
    if not safe.endswith(".zip"):
        safe += ".zip"
    target = resolved_under(TEMPLATE_DIR / safe, (TEMPLATE_DIR,), label="template name")
    raw = base64.b64decode(content_b64, validate=True)
    if len(raw) > 10_000_000:
        raise ValueError("template upload too large")
    atomic_write_bytes(target, raw)
    audit("upload_template", actor, {"template": str(target), "size": len(raw)})
    return import_template(str(target), actor)


def products() -> dict[str, Any]:
    return {"vendor_products": read_csv(CSV_FILES["vendor_product"]), "splunk_metadata": read_csv(CSV_FILES["splunk_metadata"]), "compliance_meta": read_csv(CSV_FILES["compliance_meta"]), "host": read_csv(CSV_FILES["host"])}


def actor_from(handler: BaseHTTPRequestHandler) -> str:
    proxy_actor = handler.headers.get("X-Authentik-Username") or handler.headers.get("X-Forwarded-User")
    if proxy_actor:
        return proxy_actor
    if manual_token_authorized(handler):
        return "admin"
    return handler.client_address[0]


def parse_groups(header: str) -> set[str]:
    return {g.strip() for g in re.split(r"[,;|]", header or "") if g.strip()}


def proxy_authorized(handler: BaseHTTPRequestHandler) -> bool:
    if not (PROXY_SECRET and handler.headers.get("X-SC4S-Manager-Proxy") == PROXY_SECRET):
        return False
    required = {g.strip() for g in os.environ.get("SC4S_MANAGER_ADMIN_GROUPS", "").split(",") if g.strip()}
    if not required:
        return True
    return bool(required & parse_groups(handler.headers.get("X-Authentik-Groups", "")))


def origin_allowed(handler: BaseHTTPRequestHandler) -> bool:
    origin = handler.headers.get("Origin")
    if not origin:
        return True
    host = handler.headers.get("Host", "")
    return origin in {f"https://{host}", f"http://{host}"}


def _token_matches(candidate: str, expected: str) -> bool:
    return bool(candidate and expected and hmac.compare_digest(candidate, expected))


def _manual_session_token() -> str:
    if not MANUAL_LOGIN_TOKEN:
        return ""
    return hmac.new(
        MANUAL_LOGIN_TOKEN.encode("utf-8"),
        b"sc4s-manager-manual-session-v1",
        hashlib.sha256,
    ).hexdigest()


def _cookie_value(cookie_header: str, name: str) -> str:
    for part in (cookie_header or "").split(";"):
        key, sep, value = part.strip().partition("=")
        if sep and key == name:
            return unquote(value)
    return ""


def manual_token_authorized(handler: BaseHTTPRequestHandler) -> bool:
    if not MANUAL_LOGIN_TOKEN:
        return False
    auth = handler.headers.get("Authorization", "")
    if auth.lower().startswith("bearer ") and _token_matches(auth[7:].strip(), MANUAL_LOGIN_TOKEN):
        return True
    if _token_matches(handler.headers.get("X-SC4S-Manual-Token", ""), MANUAL_LOGIN_TOKEN):
        return True
    if _token_matches(_cookie_value(handler.headers.get("Cookie", ""), "sc4s_manual_session"), _manual_session_token()):
        return True
    qs = parse_qs(urlparse(handler.path).query)
    for key in ("token", "login_token"):
        if any(_token_matches(value, MANUAL_LOGIN_TOKEN) for value in qs.get(key, [])):
            return True
    return False


def manual_login_redirect(handler: BaseHTTPRequestHandler) -> bool:
    if not MANUAL_LOGIN_TOKEN:
        return False
    raw_target_has_controls = "\r" in handler.path or "\n" in handler.path
    parsed = urlparse(handler.path)
    qs = parse_qs(parsed.query)
    token = next((value for key in ("token", "login_token") for value in qs.get(key, [])), "")
    if not _token_matches(token, MANUAL_LOGIN_TOKEN):
        return False
    clean_items = [
        (key, value)
        for key, values in qs.items()
        if key not in {"token", "login_token"}
        for value in values
    ]
    target = parsed.path or "/"
    if clean_items:
        target = f"{target}?{urlencode(clean_items)}"
    if raw_target_has_controls or "\r" in target or "\n" in target:
        target = "/"
    handler.send_response(HTTPStatus.SEE_OTHER)
    handler.send_header("Location", target)
    handler.send_header(
        "Set-Cookie",
        "sc4s_manual_session=%s; Path=/; Max-Age=86400; HttpOnly; SameSite=Lax" % _manual_session_token(),
    )
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    return True


def redact_request_log_message(message: str) -> str:
    return re.sub(r"([?&](?:token|login_token)=)[^&\s]+", r"\1[REDACTED]", message)


def authorized(handler: BaseHTTPRequestHandler, unsafe: bool) -> bool:
    if handler.path.startswith("/health") or handler.path.startswith("/api/health"):
        return True
    if manual_token_authorized(handler):
        return (not unsafe) or origin_allowed(handler)
    if API_TOKEN and handler.headers.get("X-SC4S-Manager-Token") == API_TOKEN and handler.client_address[0] in {"127.0.0.1", "::1"}:
        return True
    if proxy_authorized(handler):
        return (not unsafe) or origin_allowed(handler)
    return False


def frontend_index_path() -> Path:
    return FRONTEND_DIST / "index.html"


def frontend_dist_available() -> bool:
    return frontend_index_path().is_file()


def _path_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def json_response(h: BaseHTTPRequestHandler, status: int, obj: Any) -> None:
    body = json.dumps(redact(obj), indent=2, sort_keys=True).encode()
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(body)))
    h.send_header("Cache-Control", "no-store")
    h.end_headers()
    h.wfile.write(body)


def _packs_module():
    import importlib.util
    module_path = Path(__file__).resolve().parent / "packs.py"
    spec = importlib.util.spec_from_file_location("sc4s_manager_packs_runtime", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load packs module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _exporters_module():
    import importlib.util
    module_path = Path(__file__).resolve().parent / "exporters.py"
    spec = importlib.util.spec_from_file_location("sc4s_manager_exporters_runtime", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load exporters module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _catalogue_module():
    import importlib.util
    module_path = Path(__file__).resolve().parent / "catalogue.py"
    spec = importlib.util.spec_from_file_location("sc4s_manager_catalogue_runtime", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load catalogue module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _library_module():
    import importlib.util
    module_path = Path(__file__).resolve().parent / "library.py"
    spec = importlib.util.spec_from_file_location("sc4s_manager_library_runtime", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load library module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sample_preview_module():
    import importlib.util
    module_path = Path(__file__).resolve().parent / "sample_preview.py"
    spec = importlib.util.spec_from_file_location("sc4s_manager_sample_preview_runtime", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load sample_preview module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_library_manager: Any | None = None


def _library_post_check() -> dict[str, Any]:
    stats = service_stats()
    return {
        "health": stats.get("health"),
        "ports": stats.get("ports"),
        "docker": stats.get("docker"),
        "control_provider": stats.get("control_provider"),
    }


def library_manager() -> Any:
    global _library_manager
    if _library_manager is None:
        mod = _library_module()
        _library_manager = mod.LibraryManager(
            root=ROOT,
            manager_root=MANAGER_ROOT,
            validate_config=validate_config,
            reload_sc4s=reload_sc4s,
            post_check=_library_post_check,
            audit=audit,
            apply_lock=_lock,
        )
    return _library_manager


def _runtime_state_module():
    import importlib.util
    module_path = Path(__file__).resolve().parent / "runtime_state.py"
    spec = importlib.util.spec_from_file_location("sc4s_manager_runtime_state_runtime", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load runtime_state module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def runtime_state_snapshot() -> dict[str, Any]:
    """Aggregate live runtime state for /api/runtime/state.

    Control daemon failures are captured as ok=false fields, never 500s.
    """
    mod = _runtime_state_module()
    status = control_request("status")
    metrics = control_request("metrics")
    listeners = control_request("listeners")
    warnings_resp = control_request("warnings")
    env = parse_env()
    return mod.build_runtime_state(
        control_status=status,
        control_metrics=metrics,
        control_listeners=listeners,
        control_warnings=warnings_resp,
        env=env,
        app_version=APP_VERSION,
        supported_sc4s_version=SUPPORTED_SC4S_VERSION,
        generated_at=now(),
    )


def pack_inventory() -> dict[str, Any]:
    mod = _packs_module()
    packs = [mod.pack_summary(p) for p in mod.load_packs(PACK_DIR)]
    return {"packs": packs, "count": len(packs)}


def pack_detail(pack_id: str) -> dict[str, Any]:
    mod = _packs_module()
    pack = mod.pack_by_id(mod.load_packs(PACK_DIR), pack_id)
    return mod.pack_summary(pack)


def _raw_pack(pack_id: str) -> dict[str, Any]:
    mod = _packs_module()
    return mod.pack_by_id(mod.load_packs(PACK_DIR), pack_id)


def pack_fixture_validation(pack_id: str) -> dict[str, Any]:
    mod = _packs_module()
    pack = _raw_pack(pack_id)
    return {"pack_id": pack_id, "results": mod.validate_pack_fixtures(pack, pack["pack_dir"])}


def pack_export_bundle(pack_id: str) -> tuple[str, bytes]:
    exporters = _exporters_module()
    pack = _raw_pack(pack_id)
    filename, data, _manifest = exporters.build_pack_export_bundle(pack, pack["pack_dir"])
    return filename, data


def catalogue_inventory(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    mod = _catalogue_module()
    return mod.catalogue_inventory(PACK_DIR, MANAGER_ROOT, filters)


def catalogue_detail(entry_id: str) -> dict[str, Any]:
    mod = _catalogue_module()
    return mod.catalogue_detail(entry_id, PACK_DIR, MANAGER_ROOT)


def library_sources() -> dict[str, Any]:
    return library_manager().sources()


def library_source_health(source_id: str = "official") -> dict[str, Any]:
    return library_manager().source_health(source_id)


def library_error_payload(exc: Exception) -> dict[str, Any]:
    mod = _library_module()
    classified = mod.classify_library_exception(exc)
    return {"error": classified["message"], "code": classified["code"], "next_action": classified["next_action"]}


def sync_library_source(source_id: str) -> dict[str, Any]:
    return library_manager().sync_source(source_id)


def library_catalogue(source_id: str = "official", filters: dict[str, Any] | None = None) -> dict[str, Any]:
    return library_manager().catalogue(source_id, filters)


def library_entry(source_id: str, entry_id: str, refresh: bool = False) -> dict[str, Any]:
    return library_manager().entry(source_id, entry_id, refresh=refresh)


def download_library_bundle(source_id: str, entry_id: str) -> dict[str, Any]:
    result = library_manager().download_bundle(source_id, entry_id, refresh=True)
    return {
        "ok": result.get("ok", True),
        "source_id": source_id,
        "entry_id": entry_id,
        "detail": result.get("detail"),
        "download": result.get("download"),
        "verification": result.get("verification"),
    }


def validate_library_import(source_id: str, entry_id: str, actor: str = "manager") -> dict[str, Any]:
    return library_manager().validate_import(source_id, entry_id, actor=actor)


def list_library_imports() -> dict[str, Any]:
    return library_manager().list_imports()


def apply_library_import(import_id: str, actor: str, apply: bool = True) -> dict[str, Any]:
    return library_manager().apply_import(import_id, actor=actor, apply=apply)


def _pack_subroute(path: str) -> tuple[str, str | None]:
    rest = path.removeprefix("/api/packs/")
    if rest.endswith("/export"):
        return unquote(rest[: -len("/export")]), "export"
    if rest.endswith("/validate-fixtures"):
        return unquote(rest[: -len("/validate-fixtures")]), "validate-fixtures"
    return unquote(rest), None


def _catalogue_subroute(path: str) -> str | None:
    rest = path.removeprefix("/api/catalogue/")
    if not rest:
        return None
    return unquote(rest)


def html_response(h: BaseHTTPRequestHandler, status: int, body: str) -> None:
    raw = body.encode()
    h.send_response(status)
    h.send_header("Content-Type", "text/html; charset=utf-8")
    h.send_header("Content-Length", str(len(raw)))
    h.send_header("Cache-Control", "no-store")
    h.end_headers()
    h.wfile.write(raw)


def text_response(h: BaseHTTPRequestHandler, status: int, body: str, ctype: str = "text/plain; charset=utf-8") -> None:
    raw = body.encode()
    h.send_response(status)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(raw)))
    h.send_header("Cache-Control", "no-store")
    h.end_headers()
    h.wfile.write(raw)


def binary_response(h: BaseHTTPRequestHandler, status: int, data: bytes, filename: str, ctype: str = "application/octet-stream") -> None:
    h.send_response(status)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(data)))
    h.send_header("Content-Disposition", 'attachment; filename="download.zip"')
    h.send_header("Cache-Control", "no-store")
    h.end_headers()
    h.wfile.write(data)


def file_response(h: BaseHTTPRequestHandler, status: int, path: Path, ctype: str, cache_control: str) -> None:
    data = path.read_bytes()
    h.send_response(status)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(data)))
    h.send_header("Cache-Control", cache_control)
    h.end_headers()
    h.wfile.write(data)


def static_asset_response(h: BaseHTTPRequestHandler, request_path: str) -> bool:
    if not request_path.startswith("/assets/"):
        return False
    rel = unquote(request_path.removeprefix("/assets/"))
    if not rel or rel.startswith("/"):
        json_response(h, 404, {"error": "not found"})
        return True
    asset = FRONTEND_DIST / "assets" / rel
    if not _path_inside(asset, FRONTEND_DIST / "assets") or not asset.is_file():
        json_response(h, 404, {"error": "not found"})
        return True
    ctype = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
    file_response(h, 200, asset, ctype, "public, max-age=31536000, immutable")
    return True


def frontend_response(h: BaseHTTPRequestHandler, request_path: str) -> bool:
    index = frontend_index_path()
    if index.is_file() and (request_path in ["/", "/index.html"] or frontend_dist_available()):
        file_response(h, 200, index, "text/html; charset=utf-8", "no-store")
        return True
    if request_path in ["/", "/index.html"]:
        data = INDEX_HTML.encode("utf-8")
        h.send_response(200)
        h.send_header("Content-Type", "text/html; charset=utf-8")
        h.send_header("Content-Length", str(len(data)))
        h.send_header("Cache-Control", "no-store")
        h.end_headers()
        h.wfile.write(data)
        return True
    return False


def read_body(h: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(h.headers.get("Content-Length", "0") or "0")
    if length > 1_000_000:
        raise ValueError("request too large")
    raw = h.rfile.read(length).decode("utf-8") if length else "{}"
    ctype = h.headers.get("Content-Type", "")
    if "application/json" in ctype:
        obj = json.loads(raw or "{}")
        if not isinstance(obj, dict):
            raise ValueError("JSON body must be an object")
        return obj
    return {k: v[-1] for k, v in parse_qs(raw).items()}



class Handler(BaseHTTPRequestHandler):
    server_version = "SC4SManager/" + APP_VERSION

    def log_message(self, fmt: str, *args: Any) -> None:
        print(json.dumps({"ts": now(), "remote": self.client_address[0], "msg": redact_request_log_message(fmt % args)}))

    def deny(self) -> None:
        json_response(self, HTTPStatus.FORBIDDEN, {"error": "forbidden", "hint": "provide a valid API token or access through a configured proxy"})

    def do_GET(self) -> None:
        try:
            if manual_login_redirect(self):
                return
            parsed = urlparse(self.path)
            if parsed.path == "/api/auth/status":
                return json_response(self, 200, {"authenticated": authorized(self, unsafe=False)})
            # Serve the frontend app and its assets without auth so the login page can render.
            # API routes below this block still require authentication.
            if static_asset_response(self, parsed.path):
                return
            if parsed.path not in ["/health", "/api/health"] and not parsed.path.startswith("/api/"):
                if parsed.path.startswith("/") and frontend_response(self, parsed.path):
                    return
            if not authorized(self, unsafe=False):
                return self.deny()
            if parsed.path in ["/health", "/api/health"]:
                return json_response(self, 200, {"status": "ok", "version": APP_VERSION, "sc4s": health_probe()})
            if parsed.path == "/api/stats":
                return json_response(self, 200, service_stats())
            if parsed.path == "/api/runtime/state":
                return json_response(self, 200, runtime_state_snapshot())
            if parsed.path == "/api/config":
                env = {k: ("[REDACTED]" if SECRET_KEY_RE.search(k) else v) for k, v in parse_env().items()}
                return json_response(self, 200, {"env": env, "files": list_config_files(), "csv": {k: read_csv(v)[:200] for k, v in CSV_FILES.items()}})
            if parsed.path == "/api/config/file":
                path = parse_qs(parsed.query).get("path", [""])[0]
                p = safe_editable_path(path)
                return json_response(self, 200, {"path": str(p), "content": p.read_text() if p.exists() else ""})
            if parsed.path == "/api/templates":
                return json_response(self, 200, {"templates": templates()})
            if parsed.path == "/api/products":
                return json_response(self, 200, products())
            if parsed.path == "/api/source-catalog":
                return json_response(self, 200, source_catalog())
            if parsed.path == "/api/sources":
                return json_response(self, 200, source_inventory())
            if parsed.path == "/api/packs":
                return json_response(self, 200, pack_inventory())
            if parsed.path.startswith("/api/packs/"):
                pack_id, action = _pack_subroute(parsed.path)
                try:
                    if action == "export":
                        filename, data = pack_export_bundle(pack_id)
                        return binary_response(self, 200, data, filename, "application/zip")
                    if action == "validate-fixtures":
                        return json_response(self, 200, pack_fixture_validation(pack_id))
                    return json_response(self, 200, pack_detail(pack_id))
                except KeyError:
                    return json_response(self, 404, {"error": "pack not found", "code": "pack_not_found"})
            if parsed.path == "/api/catalogue":
                q = parse_qs(parsed.query)
                filters = {
                    k: v[-1]
                    for k, v in q.items()
                    if k in {"q", "vendor", "product", "origin", "relationship", "review_status", "trust_level", "quality_status", "min_quality_score", "is_verified", "artifact_type", "has_reduction", "has_splunk_knowledge", "sc4s_version", "limit", "offset"}
                }
                return json_response(self, 200, catalogue_inventory(filters))
            if parsed.path.startswith("/api/catalogue/"):
                try:
                    return json_response(self, 200, catalogue_detail(_catalogue_subroute(parsed.path) or ""))
                except KeyError:
                    return json_response(self, 404, {"error": "catalogue entry not found", "code": "catalogue_entry_not_found"})
            if parsed.path == "/api/library/sources":
                return json_response(self, 200, library_sources())
            if parsed.path == "/api/library/source-health":
                q = parse_qs(parsed.query)
                source_id = q.get("source_id", ["official"])[-1] or "official"
                try:
                    return json_response(self, 200, library_source_health(source_id))
                except Exception as e:
                    return json_response(self, 502, library_error_payload(e))
            if parsed.path == "/api/library/catalogue":
                q = parse_qs(parsed.query)
                source_id = q.get("source_id", ["official"])[-1] or "official"
                filters = {k: v[-1] for k, v in q.items() if k in {"downloadable_only", "search"}}
                return json_response(self, 200, library_catalogue(source_id, filters))
            if parsed.path == "/api/library/entry":
                q = parse_qs(parsed.query)
                source_id = q.get("source_id", ["official"])[-1] or "official"
                entry_id = q.get("entry_id", [""])[-1]
                if not entry_id:
                    raise ValueError("entry_id is required")
                refresh = str(q.get("refresh", [""])[-1]).lower() in {"1", "true", "yes", "on"}
                return json_response(self, 200, library_entry(source_id, entry_id, refresh=refresh))
            if parsed.path == "/api/library/imports":
                return json_response(self, 200, list_library_imports())
            if parsed.path == "/api/destinations":
                return json_response(self, 200, destination_inventory())
            if parsed.path == "/api/routes":
                return json_response(self, 200, route_inventory())
            if parsed.path == "/api/metrics/syslog-ng":
                q = parse_qs(parsed.query)
                filters = {k: v[-1] for k, v in q.items() if k in {"source_name", "source_id", "source_instance", "state", "type", "search", "limit"}}
                return json_response(self, 200, syslog_ng_metrics(filters))
            if parsed.path == "/metrics":
                return text_response(self, 200, prometheus_metrics(), "text/plain; version=0.0.4; charset=utf-8")
            if parsed.path == "/api/schema":
                return json_response(self, 200, option_schema())
            if parsed.path == "/api/tls":
                return json_response(self, 200, tls_inventory())
            if parsed.path == "/api/validate":
                return json_response(self, 200, validate_config())
            if parsed.path == "/api/backups":
                return json_response(self, 200, {"backups": backups()})
            if parsed.path == "/api/backups/diff":
                name = parse_qs(parsed.query).get("name", [""])[0]
                return json_response(self, 200, backup_diff(name))
            if parsed.path in ["/api/templates/download", "/api/products/download"]:
                name = parse_qs(parsed.query).get("name", [""])[0]
                tp = template_path_by_name(name)
                return binary_response(self, 200, tp.read_bytes(), tp.name, "application/zip")
            if parsed.path == "/api/audit":
                lines = AUDIT_LOG.read_text().splitlines()[-200:] if AUDIT_LOG.exists() else []
                return json_response(self, 200, {"lines": lines})
            if parsed.path.startswith("/api/"):
                return json_response(self, 404, {"error": "not found"})
            return json_response(self, 404, {"error": "not found"})
        except ValueError as e:
            return json_response(self, 400, {"error": str(e)})
        except Exception as e:
            return json_response(self, 500, {"error": str(e)})

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path in ("/api/login", "/api/logout"):
                payload = read_body(self)
                if parsed.path == "/api/login":
                    if not MANUAL_LOGIN_TOKEN:
                        return json_response(self, 403, {"error": "standalone login is not configured", "hint": "set SC4S_MANAGER_MANUAL_LOGIN_TOKEN in manager.env"})
                    token = payload.get("token", "")
                    if not isinstance(token, str) or not _token_matches(token, MANUAL_LOGIN_TOKEN):
                        return json_response(self, 401, {"error": "invalid token"})
                    body = json.dumps({"ok": True}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Set-Cookie", "sc4s_manual_session=%s; Path=/; Max-Age=86400; HttpOnly; SameSite=Lax" % _manual_session_token())
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                body = json.dumps({"ok": True}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Set-Cookie", "sc4s_manual_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if not authorized(self, unsafe=True):
                return self.deny()
            actor = actor_from(self)
            payload = read_body(self)
            if parsed.path == "/api/preview":
                return json_response(self, 200, preview_change(payload))
            if parsed.path == "/api/apply":
                return json_response(self, 200, apply_change(payload, actor))
            if parsed.path == "/api/ports":
                return json_response(self, 200, set_port(payload.get("kind", ""), bool(payload.get("enabled")), payload.get("port"), actor))
            if parsed.path == "/api/env":
                return json_response(self, 200, set_env_value(str(payload.get("key", "")), str(payload.get("value", "")), actor))
            if parsed.path == "/api/env/secret":
                return json_response(self, 200, set_secret_env_value(str(payload.get("key", "")), str(payload.get("value", "")), actor))
            if parsed.path == "/api/services":
                return json_response(self, 200, add_service(payload, actor))
            if parsed.path == "/api/sources/onboard":
                return json_response(self, 200, onboard_source(payload, actor))
            if parsed.path == "/api/sources/delete":
                return json_response(self, 200, delete_source(str(payload.get("name") or payload.get("filter") or ""), actor))
            if parsed.path == "/api/destinations":
                return json_response(self, 200, configure_destination(payload, actor))
            if parsed.path == "/api/destinations/delete":
                return json_response(self, 200, delete_destination(str(payload.get("kind", "")), str(payload.get("id", "")), actor))
            if parsed.path == "/api/routes":
                return json_response(self, 200, upsert_route(payload, actor))
            if parsed.path == "/api/routes/delete":
                return json_response(self, 200, delete_route(str(payload.get("id", "")), actor))
            if parsed.path == "/api/config/file":
                return json_response(self, 200, save_config_file(str(payload.get("path", "")), str(payload.get("content", "")), actor))
            if parsed.path in ["/api/templates/export", "/api/products/export"]:
                return json_response(self, 200, export_template(str(payload.get("name", "sc4s-template")), actor))
            if parsed.path in ["/api/templates/import", "/api/products/import"]:
                if payload.get("content_base64"):
                    return json_response(self, 200, import_template_upload(str(payload.get("name", "upload.zip")), str(payload.get("content_base64", "")), actor))
                return json_response(self, 200, import_template(str(payload.get("path", "")), actor))
            if parsed.path == "/api/tls":
                return json_response(self, 200, install_tls_bundle(str(payload.get("cert", "")), str(payload.get("key", "")), str(payload.get("ca", "")), actor))
            if parsed.path == "/api/tls/delete":
                return json_response(self, 200, delete_tls_bundle(actor))
            if parsed.path == "/api/backups/restore":
                return json_response(self, 200, restore_backup(str(payload.get("name", "")), actor))
            if parsed.path == "/api/validate":
                return json_response(self, 200, validate_config())
            if parsed.path == "/api/reload":
                return json_response(self, 200, reload_sc4s(actor))
            if parsed.path == "/api/restart":
                return json_response(self, 200, restart_sc4s(actor))
            if parsed.path == "/api/library/sync":
                try:
                    return json_response(self, 200, sync_library_source(str(payload.get("source_id", "official")) or "official"))
                except Exception as e:
                    return json_response(self, 502, library_error_payload(e))
            if parsed.path == "/api/library/download":
                try:
                    return json_response(self, 200, download_library_bundle(str(payload.get("source_id", "official")) or "official", str(payload.get("entry_id", ""))))
                except Exception as e:
                    return json_response(self, 502, library_error_payload(e))
            if parsed.path == "/api/library/import/validate":
                try:
                    return json_response(self, 200, validate_library_import(str(payload.get("source_id", "official")) or "official", str(payload.get("entry_id", "")), actor))
                except Exception as e:
                    return json_response(self, 502, library_error_payload(e))
            if parsed.path == "/api/library/import/apply":
                try:
                    return json_response(self, 200, apply_library_import(str(payload.get("import_id", "")), actor, bool(payload.get("apply", True))))
                except Exception as e:
                    return json_response(self, 502, library_error_payload(e))
            if parsed.path.startswith("/api/packs/"):
                pack_id, action = _pack_subroute(parsed.path)
                if action == "validate-fixtures":
                    try:
                        return json_response(self, 200, pack_fixture_validation(pack_id))
                    except KeyError:
                        return json_response(self, 404, {"error": "pack not found", "code": "pack_not_found"})
            if parsed.path == "/api/samples/classify":
                _sp = _sample_preview_module()
                return json_response(self, 200, _sp.classify_sample(
                    str(payload.get("sample", "")),
                    str(payload.get("source_hint", "")),
                    str(payload.get("transport", "unknown")),
                ))
            if parsed.path == "/api/samples/preview":
                _sp = _sample_preview_module()
                return json_response(self, 200, _sp.preview_sample(
                    str(payload.get("sample", "")),
                    str(payload.get("source_hint", "")),
                    str(payload.get("transport", "unknown")),
                    source_catalog=SOURCE_CATALOG,
                ))
            return json_response(self, 404, {"error": "not found"})
        except ValueError as e:
            return json_response(self, 400, {"error": str(e)})
        except Exception as e:
            return json_response(self, 500, {"error": str(e)})


def main() -> None:
    try:
        ensure_dirs()
    except PermissionError as e:
        print(startup_permission_error_message(e), file=sys.stderr)
        raise SystemExit(78) from None
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"SC4S Manager {APP_VERSION} listening on {HOST}:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
