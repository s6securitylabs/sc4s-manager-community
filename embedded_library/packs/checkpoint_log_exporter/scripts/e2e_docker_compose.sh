#!/usr/bin/env bash
set -euo pipefail

PACK_ID="checkpoint_log_exporter"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-checkpoint-log-exporter-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_CHECKPOINT_LOG_EXPORTER_PORT:-20041}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
EXPECTED_EVENT_COUNT=5
READBACK_SPL='search index=netfw "SC4S_CHECKPOINT_LOG_EXPORTER_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
COUNT_SPL='search index=netfw "SC4S_CHECKPOINT_LOG_EXPORTER_TEST_" earliest=-2h | stats count'
METADATA_ASSERT_SPL='search index=netfw "SC4S_CHECKPOINT_LOG_EXPORTER_TEST_" earliest=-2h | stats count AS total count(eval(index!="netfw" OR sourcetype!="cp_log:syslog" OR source!="checkpoint_log_exporter")) AS metadata_mismatches'
DETAIL_SPL='search index=netfw "SC4S_CHECKPOINT_LOG_EXPORTER_TEST_" earliest=-2h | table _time index sourcetype source vendor product vendor_raw_action action signature signature_id src src_ip s_port src_port dst dest_ip service dest_port proto transport user administrator client_ip rule_name rule_uid protection_id protection_name attack blade marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/checkpoint_log_exporter/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Check Point Log Exporter SC4S TEST -> Splunk TEST harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/checkpoint_log_exporter/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the netfw index.
  replay        Send every RFC5424/RFC5425 fixture through the pack TLS listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_CHECKPOINT_LOG_EXPORTER_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed Check Point Log Exporter RFC5424 structured-data source shape. It is not field
  validation for a real Check Point gateway, management server, MTA, blade/version, collector, or
  proprietary Splunk TA deployment.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_checkpoint_log_exporter
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
      SC4S_LISTEN_CHECKPOINT_LOG_EXPORTER_TLS_PORT: "20041"
      SOURCE_ALL_SET: CHECKPOINT_LOG_EXPORTER
      SOURCE_ALL_SET_APPEND: CHECKPOINT_LOG_EXPORTER
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20041/tcp"
    volumes:
      - ${PACK_DIR}/sc4s/app_parsers/syslog:/opt/sc4s/local/config/app_parsers/syslog:ro
      - sc4s-var:/var/lib/syslog-ng
    healthcheck:
      test: ["CMD-SHELL", "pgrep -x syslog-ng >/dev/null 2>&1 && syslog-ng-ctl stats >/tmp/sc4s-stats.out 2>&1 && ! grep -q 'Error connecting control socket' /tmp/sc4s-stats.out && netstat -ltn 2>/dev/null | grep -q ':20041 '"]
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
  packs/checkpoint_log_exporter/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/checkpoint_log_exporter/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/checkpoint_log_exporter/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/checkpoint_log_exporter/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index netfw -auth admin:\$SPLUNK_PASSWORD || true
  docker compose -f .tmp/e2e/checkpoint_log_exporter/compose.yaml -p ${PROJECT} exec -T -u splunk splunk /opt/splunk/bin/splunk list index netfw -auth admin:\$SPLUNK_PASSWORD
  packs/checkpoint_log_exporter/scripts/send_tls_20041.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/checkpoint_log_exporter/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=netfw present.
  2. SC4S TEST healthy and listening on TLS/RFC5425 tcp/${SC4S_HOST_PORT} for source_id CHECKPOINT_LOG_EXPORTER.
  3. Replay sends 5 fixture events from test-events/checkpoint_log_exporter_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 5 events in cp_log:syslog with source checkpoint_log_exporter.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, action, rule, IPS, audit, email-security, source/destination, and transport fields.

Fixture families covered:
  - log_exporter_syslog / firewall_traffic / ips_protection / audit_activity / email_security -> cp_log:syslog

Explicit gaps:
  - This harness does not prove a real Check Point gateway, management server, MTA, blade/version, collector wrapper, or proprietary Splunk TA deployment.
  - TCP/RFC5424 production mode remains a deployment variant; this disposable harness exercises the included dedicated TLS/RFC5425 listener helper.
  - Field validation with retained real product/source-version telemetry is not expected to pass until sanctioned samples or a non-production Check Point test feed are captured.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk add index netfw -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk list index netfw -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_list_index.log
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S Check Point Log Exporter TLS listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tls_20041.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "checkpoint|cp_log|splunk|hec|destination|source" | head -120 || true'
  echo "== Splunk readback summary =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${READBACK_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk detail readback =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${DETAIL_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk readback count assertion =="
  local observed_count
  observed_count="$(compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${COUNT_SPL}" -auth "admin:${SPLUNK_PASSWORD}" -output csv | awk -F, 'NR==2 {gsub(/\r/, "", $1); print $1}')"
  if [[ "${observed_count}" != "${EXPECTED_EVENT_COUNT}" ]]; then
    echo "ERROR: expected ${EXPECTED_EVENT_COUNT} indexed Check Point Log Exporter fixture events, observed ${observed_count:-0}" >&2
    return 1
  fi
  echo "== Splunk readback metadata assertion =="
  local metadata_result metadata_total metadata_mismatches
  metadata_result="$(compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${METADATA_ASSERT_SPL}" -auth "admin:${SPLUNK_PASSWORD}" -output csv | awk -F, 'NR==2 {gsub(/[\"\r]/, "", $1); gsub(/[\"\r]/, "", $2); print $1 "," $2}')"
  IFS=, read -r metadata_total metadata_mismatches <<<"${metadata_result}"
  if [[ "${metadata_total:-0}" != "${EXPECTED_EVENT_COUNT}" || "${metadata_mismatches:-0}" != "0" ]]; then
    echo "ERROR: observed ${metadata_mismatches:-unknown} Check Point Log Exporter events with wrong index, sourcetype, or source (total ${metadata_total:-0})" >&2
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
