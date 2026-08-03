#!/usr/bin/env bash
set -euo pipefail

PACK_ID="windows_sysmon"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-windows-sysmon-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_WINDOWS_SYSMON_PORT:-20071}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=oswinsec "SC4S_WINDOWS_SYSMON_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=oswinsec "SC4S_WINDOWS_SYSMON_TEST_" earliest=-2h | table _time index sourcetype source vendor product event_id provider channel record_id computer user process_guid process_id process_path process_name command_line parent_process_guid parent_process_path parent_command_line hashes sha256 md5 src_ip src_port dest_ip dest_port dest_host transport initiated image_loaded loaded_driver signed file_signature signature_status source_process_guid source_process_id source_process_path source_process_name target_process_guid target_process_id target_process_path target_process_name new_thread_id start_address start_module start_function granted_access call_trace target_filename file_path file_name creation_utc_time previous_creation_utc_time query_name query_status query_results is_executable archived delete_detected target_object registry_event_type registry_details registry_new_name pipe_name device clipboard_session client_info wmi_event_type wmi_operation wmi_namespace wmi_name wmi_query wmi_type wmi_destination wmi_consumer wmi_filter tamper_type action signature signature_id marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/windows_sysmon/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Windows Sysmon XML relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/windows_sysmon/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the oswinsec index.
  replay        Send every Windows Sysmon XML fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_WINDOWS_SYSMON_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed one-line Windows Sysmon XML relay shape and declared Sysmon sourcetypes.
  It is not production/field validation for a real Windows endpoint, Sysmon configuration,
  WEF/WEC/NXLog/Fluent Bit/Cribl relay, native EVTX, collector-normalized JSON, multiline
  XML export, or complete Sysmon/Splunk Windows TA parity.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_windows_sysmon:ro
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
      SC4S_LISTEN_WINDOWS_SYSMON_TCP_PORT: "20071"
      SOURCE_ALL_SET: WINDOWS_SYSMON
      SOURCE_ALL_SET_APPEND: WINDOWS_SYSMON
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20071/tcp"
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
  packs/windows_sysmon/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/windows_sysmon/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/windows_sysmon/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/windows_sysmon/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index oswinsec -auth admin:\$SPLUNK_PASSWORD
  packs/windows_sysmon/scripts/send_tcp_20071.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/windows_sysmon/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=oswinsec searchable.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id WINDOWS_SYSMON.
  3. Replay sends 22 fixture events from test-events/windows_sysmon_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 22 events across windows:sysmon:* sourcetypes.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, EventID/provider/channel, process/network/file/DNS/registry/pipe/WMI/driver/raw-access/clipboard/tampering fields, eventtypes/tags, marker, and raw XML preservation.

Fixture families covered:
  - process creation, remote thread, process access, process tampering
  - network connection and DNS query
  - file creation, file time change, file deletion, and delete-detected
  - driver load, image load, raw access, clipboard, registry, named pipe, and WMI activity

Explicit gaps:
  - This harness does not prove live Sysmon endpoint emission, Sysmon configuration policy, WEF/WEC/NXLog/Fluent Bit/Cribl wrappers, native EVTX, collector-normalized JSON, multiline XML exports, or complete Sysmon provider coverage.
  - It replays synthetic-equivalent fixture XML through the declared listener; field validation with retained real product/source-version telemetry requires sanctioned Windows Sysmon relay samples or a non-production Windows feed.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk add index oswinsec -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "Windows Sysmon listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20071.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "windows|sysmon|splunk|hec|destination|source" | head -120 || true'
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
