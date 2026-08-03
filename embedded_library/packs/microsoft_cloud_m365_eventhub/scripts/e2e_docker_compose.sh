#!/usr/bin/env bash
set -euo pipefail

PACK_ID="microsoft_cloud_m365_eventhub"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-microsoft-cloud-m365-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_MICROSOFT_CLOUD_M365_EVENTHUB_PORT:-20061}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search (index=main OR index=netauth OR index=infraops OR index=netdlp OR index=epintel) "SC4S_MICROSOFT_CLOUD_TEST_" earliest=-2h | stats count by index sourcetype source host | sort index sourcetype'
DETAIL_SPL='search (index=main OR index=netauth OR index=infraops OR index=netdlp OR index=epintel) "SC4S_MICROSOFT_CLOUD_TEST_" earliest=-2h | table _time index sourcetype source vendor product ms_source_sourcetype operation action user src_ip result status risk_level risk_state risk_detail object app resource_group resource_provider sensitivity_label marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/microsoft_cloud_m365_eventhub/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Microsoft Cloud/M365 JSON relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/microsoft_cloud_m365_eventhub/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the routed indexes.
  replay        Send every Microsoft Cloud fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected index/sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_MICROSOFT_CLOUD_M365_EVENTHUB_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed one-line Microsoft Cloud/M365 JSON relay shape and declared M365,
  Exchange, SharePoint, Entra, Azure, Purview, Defender, and Intune families. It is not
  production/field validation for a real Microsoft tenant, Event Hub namespace, Cribl
  route, API collector, source-type catalogue, checkpointing, or export completeness.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_microsoft_cloud_m365_eventhub:ro
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
      SC4S_LISTEN_MICROSOFT_CLOUD_M365_EVENTHUB_TCP_PORT: "20061"
      SOURCE_ALL_SET: MICROSOFT_CLOUD_M365_EVENTHUB
      SOURCE_ALL_SET_APPEND: MICROSOFT_CLOUD_M365_EVENTHUB
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20061/tcp"
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
  packs/microsoft_cloud_m365_eventhub/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/microsoft_cloud_m365_eventhub/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/microsoft_cloud_m365_eventhub/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  for idx in main netauth infraops netdlp epintel; do docker compose -f .tmp/e2e/microsoft_cloud_m365_eventhub/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index \$idx -auth admin:\$SPLUNK_PASSWORD || true; done
  packs/microsoft_cloud_m365_eventhub/scripts/send_tcp_20061.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/microsoft_cloud_m365_eventhub/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and indexes main/netauth/infraops/netdlp/epintel searchable.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id MICROSOFT_CLOUD_M365_EVENTHUB.
  3. Replay sends 12 fixture events from test-events/microsoft_cloud_m365_eventhub_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 12 events across declared Microsoft Cloud/M365 indexes and sourcetypes.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, vendor/product, source sourcetype, operation/action, user/source IP, risk, object/resource, sensitivity label, marker, and raw JSON preservation.

Fixture families covered:
  - o365_management / exchange / sharepoint
  - entra_audit / entra_signin / entra_identityprotection
  - azure_resource / azure_activity
  - purview_dlp / purview_audit
  - defender / intune_audit

Explicit gaps:
  - This harness does not prove live Microsoft tenant export, Event Hub delivery, Cribl source-type preservation, API pagination/checkpoints, or collector wrapper completeness.
  - It replays synthetic-equivalent fixture JSON through the declared listener; field validation with retained real tenant/source-version telemetry requires sanctioned Microsoft samples or a non-production Microsoft relay.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  for idx in main netauth infraops netdlp epintel; do
    compose exec -T splunk /opt/splunk/bin/splunk add index "${idx}" -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_${idx}.log 2>&1 || true
  done
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "Microsoft Cloud listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20061.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "microsoft|splunk|hec|destination|source" | head -120 || true'
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
