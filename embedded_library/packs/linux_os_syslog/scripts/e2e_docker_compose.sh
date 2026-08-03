#!/usr/bin/env bash
set -euo pipefail

PACK_ID="linux_os_syslog"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-linux-os-syslog-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_LINUX_OS_SYSLOG_PORT:-20065}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
EXPECTED_EVENT_COUNT=13
COUNT_SPL='search index=osnix "SC4S_LINUX_OS_SYSLOG_TEST_" earliest=-2h | stats count'
READBACK_SPL='search index=osnix "SC4S_LINUX_OS_SYSLOG_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=osnix "SC4S_LINUX_OS_SYSLOG_TEST_" earliest=-2h | table _time index sourcetype source host vendor product program process_id action signature signature_id result user auth_method src src_ip src_port dest dest_ip dest_port transport dest_user pam_service pam_event pam_logname effective_uid terminal ruser rhost user_uid dest_user_uid package_action package_name package_version package_arch account_action account_name account_uid account_gid account_home account_shell account_source account_attribute account_old_value account_new_value service command marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/linux_os_syslog/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Linux common OS syslog pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/linux_os_syslog/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the osnix index.
  replay        Send every Linux OS syslog fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_LINUX_OS_SYSLOG_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_linux_os_syslog
    healthcheck:
      test: ["CMD-SHELL", "pgrep -x splunkd >/dev/null 2>&1 && curl -ksS --max-time 5 https://127.0.0.1:8089/services/server/info >/dev/null && curl -ksS --max-time 5 https://127.0.0.1:8088/services/collector/health >/dev/null"]
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
      SC4S_LISTEN_LINUX_OS_SYSLOG_TCP_PORT: "20065"
      SOURCE_ALL_SET: LINUX_OS_SYSLOG
      SOURCE_ALL_SET_APPEND: LINUX_OS_SYSLOG
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20065/tcp"
    volumes:
      - ${PACK_DIR}/sc4s/app_parsers/syslog:/opt/sc4s/local/config/app_parsers/syslog:ro
      - sc4s-var:/var/lib/syslog-ng
    healthcheck:
      test: ["CMD-SHELL", "pgrep -x syslog-ng >/dev/null 2>&1 && syslog-ng-ctl stats 2>&1 | grep -qv 'Error connecting control socket' && (ss -ltn sport = :20065 2>/dev/null | grep -q ':20065 ' || netstat -ltn 2>/dev/null | grep -q ':20065 ')"]
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
  packs/linux_os_syslog/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/linux_os_syslog/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/linux_os_syslog/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/linux_os_syslog/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index osnix -auth admin:\$SPLUNK_PASSWORD || true
  packs/linux_os_syslog/scripts/send_tcp_20065.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/linux_os_syslog/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=osnix present.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id LINUX_OS_SYSLOG.
  3. Replay sends 13 fixture events from test-events/linux_os_syslog_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 13 events across linux:os:auth:sshd, linux:os:auth:sudo, linux:os:auth:su, linux:os:cron, linux:os:kernel, linux:os:systemd, linux:os:package, and linux:os:account.
  6. Detail SPL verifies count, index, sourcetype, source, host, timestamp and required fields per family.

Fixture families covered:
  - sshd_auth and sshd_auth_success -> linux:os:auth:sshd
  - sudo -> linux:os:auth:sudo
  - su_pam and pam_auth_failure -> linux:os:auth:su
  - cron -> linux:os:cron
  - kernel -> linux:os:kernel
  - systemd -> linux:os:systemd
  - package_manager -> linux:os:package
  - account_mgmt -> linux:os:account

Explicit gaps:
  - distro-specific wrappers, journald JSON, native package-log files, broader PAM/shadow-utils variants, multiline application logs, and collector-specific envelopes are not expected to pass until fixture/source-shape evidence is added.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk add index osnix -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S Linux OS syslog listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20065.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "linux_os|linux|splunk|hec|destination|source" | head -80 || true'
  echo "== Splunk readback summary =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${READBACK_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk detail readback =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${DETAIL_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk readback count assertion =="
  local observed_count
  observed_count="$(compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${COUNT_SPL}" -auth "admin:${SPLUNK_PASSWORD}" -output csv | awk -F, 'NR==2 {gsub(/[\"\r]/, "", $1); print $1}')"
  if [[ "${observed_count:-0}" != "${EXPECTED_EVENT_COUNT}" ]]; then
    echo "expected ${EXPECTED_EVENT_COUNT} indexed Linux OS syslog fixture events, observed ${observed_count:-0}" >&2
    return 1
  fi
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
