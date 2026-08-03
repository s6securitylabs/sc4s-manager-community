#!/usr/bin/env bash
set -euo pipefail

PACK_ID="google_cloud_workspace_audit"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-google-cloud-workspace-audit-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_GOOGLE_CLOUD_WORKSPACE_AUDIT_PORT:-20111}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=main "SC4S_GOOGLE_CLOUD_WORKSPACE_AUDIT_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=main "SC4S_GOOGLE_CLOUD_WORKSPACE_AUDIT_TEST_" earliest=-2h | table _time index sourcetype source host vendor product google_audit_family cloud_project gcp_service method app user src_user src_ip action signature signature_id resource_name status gcp_permission gcp_permission_granted workspace_oauth_app workspace_oauth_client_id workspace_oauth_client_type workspace_group_email workspace_member_email workspace_member_role workspace_calendar_id workspace_calendar_access_level workspace_calendar_grantee_email workspace_saml_application workspace_saml_failure_type marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/google_cloud_workspace_audit/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Google Cloud / Workspace audit JSON relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/google_cloud_workspace_audit/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and ensure index=main is searchable.
  replay        Send every Google Cloud / Workspace fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_GOOGLE_CLOUD_WORKSPACE_AUDIT_PORT, SPLUNK_WEB_PORT,
  SPLUNK_MGMT_PORT, SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR,
  SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for
  the fixture-backed one-line Google Cloud AuditLog / Workspace Reports Activity JSON
  relay shape and declared audit families. It is not production or field validation for
  a real Google Cloud project, Workspace tenant, Pub/Sub/API/export collector, credential
  custody, pagination/checkpointing path, or export completeness.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_google_cloud_workspace_audit:ro
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
      SC4S_LISTEN_GOOGLE_CLOUD_WORKSPACE_AUDIT_TCP_PORT: "20111"
      SOURCE_ALL_SET: GOOGLE_CLOUD_WORKSPACE_AUDIT
      SOURCE_ALL_SET_APPEND: GOOGLE_CLOUD_WORKSPACE_AUDIT
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20111/tcp"
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
  packs/google_cloud_workspace_audit/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/google_cloud_workspace_audit/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/google_cloud_workspace_audit/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/google_cloud_workspace_audit/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk list index main -auth admin:\$SPLUNK_PASSWORD
  packs/google_cloud_workspace_audit/scripts/send_tcp_20111.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/google_cloud_workspace_audit/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=main searchable.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id GOOGLE_CLOUD_WORKSPACE_AUDIT.
  3. Replay sends 12 fixture events from test-events/google_cloud_workspace_audit_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 12 events with sourcetype google:audit:json and source/host context.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, vendor/product,
     Google audit family, project/service/method/app, user/source IP, action/signature,
     permission/grant, Workspace OAuth/Groups/Calendar/SAML context, marker, and raw JSON preservation.

Fixture families covered:
  - GCP Admin Activity / Data Access / System Event / Policy Denied
  - Workspace login / admin / Drive / OAuth token / Groups / Calendar ACL / SAML

Explicit gaps:
  - This harness does not prove live Google Cloud project or Workspace tenant emission, Pub/Sub/API/export collector behavior, credential custody, pagination/checkpoints, destination envelope metadata, or export completeness.
  - It replays synthetic-equivalent fixture JSON through the declared listener; field validation with retained real source-version telemetry requires sanctioned Google samples or a non-production Google relay.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk list index main -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_main_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "Google Cloud / Workspace audit listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20111.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "google|workspace|audit|splunk|hec|destination|source" | head -120 || true'
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
