#!/usr/bin/env bash
set -euo pipefail

PACK_ID="commvault_commcell"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-commvault-commcell-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_COMMVAULT_COMMCELL_PORT:-20029}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
EXPECTED_EVENT_COUNT=9
READBACK_SPL='search index=commvault "COMMVAULT_PROFILE_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
COUNT_SPL='search index=commvault "COMMVAULT_PROFILE_TEST_" earliest=-2h | stats count'
DETAIL_SPL='search index=commvault "COMMVAULT_PROFILE_TEST_" earliest=-2h | table _time index sourcetype source host vendor product cv_event_type action signature_id signature severity user dest process process_id app message Opid Eventid Alertid sechub_fixture_marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/commvault_commcell/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Commvault CommCell SC4S TEST -> Splunk TEST harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/commvault_commcell/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the commvault index.
  replay        Send every Commvault fixture through the pack TLS/RFC5425 listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_COMMVAULT_COMMCELL_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is refreshed SC4S TEST -> Splunk TEST replay/read-back evidence only
  for the fixture-backed Commvault AuditTrail/Events/Alerts/base source shape. It is not
  field validation for a real CommCell source version, every SIEM/syslog field combination,
  collector wrapper, optional alert-drop reduction behavior, or source-local timezone behavior.
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
      # Splunk's container entrypoint chowns installed apps during first boot.
      # This disposable harness mounts the pack app writable so the entrypoint can
      # complete; do not treat the generated compose file as a production install.
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_commvault_commcell
    healthcheck:
      test: ["CMD-SHELL", "pgrep -x splunkd >/dev/null 2>&1 && curl -ksS --max-time 5 https://127.0.0.1:8089/services/server/info >/dev/null"]
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
      SC4S_LISTEN_COMMVAULT_COMMCELL_TLS_PORT: "20029"
      SOURCE_ALL_SET: COMMVAULT_COMMCELL
      SOURCE_ALL_SET_APPEND: COMMVAULT_COMMCELL
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20029/tcp"
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
  packs/commvault_commcell/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/commvault_commcell/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/commvault_commcell/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/commvault_commcell/compose.yaml -p ${PROJECT} exec -T -u splunk splunk /opt/splunk/bin/splunk add index commvault -auth admin:\$SPLUNK_PASSWORD || true
  packs/commvault_commcell/scripts/send_tls_20029.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/commvault_commcell/compose.yaml -p ${PROJECT} exec -T -u splunk splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=commvault searchable.
  2. SC4S TEST healthy and listening on TLS/RFC5425 tcp/${SC4S_HOST_PORT} for source_id COMMVAULT_COMMCELL.
  3. Replay sends 9 fixture events from test-events/commvault_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 9 events across commvault:commcell:audittrail, commvault:commcell:event, commvault:commcell:alert, and commvault:commcell.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, Commvault product fields, family/action, identifier, severity, user/dest/process context, message, and raw preservation.

Fixture families covered:
  - audit -> commvault:commcell:audittrail (COMMVAULT_PROFILE_TEST_<timestamp>_AUDIT001/AUDIT002/AUDIT003)
  - event -> commvault:commcell:event (COMMVAULT_PROFILE_TEST_<timestamp>_EVENT001/EVENT002)
  - alert -> commvault:commcell:alert (COMMVAULT_PROFILE_TEST_<timestamp>_ALERT001/ALERT002)
  - base -> commvault:commcell (COMMVAULT_PROFILE_TEST_<timestamp>_MEDIA/BASE)

Explicit gaps:
  - This harness refreshes pack-aware fixture replay/read-back only; it does not field-validate a real CommCell version or every SIEM/syslog event shape.
  - It does not prove optional alert-drop postfilter behavior; reduction must be enabled and tested separately before use.
  - Collector/file/API/export wrappers, source-local timezone fallback, and customer-specific Eventcode coverage require additional retained evidence.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk add index commvault -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_commvault.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "Commvault CommCell TLS listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tls_20029.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "commvault|commcell|splunk|hec|destination|source" | head -120 || true'
  echo "== Splunk readback summary =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${READBACK_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk detail readback =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${DETAIL_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk readback count assertion =="
  local observed_count
  observed_count="$(compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${COUNT_SPL}" -auth "admin:${SPLUNK_PASSWORD}" -output csv | awk -F, 'NR==2 {gsub(/\r/, "", $1); print $1}')"
  if [[ "${observed_count}" != "${EXPECTED_EVENT_COUNT}" ]]; then
    echo "ERROR: expected ${EXPECTED_EVENT_COUNT} indexed Commvault CommCell fixture events, observed ${observed_count:-0}" >&2
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
