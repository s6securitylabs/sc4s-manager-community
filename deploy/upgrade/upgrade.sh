#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: deploy/upgrade/upgrade.sh --artifact PATH [--prefix /opt/sc4s-manager] [--backup-dir /opt/sc4s-manager/backups]

Dry-run upgrade planner for SC4S Manager. It validates inputs and prints the
backup/deploy/validate/restart/post-check sequence without changing files or
services.
USAGE
}

artifact=""
prefix="/opt/sc4s-manager"
backup_dir="/opt/sc4s-manager/backups"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

while (($#)); do
  case "$1" in
    --artifact)
      artifact="${2:?missing value for --artifact}"
      shift 2
      ;;
    --prefix)
      prefix="${2:?missing value for --prefix}"
      shift 2
      ;;
    --backup-dir)
      backup_dir="${2:?missing value for --backup-dir}"
      shift 2
      ;;
    --dry-run)
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --execute|--apply|--force)
      echo "error: this upgrade script is intentionally dry-run only" >&2
      exit 2
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$artifact" ]]; then
  echo "error: --artifact is required" >&2
  usage >&2
  exit 2
fi

if [[ ! -e "$artifact" ]]; then
  echo "error: artifact does not exist: $artifact" >&2
  exit 1
fi

case "$artifact" in
  *.tar|*.tar.gz|*.tgz)
    ;;
  *)
    echo "error: artifact is not a supported archive (.tar, .tar.gz, .tgz): $artifact" >&2
    exit 1
    ;;
esac

if ! tar -tf "$artifact" >/dev/null 2>&1; then
  echo "error: artifact is not a readable tar archive: $artifact" >&2
  exit 1
fi

if ! tar -tf "$artifact" | grep -Eq '(^|/)src/sc4s_manager/app\.py$'; then
  echo "error: artifact does not contain src/sc4s_manager/app.py" >&2
  exit 1
fi

verify_frontend_artifact_if_available() {
  local frontend_dir="$repo_root/frontend"
  if [[ ! -f "$frontend_dir/package.json" ]]; then
    echo "frontend artifact: skipped (frontend/package.json not present)"
    return 0
  fi

  if [[ -f "$frontend_dir/dist/index.html" ]]; then
    echo "frontend artifact: found frontend/dist/index.html"
    echo "frontend artifact: use scripts/build_frontend.sh to refresh before packaging"
    return 0
  fi

  echo "frontend artifact: frontend source present but frontend/dist/index.html is absent" >&2
  echo "frontend artifact: run scripts/build_frontend.sh before creating a release artifact" >&2
}

verify_frontend_artifact_if_available

cat <<PLAN
sc4s-manager dry-run upgrade plan

Artifact: $artifact
Install prefix: $prefix
Backup directory: $backup_dir

Would perform:
1. Capture current package manifest and service status.
2. Back up $prefix, /etc/sc4s-manager, systemd units, and manager state metadata.
3. Stage artifact in a temporary release directory.
4. Run syntax checks and unit tests from the staged release.
5. Stop manager after control socket health is recorded.
6. Atomically switch $prefix to the staged release.
7. Reload systemd and restart sc4s-manager-control.socket, sc4s-manager-control.service, and sc4s-manager.service.
8. Run post-checks: /health, /api/health, config validation, version drift, and redaction smoke.
9. Record upgrade evidence with no secret values.

No files, services, users, containers, or symlinks were changed.
PLAN
