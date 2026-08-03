#!/usr/bin/env bash
set -euo pipefail

PACK_ID="juniper_srx_junos"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-juniper-srx-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_JUNIPER_SRX_JUNOS_PORT:-20044}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=netfw "SC4S_JUNIPER_SRX_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=netfw "SC4S_JUNIPER_SRX_TEST_" earliest=-2h | table _time index sourcetype source host vendor product vendor_product juniper_program juniper_event action signature signature_id severity src src_ip src_port dest dest_ip dest_port transport user url policy_name source_zone destination_zone eventtype _raw'

usage() {
  cat <<'USAGE'
Usage: packs/juniper_srx_junos/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Juniper SRX/Junos TCP/RFC5424 SC4S pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/juniper_srx_junos/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack.
  replay        Send every Juniper SRX/Junos fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_JUNIPER_SRX_JUNOS_PORT, SPLUNK_WEB_PORT,
  SPLUNK_MGMT_PORT, SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR,
  SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  four fixture-backed Juniper SRX/Junos structured syslog source shapes. It is not production/field
  validation for a real appliance, Junos release, collector wrapper, TLS/RFC5425 path,
  or the full SRX/Junos security log taxonomy.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_juniper_srx_junos:ro
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
      SC4S_LISTEN_JUNIPER_SRX_JUNOS_TCP_PORT: "20044"
      SOURCE_ALL_SET: JUNIPER_SRX_JUNOS
      SOURCE_ALL_SET_APPEND: JUNIPER_SRX_JUNOS
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20044/tcp"
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
  packs/juniper_srx_junos/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/juniper_srx_junos/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/juniper_srx_junos/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  packs/juniper_srx_junos/scripts/send_tcp_20044.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/juniper_srx_junos/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=netfw searchable.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id JUNIPER_SRX_JUNOS.
  3. Replay sends 4 fixture events from test-events/juniper_srx_junos_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 4 events with sourcetypes juniper:junos:firewall, juniper:junos:idp, and juniper:junos:utm.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, Juniper family/action/signature fields, source/destination/port fields, policy/zone/user/url context, eventtype, and raw preservation.

Fixture families covered:
  - flow / idp / utm

Explicit gaps:
  - This harness does not prove a live SRX/Junos appliance, Junos release-specific field completeness, TLS/RFC5425 production transport, collector envelopes, or the full SRX/Junos security log taxonomy.
  - Field validation with retained real product/source-version telemetry requires sanctioned appliance samples or a non-production SRX/Junos feed.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S Juniper SRX/Junos TCP listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20044.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  compose exec -T splunk /opt/splunk/bin/splunk search "${READBACK_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  compose exec -T splunk /opt/splunk/bin/splunk search "${DETAIL_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
}

run() {
  up
  replay
  echo "waiting for Splunk indexing"
  sleep 20
  readback
}

down() {
  require_docker
  if [[ -f "${COMPOSE_FILE}" ]]; then
    compose down -v --remove-orphans
  else
    echo "compose file not present at ${COMPOSE_FILE}; nothing to remove"
  fi
}

cmd="${1:-plan}"
case "${cmd}" in
  plan) plan ;;
  write-compose) write_compose ;;
  up) up ;;
  replay|send) replay ;;
  readback) readback ;;
  run|validate) run ;;
  down) down ;;
  help|-h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
