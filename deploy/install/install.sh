#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: deploy/install/install.sh [--prefix /opt/sc4s-manager] [--state-dir /opt/sc4s-manager/state]

Dry-run installer for SC4S Manager packaging validation. It prints the install
plan and verifies local artifacts, but does not create users, write system
paths, enable services, pull images, or restart anything.
USAGE
}

prefix="/opt/sc4s-manager"
state_dir="/opt/sc4s-manager/state"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

while (($#)); do
  case "$1" in
    --prefix)
      prefix="${2:?missing value for --prefix}"
      shift 2
      ;;
    --state-dir)
      state_dir="${2:?missing value for --state-dir}"
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
      echo "error: this installer is intentionally dry-run only" >&2
      exit 2
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_file() {
  local path="$1"
  if [[ ! -f "$repo_root/$path" ]]; then
    echo "missing required artifact: $path" >&2
    exit 1
  fi
}

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

require_file "deploy/systemd/sc4s-manager.service"
require_file "deploy/systemd/sc4s-manager-control.service"
require_file "deploy/systemd/sc4s-manager-control.socket"
require_file "deploy/compose/compose.yaml"

cat <<PLAN
sc4s-manager dry-run install plan

Repository: $repo_root
Install prefix: $prefix
State directory: $state_dir

Would verify:
- Python runtime >= 3.11
- Container runtime availability
- Dedicated sc4s-manager user/group
- Writable SC4S root, TLS directory, and manager runtime directories
- External secret material in /etc/sc4s-manager/*.env

Would install:
- application files to $prefix
- systemd units to /etc/systemd/system/
- manager runtime directories under $prefix/state, $prefix/backups, and $prefix/templates
- SC4S TLS/config directories under /opt/sc4s/tls and /opt/sc4s/local
- manager runtime ownership for sc4s-manager:sc4s-manager on those directories
- control socket at /run/sc4s-manager/control.sock

Would not run in dry-run mode:
- useradd/groupadd
- package installation
- image pulls
- systemctl daemon-reload/enable/start
- container restart/reload actions
PLAN
