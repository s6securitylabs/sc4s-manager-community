#!/usr/bin/env bash
set -euo pipefail

PACK_ID="dell_powerscale_onefs"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-dell-powerscale-onefs-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_DELL_POWERSCALE_ONEFS_PORT:-20092}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=infraops "SC4S_DELL_POWERSCALE_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=infraops "SC4S_DELL_POWERSCALE_TEST_" earliest=-2h | table _time index sourcetype source host vendor product protocol topic eventType detailType action signature clientIPAddr src userID userSID user actor object fileName newFileName zoneName marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/dell_powerscale_onefs/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Dell PowerScale OneFS SC4S TEST -> Splunk TEST harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/dell_powerscale_onefs/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the infraops index.
  replay        Send every fixture through the pack TLS/RFC5425 listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_DELL_POWERSCALE_ONEFS_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed Dell PowerScale OneFS protocol/config JSON syslog smoke shape. It is not field
  validation for a real PowerScale appliance, OneFS build, SMB/NFS/HDFS audit coverage, collector
  tier, exact vendor JSON/envelope behavior, or source timezone behavior.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_dell_powerscale_onefs:ro
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
      SC4S_LISTEN_DELL_POWERSCALE_ONEFS_TLS_PORT: "20092"
      SOURCE_ALL_SET: DELL_POWERSCALE_ONEFS
      SOURCE_ALL_SET_APPEND: DELL_POWERSCALE_ONEFS
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20092/tcp"
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
  packs/dell_powerscale_onefs/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/dell_powerscale_onefs/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/dell_powerscale_onefs/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/dell_powerscale_onefs/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index infraops -auth admin:\$SPLUNK_PASSWORD || true
  packs/dell_powerscale_onefs/scripts/send_tls_20092.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/dell_powerscale_onefs/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=infraops present.
  2. SC4S TEST healthy and listening on TLS/RFC5425 tcp/${SC4S_HOST_PORT} for source_id DELL_POWERSCALE_ONEFS.
  3. Replay sends 2 fixture events from test-events/dell_powerscale_onefs_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 2 events across dell:powerscale:onefs:protocol and dell:powerscale:onefs:config with source dell_powerscale_onefs.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, protocol/config family, raw OneFS fields, and analyst aliases.

Fixture families covered:
  - protocol -> dell:powerscale:onefs:protocol (protocol rename audit marker)
  - config -> dell:powerscale:onefs:config (configuration modify audit marker)

Explicit gaps:
  - This harness does not prove a real Dell PowerScale appliance, OneFS version, SMB/NFS/HDFS audit completeness, or production logging configuration.
  - It does not prove exact OneFS forwarded JSON/envelope behavior, UDP/BSD legacy variants, collector wrapper behavior, or source-local timezone handling.
  - Field validation with retained real product/source-version telemetry is not expected to pass until sanctioned PowerScale output or vendor-certified examples are captured.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk add index infraops -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S Dell PowerScale OneFS TLS listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tls_20092.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "powerscale|onefs|dell|splunk|hec|destination|source" | head -120 || true'
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
