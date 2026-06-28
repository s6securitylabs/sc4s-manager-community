#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/build_frontend.sh

Build the optional SC4S Manager static frontend for release packaging.
This script intentionally mutates only frontend dependency/build outputs
(node_modules/, package-lock updates as npm requires, and frontend/dist/).
The dry-run install and upgrade scripts never call this script.
USAGE
}

case "${1:-}" in
  -h|--help)
    usage
    exit 0
    ;;
  "")
    ;;
  *)
    echo "error: unknown argument: $1" >&2
    usage >&2
    exit 2
    ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
frontend_dir="$repo_root/frontend"

if [[ ! -f "$frontend_dir/package.json" ]]; then
  echo "frontend build: skipped (frontend/package.json not present)"
  exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm is required to build the frontend" >&2
  exit 1
fi

cd "$frontend_dir"
if [[ -f package-lock.json || -f npm-shrinkwrap.json ]]; then
  npm ci
else
  npm install
fi
npm run build

test -f dist/index.html
printf 'frontend build: wrote %s\n' "$frontend_dir/dist/index.html"
