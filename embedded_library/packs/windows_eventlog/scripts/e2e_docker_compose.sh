#!/usr/bin/env bash
set -euo pipefail

PACK_ID="windows_eventlog"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-windows-eventlog-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_WINDOWS_EVENTLOG_PORT:-20063}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=oswinsec "SC4S_WINDOWS_EVENTLOG_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=oswinsec "SC4S_WINDOWS_EVENTLOG_TEST_" earliest=-2h | table _time index sourcetype source vendor product event_id signature signature_id provider user user_domain src_user src_user_domain src_ip src_port logon_type workstation package_name service_sid ticket_options ticket_encryption_type pre_auth_type failure_code logon_guid transmitted_services cert_issuer_name cert_serial_number cert_thumbprint failure_reason status sub_status object_name object_type access_mask access_list object_process audit_policy_changes policy_category policy_subcategory service_name service_file_name service_type service_start_type service_account target_sid member_name member_sid subject_logon_id task_name task_content display_name user_principal_name sam_account_name user_account_control dest process process_command_line parent_process script_block_text threat_name file_path severity marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/windows_eventlog/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Windows Event XML relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/windows_eventlog/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the oswinsec index.
  replay        Send every Windows Event XML fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_WINDOWS_EVENTLOG_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed one-line Windows Event XML relay shape and declared Security, process,
  PowerShell, and Defender sourcetypes. It is not production/field validation for a real
  Windows domain/controller/endpoint, WEF/WEC/NXLog/Fluent Bit/Cribl relay, native EVTX,
  collector-normalized JSON, multiline XML export, or complete Windows TA parity.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_windows_eventlog:ro
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
      SC4S_LISTEN_WINDOWS_EVENTLOG_TCP_PORT: "20063"
      SOURCE_ALL_SET: WINDOWS_EVENTLOG
      SOURCE_ALL_SET_APPEND: WINDOWS_EVENTLOG
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20063/tcp"
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
  packs/windows_eventlog/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/windows_eventlog/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/windows_eventlog/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/windows_eventlog/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index oswinsec -auth admin:\$SPLUNK_PASSWORD
  packs/windows_eventlog/scripts/send_tcp_20063.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/windows_eventlog/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=oswinsec searchable.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id WINDOWS_EVENTLOG.
  3. Replay sends 18 fixture events from test-events/windows_eventlog_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 18 events across windows:eventlog:security, windows:eventlog:process, windows:eventlog:powershell, and windows:eventlog:defender sourcetypes.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, EventID/provider, user/source/process/script/Defender/Kerberos/NTLM/object/policy/service/task fields, marker, and raw XML preservation.

Fixture families covered:
  - security logon/authentication/Kerberos/NTLM/account/group/object/policy/service/log/task audit
  - process creation
  - PowerShell script block
  - Microsoft Defender detection

Explicit gaps:
  - This harness does not prove live Windows Event Log emission, WEF/WEC/NXLog/Fluent Bit/Cribl wrappers, native EVTX, collector-normalized JSON, multiline XML exports, or complete Windows provider coverage.
  - It replays synthetic-equivalent fixture XML through the declared listener; field validation with retained real product/source-version telemetry requires sanctioned Windows relay samples or a non-production Windows feed.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk add index oswinsec -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "Windows Event Log listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20063.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "windows|eventlog|splunk|hec|destination|source" | head -120 || true'
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
