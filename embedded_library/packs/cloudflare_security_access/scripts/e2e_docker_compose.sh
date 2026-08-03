#!/usr/bin/env bash
set -euo pipefail

PACK_ID="cloudflare_security_access"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-cloudflare-security-access-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_CLOUDFLARE_SECURITY_ACCESS_PORT:-20081}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=netwaf "SC4S_CLOUDFLARE_SECURITY_ACCESS_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=netwaf "SC4S_CLOUDFLARE_SECURITY_ACCESS_TEST_" earliest=-2h | table _time index sourcetype source vendor product cloudflare_family ray_id user src_ip src_internal_ip dest uri url http_method http_user_agent status cache_status action signature signature_id rule_id ruleset_id rule_message policy_id policy_name service_token_id session_id dest_ip dest_port src_port transport app sni query query_type resolver_decision resource_id resource_type resource_name interface event_id virtual_network_id virtual_network_name marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/cloudflare_security_access/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Cloudflare JSON relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/cloudflare_security_access/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the netwaf index.
  replay        Send every Cloudflare fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_CLOUDFLARE_SECURITY_ACCESS_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed one-line Cloudflare JSON relay shape and declared HTTP request, WAF,
  Access, Gateway DNS/HTTP/Network, and audit-log families. It is not production/field
  validation for a real Cloudflare tenant, Logpush job, Zero Trust account, collector
  wrapper, selected-field configuration, or API/export completeness.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_cloudflare_security_access:ro
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
      SC4S_LISTEN_CLOUDFLARE_SECURITY_ACCESS_TCP_PORT: "20081"
      SOURCE_ALL_SET: CLOUDFLARE_SECURITY_ACCESS
      SOURCE_ALL_SET_APPEND: CLOUDFLARE_SECURITY_ACCESS
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20081/tcp"
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
  packs/cloudflare_security_access/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/cloudflare_security_access/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/cloudflare_security_access/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/cloudflare_security_access/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index netwaf -auth admin:\$SPLUNK_PASSWORD
  SC4S_TEST_HOST=127.0.0.1 SC4S_TEST_PORT=${SC4S_HOST_PORT} packs/cloudflare_security_access/scripts/send_tcp_20081.sh
  docker compose -f .tmp/e2e/cloudflare_security_access/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=netwaf searchable.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id CLOUDFLARE_SECURITY_ACCESS.
  3. Replay sends 7 fixture events from test-events/cloudflare_security_access_test_events.jsonl.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 7 events across cloudflare:http:request, cloudflare:waf:event, cloudflare:access:request, cloudflare:gateway:dns, cloudflare:gateway:http, cloudflare:gateway:network, and cloudflare:audit sourcetypes.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, Cloudflare family, Ray/request IDs, user/device/source context, WAF/action fields, Gateway policy/network fields, audit actor/resource fields, marker, and raw JSON preservation.

Fixture families covered:
  - http_request / waf_event / access_request
  - gateway_dns / gateway_http / gateway_network
  - audit_log

Explicit gaps:
  - This harness does not prove live Cloudflare Logpush/Zero Trust delivery, account-plan enabled fields, selected-field job differences, object-store/API collector wrappers, or tenant export completeness.
  - It replays synthetic-equivalent fixture JSON through the declared listener; field validation with retained real tenant/source-version telemetry requires sanctioned Cloudflare samples or a non-production Cloudflare relay.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk add index netwaf -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "Cloudflare listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  SC4S_TEST_HOST=127.0.0.1 SC4S_TEST_PORT="${SC4S_HOST_PORT}" "${PACK_DIR}/scripts/send_tcp_20081.sh"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "cloudflare|splunk|hec|destination|source" | head -120 || true'
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
