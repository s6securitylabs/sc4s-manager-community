#!/usr/bin/env bash
set -euo pipefail

PACK_ID="cisco_duo_audit"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-cisco-duo-audit-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_CISCO_DUO_AUDIT_PORT:-20088}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=main "SC4S_CISCO_DUO_AUDIT_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=main "SC4S_CISCO_DUO_AUDIT_TEST_" earliest=-2h | table _time index sourcetype source host vendor product duo_family event_type user src_user src_ip app action vendor_raw_action signature signature_id status factor reason object object_type action_name outcome_result context type credits phone telephony_id txid sekey state surfaced_timestamp priority_event triaged_as_interesting trust_explanation_type priority_reason_type user_id user_status phone_id phone_platform phone_type phone_last_seen phone_encrypted phone_screenlock phone_tampered integration_key integration_name integration_type adminapi_read_log adminapi_read_resource adminapi_integrations adminapi_settings adminapi_write_resource user_access groups_allowed policy_key prompt_v4_enabled frameless_auth_prompt_enabled networks_for_api_access marker _raw'
COUNT_SPL='search index=main "SC4S_CISCO_DUO_AUDIT_TEST_" earliest=-2h | stats count'
EXPECTED_EVENT_COUNT=12

usage() {
  cat <<'USAGE'
Usage: packs/cisco_duo_audit/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Cisco Duo Audit relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/cisco_duo_audit/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and ensure index=main is available.
  replay        Send every Cisco Duo JSON fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_CISCO_DUO_AUDIT_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed Duo JSON relay shapes. It is not production/field validation and must not
  promote trust unless retained evidence shows count, index, sourcetype, source, timestamp and fields.
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
      # Splunk's disposable entrypoint chowns installed apps during first boot.
      # Keep the TEST mount writable so bootstrap can complete; this is not
      # production install guidance.
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_cisco_duo_audit
    healthcheck:
      test: ["CMD-SHELL", "pgrep -x splunkd >/dev/null 2>&1 && curl -ksS --max-time 5 https://127.0.0.1:8089/services/server/info >/dev/null && curl -ksS --max-time 5 http://127.0.0.1:8088/services/collector/health >/dev/null"]
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
      SC4S_LISTEN_CISCO_DUO_AUDIT_TCP_PORT: "20088"
      SOURCE_ALL_SET: CISCO_DUO_AUDIT
      SOURCE_ALL_SET_APPEND: CISCO_DUO_AUDIT
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20088/tcp"
    volumes:
      - ${PACK_DIR}/sc4s/app_parsers/syslog:/opt/sc4s/local/config/app_parsers/syslog:ro
      - sc4s-var:/var/lib/syslog-ng
    healthcheck:
      test: ["CMD-SHELL", "pgrep -x syslog-ng >/dev/null 2>&1 && syslog-ng-ctl stats 2>&1 | grep -qv 'Error connecting control socket' && (ss -ltn sport = :20088 2>/dev/null | grep -q ':20088 ' || netstat -ltn 2>/dev/null | grep -q ':20088 ')"]
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
  packs/cisco_duo_audit/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/cisco_duo_audit/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/cisco_duo_audit/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  packs/cisco_duo_audit/scripts/send_tcp_20088.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/cisco_duo_audit/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=main searchable.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id CISCO_DUO_AUDIT.
  3. Replay sends 12 fixture events from test-events/cisco_duo_audit_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 12 events with sourcetype cisco:duo:audit:json.
  6. Detail SPL verifies count, index, sourcetype, source, host, timestamp and required Duo fields.

Fixture families covered:
  - authentication success, failure, and fraud
  - administrative and policy activity
  - Activity Logs v2 WebAuthn credential activity
  - Telephony Logs v2 SMS/phone usage
  - Trust Monitor auth, bypass-status, and device-registration security events
  - Admin API user/phone inventory
  - Admin API integration/application inventory

Explicit gaps:
  - direct Duo API polling, SIEM connector envelope metadata, broader telephony and Trust Monitor variants,
    pagination/checkpoint behavior, and complete optional fields are not expected to pass until fixture/source-shape evidence is added.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S Cisco Duo Audit listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20088.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "cisco_duo|duo|splunk|hec|destination|source" | head -80 || true'
  echo "== Splunk readback summary =="
  compose exec -T --user splunk splunk /opt/splunk/bin/splunk search "${READBACK_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk readback count assertion =="
  local count_output count
  count_output="$(compose exec -T --user splunk splunk /opt/splunk/bin/splunk search "${COUNT_SPL}" -auth "admin:${SPLUNK_PASSWORD}")"
  printf '%s\n' "${count_output}"
  count="$(printf '%s\n' "${count_output}" | awk '/^[[:space:]]*[0-9]+[[:space:]]*$/ {value=$1} END {print value+0}')"
  if [[ "${count}" != "${EXPECTED_EVENT_COUNT}" ]]; then
    echo "ERROR: expected ${EXPECTED_EVENT_COUNT} indexed Cisco Duo Audit fixture events but Splunk returned ${count}" >&2
    return 1
  fi
  echo "== Splunk detail readback =="
  compose exec -T --user splunk splunk /opt/splunk/bin/splunk search "${DETAIL_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
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
