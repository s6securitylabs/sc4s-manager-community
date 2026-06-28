from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_REPO_URL = "https://github.com/splunk/splunk-connect-for-syslog.git"
DEFAULT_OUTPUT_SUBDIR = Path("catalogue/generated/upstream")
DEFAULT_CACHE_ROOT = Path.home() / ".cache" / "sc4s-manager"
UPSTREAM_CATALOGUE_VERSION = "0.1"

FULL_TREE_RULES = [
    (Path("package/etc/conf.d/conflib/syslog"), "*.conf", "syslog_app_parser"),
    (Path("package/etc/conf.d/conflib/netsource"), "*.conf", "netsource_app_parser"),
    (Path("package/etc/conf.d/conflib/post-filter"), "*.conf", "postfilter"),
    (Path("package/etc/conf.d/destinations"), "*", "destination"),
    (Path("docs/sources"), "*.md", "source_documentation"),
]
LITE_TREE_RULES = [
    (Path("package/lite/etc/addons"), "*", "lite_addon"),
]
CATALOGUE_OUTPUTS = (
    ("sc4s-inbuilt", FULL_TREE_RULES),
    ("sc4s-inbuilt-lite", LITE_TREE_RULES),
)
CATALOGUE_COLUMNS = [
    "origin",
    "artifact_path",
    "artifact_type",
    "source_id",
    "vendor",
    "product",
    "sha256",
]
PREFIX_PATTERNS = [
    "app-postfilter-",
    "app-netsource-",
    "app-syslog-",
    "app-raw-",
    "app-json-",
    "app-cef-",
    "app-leef-",
    "app-",
    "f-",
    "d-",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return token.strip("_")


def infer_source_id_from_path(relative_path: str, artifact_type: str) -> tuple[str | None, str | None, str | None]:
    path = Path(relative_path)
    parts = path.parts
    if "docs" in parts and "sources" in parts:
        try:
            idx = parts.index("sources")
            if len(parts) >= idx + 4 and parts[idx + 1] == "vendor":
                vendor = normalize_token(parts[idx + 2])
                product = normalize_token(parts[idx + 3])
                source_id = "_".join([p for p in [vendor, product] if p]) or None
                return source_id, vendor or None, product or None
            stem = normalize_token(path.stem)
            return stem or None, stem or None, None
        except ValueError:
            pass
    if "package" in parts and "lite" in parts and "addons" in parts:
        try:
            idx = parts.index("addons")
            if len(parts) > idx + 1:
                source = normalize_token(parts[idx + 1])
                vendor, product = split_vendor_product(source)
                return source or None, vendor, product
        except ValueError:
            pass
    stem = normalize_token(path.stem)
    for prefix in PREFIX_PATTERNS:
        if stem.startswith(normalize_token(prefix)):
            stem = stem[len(normalize_token(prefix)) :].strip("_")
            break
    if not stem and artifact_type == "destination":
        stem = normalize_token(path.parent.name)
    if not stem:
        return None, None, None
    vendor, product = split_vendor_product(stem)
    return stem, vendor, product


def split_vendor_product(source_id: str | None) -> tuple[str | None, str | None]:
    if not source_id:
        return None, None
    parts = [part for part in source_id.split("_") if part]
    if not parts:
        return None, None
    vendor = parts[0]
    product = "_".join(parts[1:]) or None
    return vendor, product


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pack_tree_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    if not root.exists():
        return snapshot
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        snapshot[str(path.relative_to(root))] = sha256_file(path)
    return snapshot


def iter_catalogue_files(upstream_root: Path, origin: str) -> list[dict[str, Any]]:
    rules = dict(CATALOGUE_OUTPUTS)[origin]
    artifacts: list[dict[str, Any]] = []
    for base, glob, artifact_type in rules:
        search_root = upstream_root / base
        if not search_root.exists():
            continue
        for candidate in sorted(search_root.rglob(glob)):
            if candidate.is_dir():
                continue
            relative = candidate.relative_to(upstream_root).as_posix()
            source_id, vendor, product = infer_source_id_from_path(relative, artifact_type)
            artifacts.append(
                {
                    "origin": origin,
                    "artifact_path": relative,
                    "artifact_type": artifact_type,
                    "source_id": source_id,
                    "vendor": vendor,
                    "product": product,
                    "sha256": sha256_file(candidate),
                }
            )
    return sorted(artifacts, key=lambda item: (item["artifact_path"], item["artifact_type"], item.get("source_id") or ""))


def build_catalogues(
    upstream_root: Path,
    *,
    repo_url: str,
    requested_ref: str,
    resolved_commit: str,
    generated_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    timestamp = generated_at or utc_now()
    catalogues: dict[str, dict[str, Any]] = {}
    for origin, _rules in CATALOGUE_OUTPUTS:
        artifacts = iter_catalogue_files(upstream_root, origin)
        catalogues[origin] = {
            "catalogue_version": UPSTREAM_CATALOGUE_VERSION,
            "origin": origin,
            "upstream": {
                "repo_url": repo_url,
                "requested_ref": requested_ref,
                "resolved_commit": resolved_commit,
                "generated_at": timestamp,
                "artifact_count": len(artifacts),
            },
            "artifacts": artifacts,
        }
    return catalogues


def write_catalogue_outputs(catalogues: dict[str, dict[str, Any]], output_dir: Path) -> dict[str, dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, dict[str, str]] = {}
    for origin, payload in sorted(catalogues.items()):
        json_path = output_dir / f"{origin}.json"
        tsv_path = output_dir / f"{origin}.tsv"
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        with tsv_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CATALOGUE_COLUMNS, delimiter="\t")
            writer.writeheader()
            for artifact in payload["artifacts"]:
                writer.writerow({column: artifact.get(column, "") or "" for column in CATALOGUE_COLUMNS})
        written[origin] = {"json": str(json_path), "tsv": str(tsv_path)}
    return written


def load_existing_catalogues(output_dir: Path) -> dict[str, dict[str, Any]]:
    existing: dict[str, dict[str, Any]] = {}
    for origin, _rules in CATALOGUE_OUTPUTS:
        path = output_dir / f"{origin}.json"
        if path.exists():
            existing[origin] = json.loads(path.read_text())
    return existing


def catalogue_artifact_map(catalogues: dict[str, dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    flattened: dict[tuple[str, str], dict[str, Any]] = {}
    for origin, payload in catalogues.items():
        for artifact in payload.get("artifacts", []):
            flattened[(origin, artifact["artifact_path"])] = artifact
    return flattened


def build_drift_report(previous: dict[str, dict[str, Any]], current: dict[str, dict[str, Any]]) -> dict[str, Any]:
    previous_map = catalogue_artifact_map(previous)
    current_map = catalogue_artifact_map(current)
    previous_keys = set(previous_map)
    current_keys = set(current_map)
    added = [current_map[key] for key in sorted(current_keys - previous_keys)]
    removed = [previous_map[key] for key in sorted(previous_keys - current_keys)]
    changed = []
    for key in sorted(previous_keys & current_keys):
        before = previous_map[key]
        after = current_map[key]
        if any(before.get(field) != after.get(field) for field in CATALOGUE_COLUMNS[2:]):
            changed.append(
                {
                    "origin": key[0],
                    "artifact_path": key[1],
                    "before": before,
                    "after": after,
                }
            )
    return {
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def write_drift_outputs(drift_report: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "drift-report.json"
    md_path = output_dir / "drift-report.md"
    json_path.write_text(json.dumps(drift_report, indent=2, sort_keys=True) + "\n")
    summary = drift_report["summary"]
    lines = [
        "# Upstream SC4S drift report",
        "",
        f"- Added: {summary['added']}",
        f"- Removed: {summary['removed']}",
        f"- Changed: {summary['changed']}",
        "",
    ]
    for section in ["added", "removed"]:
        lines.append(f"## {section.capitalize()}")
        items = drift_report[section]
        if not items:
            lines.append("")
            lines.append("- none")
            lines.append("")
            continue
        lines.append("")
        for item in items:
            lines.append(f"- `{item['origin']}` `{item['artifact_path']}` ({item['artifact_type']})")
        lines.append("")
    lines.append("## Changed")
    lines.append("")
    if not drift_report["changed"]:
        lines.append("- none")
    else:
        for item in drift_report["changed"]:
            lines.append(
                f"- `{item['origin']}` `{item['artifact_path']}`: {item['before'].get('sha256')} -> {item['after'].get('sha256')}"
            )
    lines.append("")
    md_path.write_text("\n".join(lines))
    return {"json": str(json_path), "markdown": str(md_path)}


def run_git(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.stdout.strip()


def ensure_clone(cache_dir: Path, repo_url: str) -> None:
    if cache_dir.exists() and (cache_dir / ".git").exists():
        return
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", repo_url, str(cache_dir)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def refresh_upstream_cache(cache_dir: Path, repo_url: str, ref: str, refresh_cache: bool) -> str:
    ensure_clone(cache_dir, repo_url)
    if refresh_cache:
        subprocess.run(["git", "-C", str(cache_dir), "fetch", "--tags", "--prune", "origin"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    subprocess.run(["git", "-C", str(cache_dir), "checkout", "--detach", ref], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    subprocess.run(["git", "-C", str(cache_dir), "reset", "--hard", ref], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return run_git(["git", "rev-parse", "HEAD"], cwd=cache_dir)


def sync_upstream_catalogue(
    *,
    manager_root: Path,
    cache_dir: Path,
    output_dir: Path,
    repo_url: str,
    ref: str,
    refresh_cache: bool,
    generated_at: str | None = None,
) -> dict[str, Any]:
    packs_before = pack_tree_snapshot(manager_root / "packs")
    previous = load_existing_catalogues(output_dir)
    resolved_commit = refresh_upstream_cache(cache_dir, repo_url, ref, refresh_cache)
    catalogues = build_catalogues(
        cache_dir,
        repo_url=repo_url,
        requested_ref=ref,
        resolved_commit=resolved_commit,
        generated_at=generated_at,
    )
    outputs = write_catalogue_outputs(catalogues, output_dir)
    drift_report = build_drift_report(previous, catalogues)
    drift_outputs = write_drift_outputs(drift_report, output_dir)
    packs_after = pack_tree_snapshot(manager_root / "packs")
    if packs_before != packs_after:
        raise RuntimeError("packs/ mutated during upstream sync")
    return {
        "repo_url": repo_url,
        "requested_ref": ref,
        "resolved_commit": resolved_commit,
        "generated_at": next(iter(catalogues.values()))["upstream"]["generated_at"],
        "cache_dir": str(cache_dir),
        "output_dir": str(output_dir),
        "catalogues": outputs,
        "drift_report": drift_report,
        "drift_outputs": drift_outputs,
    }


def parse_catalog_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SC4S upstream catalogue JSON/TSV from a checked-out tree.")
    parser.add_argument("--upstream-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--requested-ref", default="unknown")
    parser.add_argument("--resolved-commit", default="unknown")
    parser.add_argument("--generated-at")
    return parser.parse_args(argv)


def parse_sync_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the local upstream SC4S cache and rebuild generated catalogues.")
    parser.add_argument("--ref", required=True)
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_ROOT / "upstream-sc4s")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--generated-at")
    return parser.parse_args(argv)


def catalog_main(argv: list[str] | None = None) -> int:
    args = parse_catalog_args(argv)
    catalogues = build_catalogues(
        args.upstream_root,
        repo_url=args.repo_url,
        requested_ref=args.requested_ref,
        resolved_commit=args.resolved_commit,
        generated_at=args.generated_at,
    )
    outputs = write_catalogue_outputs(catalogues, args.output_dir)
    print(json.dumps({"output_dir": str(args.output_dir), "catalogues": outputs}, indent=2, sort_keys=True))
    return 0


def sync_main(argv: list[str] | None = None, manager_root: Path | None = None) -> int:
    args = parse_sync_args(argv)
    resolved_manager_root = manager_root or Path(__file__).resolve().parents[2]
    output_dir = args.output_dir or (resolved_manager_root / DEFAULT_OUTPUT_SUBDIR)
    result = sync_upstream_catalogue(
        manager_root=resolved_manager_root,
        cache_dir=args.cache_dir,
        output_dir=output_dir,
        repo_url=args.repo_url,
        ref=args.ref,
        refresh_cache=args.refresh_cache,
        generated_at=args.generated_at,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(sync_main())
