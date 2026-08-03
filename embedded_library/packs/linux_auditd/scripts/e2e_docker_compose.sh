#!/usr/bin/env bash
set -euo pipefail

PACK_ID="linux_auditd"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-linux-auditd-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_LINUX_AUDITD_PORT:-20064}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=osnix "SC4S_LINUX_AUDITD_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=osnix "SC4S_LINUX_AUDITD_TEST_" earliest=-2h | table _time index sourcetype source host vendor product audit_type audit_serial action operation signature signature_id result auid uid user src src_ip process process_id security_subject process_path process_command_line cwd file_path audit_key audit_rule_list selinux_permission selinux_source_context selinux_target_context selinux_target_class daemon_operation daemon_state daemon_version kernel_version audit_format user_command_cwd user_command_hex tty_major tty_minor tty_data_hex software_package software_type gpg_result key_enforce root_dir marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/linux_auditd/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Linux auditd relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/linux_auditd/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the osnix index.
  replay        Send every Linux auditd fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_LINUX_AUDITD_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed source shapes. It is not production/field validation and must not promote
  trust unless retained evidence shows count, index, sourcetype, source, timestamp and fields.
USAGE
}

require_docker() {
  command -v docker >/dev/null 2>&1 || { echo "docker CLI not found; use 'plan' or install Docker/Compose" >&2; exit 127; }
  docker compose version >/dev/null 2>&1 || { echo "docker compose plugin not available" >&2; exit 127; }
}

write_compose() {
  mkdir -p "${WORK_DIR}"
  local hec_token="${HEC_TOKEN_VALUE:-$(python3 -c 'import uuid; print(uuid.uuid4())')}"
  cat >"${COMPOSE_FILE}" <<YAML
name: ${PROJECT}
services:
  splunk:
    image: ${SPLUNK_IMAGE}
    platform: linux/amd64
    hostname: splunk-test
    environment:
      SPLUNK_START_ARGS: --accept-license
      SPLUNK_PASSWORD: ${SPLUNK_PASSWORD}
      SPLUNK_HEC_TOKEN: ${hec_token}
      SPLUNK_APPS_URL: ""
    ports:
      - "${SPLUNK_WEB_PORT}:8000"
      - "${SPLUNK_MGMT_PORT}:8089"
      - "${SPLUNK_HEC_PORT}:8088"
    volumes:
      - splunk-var:/opt/splunk/var
      - splunk-etc:/opt/splunk/etc
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_linux_auditd:ro
    healthcheck:
      test: ["CMD-SHELL", "/opt/splunk/bin/splunk status --accept-license --answer-yes --no-prompt >/dev/null 2>&1"]
      interval: 15s
      timeout: 10s
      retries: 40
  sc4s:
    image: ${SC4S_IMAGE}
    hostname: sc4s-test
    depends_on:
      splunk:
        condition: service_healthy
    environment:
      SC4S_DEST_SPLUNK_HEC_DEFAULT_URL: https://splunk:8088/services/collector/event
      SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN: ${hec_token}
      SC4S_DEST_SPLUNK_HEC_DEFAULT_TLS_VERIFY: "no"
      SC4S_LISTEN_LINUX_AUDITD_TCP_PORT: "20064"
      SOURCE_ALL_SET: LINUX_AUDITD
      SOURCE_ALL_SET_APPEND: LINUX_AUDITD
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20064/tcp"
    volumes:
      - ${PACK_DIR}/sc4s/app_parsers/syslog:/opt/sc4s/local/config/app_parsers/syslog:ro
      - sc4s-var:/var/lib/syslog-ng
    healthcheck:
      test: ["CMD-SHELL", "syslog-ng-ctl stats >/dev/null 2>&1 || pgrep syslog-ng >/dev/null 2>&1"]
      interval: 15s
      timeout: 10s
      retries: 40
volumes:
  splunk-var: {}
  splunk-etc: {}
  sc4s-var: {}
YAML
  echo "wrote ${COMPOSE_FILE}"
}

compose() {
  docker compose -f "${COMPOSE_FILE}" -p "${PROJECT}" "$@"
}

plan() {
  cat <<PLAN
One-shot command:
  packs/linux_auditd/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/linux_auditd/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/linux_auditd/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/linux_auditd/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index osnix -auth admin:\$SPLUNK_PASSWORD || true
  packs/linux_auditd/scripts/send_tcp_20064.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/linux_auditd/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=osnix present.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id LINUX_AUDITD.
  3. Replay sends 14 fixture events from test-events/linux_auditd_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 14 events across linux:auditd:syscall, linux:auditd:execve, linux:auditd:user_login, linux:auditd:path, linux:auditd:cwd, linux:auditd:user_auth, linux:auditd:config_change, linux:auditd:avc, linux:auditd:daemon_start, linux:auditd:daemon_end, linux:auditd:daemon_config, linux:auditd:user_cmd, linux:auditd:tty, and linux:auditd:software_update.
  6. Detail SPL verifies count, index, sourcetype, source, host, timestamp and required fields per family.

Fixture families covered:
  - syscall -> linux:auditd:syscall
  - execve -> linux:auditd:execve
  - user_login -> linux:auditd:user_login
  - path -> linux:auditd:path
  - cwd -> linux:auditd:cwd
  - user_auth -> linux:auditd:user_auth
  - config_change -> linux:auditd:config_change
  - avc -> linux:auditd:avc
  - daemon_start -> linux:auditd:daemon_start
  - daemon_end -> linux:auditd:daemon_end
  - daemon_config -> linux:auditd:daemon_config
  - user_cmd -> linux:auditd:user_cmd
  - tty -> linux:auditd:tty
  - software_update -> linux:auditd:software_update

Explicit gaps:
  - live Linux auditd source-version emission and kernel/userspace option behavior are not proven by this harness.
  - multi-record audit-event correlation is preserved by audit_serial but not assembled into one event.
  - AppArmor denials, audit daemon abort/rotate/resume, backlog/lost-event health records, distro wrappers, and collector envelopes remain deferred until exact source-shape evidence is added.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk add index osnix -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S Linux auditd listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20064.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "linux_audit|auditd|splunk|hec|destination|source" | head -80 || true'
  echo "== Splunk readback summary =="
  compose exec -T splunk /opt/splunk/bin/splunk search "${READBACK_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk detail readback =="
  compose exec -T splunk /opt/splunk/bin/splunk search "${DETAIL_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
}

case "${1:-plan}" in
  plan) plan ;;
  write-compose) write_compose ;;
  up) up ;;
  replay) replay ;;
  readback) readback ;;
  run) up; replay; sleep 20; readback ;;
  down) require_docker; write_compose; compose down -v --remove-orphans ;;
  -h|--help|help) usage ;;
  *) usage >&2; exit 2 ;;
esac
