#!/usr/bin/env bash
set -euo pipefail

PACK_ID="f5_bigip"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-f5-bigip-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_F5_BIGIP_PORT:-20050}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
EXPECTED_EVENT_COUNT=9
READBACK_SPL='search index IN (netops, netwaf) "SC4S_F5_BIGIP_TEST_" earliest=-2h | stats count by index sourcetype source host | sort index sourcetype'
COUNT_SPL='search index IN (netops, netwaf) "SC4S_F5_BIGIP_TEST_" earliest=-2h | stats count'
DETAIL_SPL='search index IN (netops, netwaf) "SC4S_F5_BIGIP_TEST_" earliest=-2h | table _time index sourcetype source host vendor product action signature signature_id support_id policy_name unit_hostname violations f5_asm message_code severity src dest src_ip dest_ip pool dest_port pool_member_ip pool_member_port transport packet_rate f5_irule event_type method uri qname rcode reason member _raw'

usage() {
  cat <<'USAGE'
Usage: packs/f5_bigip/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable F5 BIG-IP TLS/RFC5425 pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/f5_bigip/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create netops/netwaf indexes.
  replay        Send every F5 BIG-IP fixture through the pack TLS/RFC5425 listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_F5_BIGIP_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed F5 BIG-IP syslog/iRule/ASM/access_json shapes. It is not production/field
  validation for a real BIG-IP appliance, BIG-IP version, module configuration, custom iRule
  payloads, TLS forwarding setup, or complete upstream F5 parser coverage.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_f5_bigip
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
      SC4S_LISTEN_F5_BIGIP_TLS_PORT: "20050"
      SOURCE_ALL_SET: F5_BIGIP
      SOURCE_ALL_SET_APPEND: F5_BIGIP
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20050/tcp"
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
  packs/f5_bigip/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/f5_bigip/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/f5_bigip/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/f5_bigip/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index netops -auth admin:\$SPLUNK_PASSWORD
  docker compose -f .tmp/e2e/f5_bigip/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index netwaf -auth admin:\$SPLUNK_PASSWORD
  SC4S_HOST=127.0.0.1 SC4S_PORT=${SC4S_HOST_PORT} packs/f5_bigip/scripts/send_tls_20050.sh
  docker compose -f .tmp/e2e/f5_bigip/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=netops/index=netwaf searchable.
  2. SC4S TEST healthy and listening on tls/${SC4S_HOST_PORT} for source_id F5_BIGIP.
  3. Replay sends 9 fixture events from test-events/f5_bigip_test_events.txt through TLS/RFC5425 octet-counted framing.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 9 events across the declared F5 TMM, ASM, iRule DNS/HTTP/LB, and access_json sourcetypes.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, raw preservation, F5 product fields, ASM support/policy/unit context, TMM message code/severity/traffic fields, DNS qname/rcode, HTTP/access-json fields, pool/member split, eventtypes/tags, and markers.

Fixture families covered:
  - bigip_syslog umbrella route
  - bigip_tmm_ssl / bigip_tmm_tcl / bigip_tmm_traffic
  - bigip_asm
  - bigip_irule_dns_request / bigip_irule_dns_response / bigip_irule_http / bigip_irule_lb_failed
  - bigip_access_json

Explicit gaps:
  - This harness does not prove live BIG-IP appliance emission, BIG-IP version/module behavior, TLS forwarding configuration, custom iRule payload completeness, ASM policy semantics, or full upstream F5 parser coverage.
  - It replays synthetic-equivalent fixtures through the declared listener; field validation with retained real source-version telemetry requires sanctioned BIG-IP samples or a non-production BIG-IP relay.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk add index netops -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_netops.log 2>&1 || true
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk add index netwaf -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_netwaf.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "F5 BIG-IP TLS listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  SC4S_HOST=127.0.0.1 SC4S_PORT="${SC4S_HOST_PORT}" "${PACK_DIR}/scripts/send_tls_20050.sh"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "f5|bigip|splunk|hec|destination|source" | head -120 || true'
  echo "== Splunk readback summary =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${READBACK_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk detail readback =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${DETAIL_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk readback count assertion =="
  local observed_count
  observed_count="$(compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${COUNT_SPL}" -auth "admin:${SPLUNK_PASSWORD}" -output csv | awk -F, 'NR==2 {gsub(/\r/, "", $1); print $1}')"
  if [[ "${observed_count}" != "${EXPECTED_EVENT_COUNT}" ]]; then
    echo "ERROR: expected ${EXPECTED_EVENT_COUNT} indexed F5 BIG-IP fixture events, observed ${observed_count:-0}" >&2
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
