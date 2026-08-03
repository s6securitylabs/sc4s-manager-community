#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: deploy/rollback/rollback.sh --backup PATH [--prefix /opt/sc4s-manager] [--dry-run]

Non-mutating rollback planner. It verifies that a prior lifecycle backup exists
and prints the restore/revalidate/restart/post-check sequence. Execution is not
implemented; use a disposable-host procedure and record live evidence.
USAGE
}

backup=""
prefix="/opt/sc4s-manager"
while (($#)); do
  case "$1" in
    --backup) backup="${2:?missing value for --backup}"; shift 2 ;;
    --prefix) prefix="${2:?missing value for --prefix}"; shift 2 ;;
    --dry-run) shift ;;
    -h|--help) usage; exit 0 ;;
    --execute|--apply|--force)
      echo "error: rollback execution is not implemented; this command is a planner only" >&2
      exit 2 ;;
    *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$backup" ]] || { echo "error: --backup is required" >&2; exit 2; }
[[ -e "$backup" ]] || { echo "error: backup does not exist: $backup" >&2; exit 1; }

cat <<PLAN
sc4s-manager dry-run rollback plan
Backup: $backup
Install prefix: $prefix
Would verify backup metadata/checksums, stop Manager, restore the prior release
atomically while preserving runtime state, restart fixed services, validate
/ready and configuration, and record redacted rollback evidence.
No files, services, users, containers, or symlinks were changed.
PLAN
