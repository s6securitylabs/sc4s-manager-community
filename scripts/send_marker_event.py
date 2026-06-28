#!/usr/bin/env python3
"""Send non-destructive SC4S acceptance marker events.

This probe validates the network ingestion path only. It never reads Splunk
credentials, never queries Splunk, and sends a synthetic marker event that is
safe to search for and delete from downstream indexes.
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import time
import uuid
from dataclasses import asdict, dataclass


@dataclass
class Attempt:
    protocol: str
    host: str
    port: int
    ok: bool
    detail: str


def marker_payload(marker_id: str, hostname: str) -> str:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return (
        f"<134>1 {ts} {hostname} sc4s-acceptance - {marker_id} "
        f'[sc4s_acceptance marker_id="{marker_id}" purpose="enterprise_acceptance"] '
        f"SC4S_ACCEPTANCE_MARKER marker_id={marker_id} safe=true"
    )


def send_udp(host: str, port: int, payload: bytes, timeout: float) -> Attempt:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sent = sock.sendto(payload, (host, port))
        return Attempt("udp", host, port, sent == len(payload), f"sent_bytes={sent}")
    except Exception as exc:
        return Attempt("udp", host, port, False, type(exc).__name__)


def send_tcp(host: str, port: int, payload: bytes, timeout: float) -> Attempt:
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(payload + b"\n")
        return Attempt("tcp", host, port, True, "sent")
    except Exception as exc:
        return Attempt("tcp", host, port, False, type(exc).__name__)


def send_tls(host: str, port: int, payload: bytes, timeout: float, verify: bool) -> Attempt:
    try:
        context = ssl.create_default_context()
        if not verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host if verify else None) as sock:
                sock.sendall(payload + b"\n")
        return Attempt("tls", host, port, True, "sent")
    except Exception as exc:
        return Attempt("tls", host, port, False, type(exc).__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send safe SC4S marker events over UDP, TCP, and/or TLS.")
    parser.add_argument("--host", default="127.0.0.1", help="SC4S listener host.")
    parser.add_argument("--udp-port", type=int, default=514)
    parser.add_argument("--tcp-port", type=int, default=514)
    parser.add_argument("--tls-port", type=int, default=6514)
    parser.add_argument("--protocol", choices=["udp", "tcp", "tls", "all"], default="all")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--hostname", default=socket.gethostname())
    parser.add_argument("--marker-id", default="")
    parser.add_argument("--tls-no-verify", action="store_true", help="Allow self-signed TLS listener certificates.")
    parser.add_argument("--dry-run", action="store_true", help="Build the marker report without sending packets.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    marker_id = args.marker_id or f"sc4s-acceptance-{uuid.uuid4()}"
    payload = marker_payload(marker_id, args.hostname).encode("utf-8")
    protocols = ["udp", "tcp", "tls"] if args.protocol == "all" else [args.protocol]

    attempts: list[Attempt] = []
    if args.dry_run:
        attempts = [
            Attempt(proto, args.host, {"udp": args.udp_port, "tcp": args.tcp_port, "tls": args.tls_port}[proto], True, "dry_run")
            for proto in protocols
        ]
    else:
        for proto in protocols:
            if proto == "udp":
                attempts.append(send_udp(args.host, args.udp_port, payload, args.timeout))
            elif proto == "tcp":
                attempts.append(send_tcp(args.host, args.tcp_port, payload, args.timeout))
            elif proto == "tls":
                attempts.append(send_tls(args.host, args.tls_port, payload, args.timeout, not args.tls_no_verify))

    report = {
        "marker_id": marker_id,
        "payload_preview": payload.decode("utf-8"),
        "attempts": [asdict(attempt) for attempt in attempts],
        "splunk_search_hint": f'index=* "SC4S_ACCEPTANCE_MARKER" "{marker_id}"',
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(attempt.ok for attempt in attempts) else 2


if __name__ == "__main__":
    sys.exit(main())
