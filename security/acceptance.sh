#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: security/acceptance.sh [--base-url URL] [--token-env ENV_NAME] [--report PATH]

Security acceptance scaffold for sc4s-manager. By default it runs repository-level
checks only. When --base-url is provided, it prints the live checks to perform
but does not send mutating requests.
USAGE
}

base_url=""
token_env="SC4S_MANAGER_MANUAL_LOGIN_TOKEN"
report=""
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0

while (($#)); do
  case "$1" in
    --base-url)
      base_url="${2:?missing value for --base-url}"
      shift 2
      ;;
    --token-env)
      token_env="${2:?missing value for --token-env}"
      shift 2
      ;;
    --report)
      report="${2:?missing value for --report}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

check() {
  local name="$1"
  shift
  if "$@"; then
    printf 'PASS %s\n' "$name"
  else
    printf 'FAIL %s\n' "$name"
    failures=$((failures + 1))
  fi
}

manager_has_no_docker_socket() {
  local manager_block
  manager_block="$(awk '/^  manager:/{flag=1; next} /^  control:/{flag=0} flag {print}' "$repo_root/deploy/compose/compose.yaml")"
  ! grep -Eq 'docker\.sock|/var/run/docker\.sock' "$repo_root/deploy/systemd/sc4s-manager.service" &&
    ! grep -Eq 'docker\.sock|/var/run/docker\.sock' <<<"$manager_block"
}

control_socket_is_unix_only() {
  grep -q 'ListenStream=/run/sc4s-manager/control.sock' "$repo_root/deploy/systemd/sc4s-manager-control.socket"
}

compose_uses_secret_placeholders() {
  grep -q 'set outside git' "$repo_root/deploy/compose/compose.yaml" &&
    ! grep -Eiq '(token|secret|password):[[:space:]]*["'\'']?[A-Za-z0-9+/=]{12,}' "$repo_root/deploy/compose/compose.yaml"
}

dry_run_scripts_reject_execute() {
  "$repo_root/deploy/install/install.sh" --execute >/dev/null 2>&1 &&
    return 1
  "$repo_root/deploy/upgrade/upgrade.sh" --execute --artifact "$repo_root/README.md" >/dev/null 2>&1 &&
    return 1
  return 0
}

run_checks() {
  printf '# sc4s-manager Security Acceptance Dry Run\n\n'
  printf 'Repository: %s\n\n' "$repo_root"
  check "manager has no Docker socket mount" manager_has_no_docker_socket
  check "control socket is Unix-domain scoped" control_socket_is_unix_only
  check "compose contains placeholders, not real secrets" compose_uses_secret_placeholders
  check "install/upgrade scripts reject execute flags" dry_run_scripts_reject_execute

  if [[ -n "$base_url" ]]; then
    printf '\nLive acceptance plan for %s\n' "$base_url"
    printf '%s\n' '- GET /health and /api/health with no credentials.'
    printf '%s\n' "- Verify mutating API calls fail without $token_env or SC4S_MANAGER_API_TOKEN."
    printf '%s\n' '- Verify path traversal probes return 400.'
    printf '%s\n' '- Verify unsupported control actions are rejected by the control daemon.'
    printf '%s\n' '- Verify secret-bearing API responses and backup diffs contain [REDACTED].'
    printf '%s\n' '- Verify TLS certificate/key mismatch is rejected before restart.'
    printf '\nNo live mutating requests were sent by this scaffold.\n'
  fi
}

if [[ -n "$report" ]]; then
  run_checks | tee "$report"
else
  run_checks
fi

if ((failures > 0)); then
  exit 1
fi
