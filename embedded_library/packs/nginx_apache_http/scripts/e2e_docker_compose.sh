#!/usr/bin/env bash
set -euo pipefail

PACK_ID="nginx_apache_http"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-nginx-apache-http-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_NGINX_APACHE_HTTP_PORT:-20075}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=netops "SC4S_NGINX_APACHE_HTTP_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=netops "SC4S_NGINX_APACHE_HTTP_TEST_" earliest=-2h | table _time index sourcetype source host vendor product vendor_product eventtype src_ip src client_ip client_port user ident http_method uri_path url http_version status bytes bytes_out http_referrer http_user_agent error_level module error_code pid tid connection_id server host_header request error_message action signature signature_id marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/nginx_apache_http/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Nginx / Apache HTTP SC4S TEST -> Splunk TEST harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/nginx_apache_http/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the netops index.
  replay        Send every fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_NGINX_APACHE_HTTP_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed Nginx combined, Apache common/combined, Nginx error, and Apache error
  source shapes. It is not field validation for real web-server versions, custom log formats,
  collector wrappers, reverse-proxy timing extensions, or source-local timezone behavior.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_nginx_apache_http:ro
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
      SC4S_LISTEN_NGINX_APACHE_HTTP_TCP_PORT: "20075"
      SOURCE_ALL_SET: NGINX_APACHE_HTTP
      SOURCE_ALL_SET_APPEND: NGINX_APACHE_HTTP
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20075/tcp"
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
  packs/nginx_apache_http/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/nginx_apache_http/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/nginx_apache_http/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/nginx_apache_http/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index netops -auth admin:\$SPLUNK_PASSWORD || true
  SC4S_TEST_HOST=127.0.0.1 SC4S_TEST_PORT=${SC4S_HOST_PORT} packs/nginx_apache_http/scripts/send_tcp_20075.sh
  docker compose -f .tmp/e2e/nginx_apache_http/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=netops present.
  2. SC4S TEST healthy and listening on TCP/${SC4S_HOST_PORT} for source_id NGINX_APACHE_HTTP.
  3. Replay sends 5 fixture events from test-events/nginx_apache_http_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 5 events across nginx:access:combined, apache:httpd:access:common, apache:httpd:access:combined, nginx:error, and apache:httpd:error with source nginx_apache_http.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, HTTP access fields, error-log fields, eventtypes/tags, and normalized signatures/actions.

Fixture families covered:
  - nginx_combined -> nginx:access:combined (SC4S_NGINX_APACHE_HTTP_TEST_NGINX_COMBINED_001)
  - apache_common -> apache:httpd:access:common (SC4S_NGINX_APACHE_HTTP_TEST_APACHE_COMMON_002)
  - apache_combined -> apache:httpd:access:combined (SC4S_NGINX_APACHE_HTTP_TEST_APACHE_COMBINED_003)
  - nginx_error -> nginx:error (SC4S_NGINX_APACHE_HTTP_TEST_NGINX_ERROR_004)
  - apache_error -> apache:httpd:error (SC4S_NGINX_APACHE_HTTP_TEST_APACHE_ERROR_005)

Explicit gaps:
  - This harness does not prove real Nginx or Apache httpd source-version emission, local log_format/ErrorLogFormat customization, reverse-proxy timing fields, WAF/security modules, or collector wrapper behavior.
  - Headerless file-tail and RFC5424/syslog-wrapped production variants remain deployment variants; this disposable harness exercises the included TCP listener helper with synthetic-equivalent fixture lines.
  - Field validation with retained real product/source-version telemetry is not expected to pass until sanctioned server samples or a non-production web-server test feed are captured.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk add index netops -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S Nginx / Apache HTTP TCP listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  SC4S_TEST_HOST=127.0.0.1 SC4S_TEST_PORT="${SC4S_HOST_PORT}" "${PACK_DIR}/scripts/send_tcp_20075.sh"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "nginx|apache|http|splunk|hec|destination|source" | head -120 || true'
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
