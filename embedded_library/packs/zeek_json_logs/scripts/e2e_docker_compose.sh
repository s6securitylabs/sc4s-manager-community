#!/usr/bin/env bash
set -euo pipefail

PACK_ID="zeek_json_logs"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-zeek-json-logs-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_ZEEK_JSON_LOGS_PORT:-20083}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=netids "SC4S_ZEEK_JSON_TEST_" earliest=-2h | stats count by sourcetype source host zeek_log_type | sort zeek_log_type'
DETAIL_SPL='search index=netids "SC4S_ZEEK_JSON_TEST_" earliest=-2h | table _time index sourcetype source host vendor product zeek_log_type uid src_ip src src_port dest_ip dest dest_port transport action signature signature_id dns_query dns_query_type http_method http_status url tls_sni tls_version bytes_in bytes_out file_id file_name file_mime_type file_seen_bytes file_total_bytes file_md5 x509_id x509_subject x509_issuer x509_serial x509_not_valid_before x509_not_valid_after ssh_auth_success ssh_client ssh_server ssh_cipher_alg ssh_host_key_alg dhcp_client_addr dhcp_server_addr dhcp_mac dhcp_host_name dhcp_assigned_addr dhcp_msg_types rdp_cookie rdp_result rdp_security_protocol rdp_client_name weird_name weird_addl weird_notice weird_source software_host software_port software_type software_name software_version known_host intel_indicator intel_indicator_type intel_seen_where intel_matched_types intel_sources smtp_helo smtp_mailfrom smtp_rcptto smtp_subject smtp_last_reply marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/zeek_json_logs/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Zeek JSON relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/zeek_json_logs/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the netids index.
  replay        Send every Zeek JSON fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected Zeek family coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_ZEEK_JSON_LOGS_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed source shape. It is not production/field validation and must not promote
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_zeek_json_logs:ro
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
      SC4S_LISTEN_ZEEK_JSON_LOGS_TCP_PORT: "20083"
      SOURCE_ALL_SET: ZEEK_JSON_LOGS
      SOURCE_ALL_SET_APPEND: ZEEK_JSON_LOGS
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20083/tcp"
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
  packs/zeek_json_logs/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/zeek_json_logs/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/zeek_json_logs/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/zeek_json_logs/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index netids -auth admin:\$SPLUNK_PASSWORD || true
  packs/zeek_json_logs/scripts/send_tcp_20083.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/zeek_json_logs/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=netids present.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id ZEEK_JSON_LOGS.
  3. Replay sends 15 fixture events from test-events/zeek_json_logs_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 15 events across Zeek conn, dns, http, ssl, notice, files, x509, ssh, dhcp, rdp, weird, software, known_hosts, intel, and smtp fixture families.
  6. Detail SPL verifies count, index, sourcetype, source, host, timestamp and required Zeek family fields.

Fixture families covered:
  - conn -> zeek:json
  - dns -> zeek:json
  - http -> zeek:json
  - ssl -> zeek:json
  - notice -> zeek:json
  - files -> zeek:json
  - x509 -> zeek:json
  - ssh -> zeek:json
  - dhcp -> zeek:json
  - rdp -> zeek:json
  - weird -> zeek:json
  - software -> zeek:json
  - known_hosts -> zeek:json
  - intel -> zeek:json
  - smtp -> zeek:json

Explicit gaps:
  - live Zeek sensor/source-version emission and LogAscii timestamp/optional-field behavior are not proven by this harness.
  - collector wrappers, file-tail buffering, syslog envelope rewrites, and Cribl/Fluent Bit/Vector delivery semantics remain unverified.
  - Zeek TSV logs, package-specific logs, local policy extensions, and real PCAP-derived traffic/source coverage remain deferred until exact source-shape evidence is added.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk add index netids -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S Zeek JSON listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20083.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "zeek|json|splunk|hec|destination|source" | head -80 || true'
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
