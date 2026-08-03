#!/usr/bin/env bash
set -euo pipefail

PACK_ID="crowdstrike_falcon"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-crowdstrike-falcon-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_CROWDSTRIKE_FALCON_PORT:-20076}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=epintel "SC4S_CROWDSTRIKE_FALCON_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
DETAIL_SPL='search index=epintel "SC4S_CROWDSTRIKE_FALCON_TEST_" earliest=-2h | table _time index sourcetype source vendor product vendor_product crowdstrike_event_simpleName action signature crowdstrike_aid crowdstrike_cid device_id agent_version device_name dest host_status platform_name os_version first_seen last_seen external_ip local_ip device_tags vulnerability_id cve_id vulnerability_status severity remediation affected_product affected_version indicator_value indicator_type indicator_confidence indicator_tags threat_actor malware_family kill_chain_phase threat_type target_region published_date last_updated identity_incident_id detect_id detect_name detect_description severity_name tactic technique objective endpoint_ip policy_name rule_name rule_action response_action destination data_volume operation service result session_id session_start session_end event_utc_timestamp os_platform user user_domain process process_id process_command_line parent_process parent_process_id src_ip src_port dest_ip dest_port transport dns_request_type query url file_path file_name file_identifier file_access_type file_size file_hash containment_state sensor_state config_build config_state_hash config_state_data user_id marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/crowdstrike_falcon/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable CrowdStrike Falcon Platform JSON relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/crowdstrike_falcon/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the epintel index.
  replay        Send every CrowdStrike Falcon fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_CROWDSTRIKE_FALCON_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed one-line CrowdStrike Falcon JSON relay shape and declared platform families. It is
  not production or field validation for a live Falcon tenant, FDR S3/SQS custody, API credential
  handling, Event Streams receiver delivery, native API pagination/envelope unwrapping, or complete
  Falcon platform coverage.
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_crowdstrike_falcon:ro
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
      SC4S_LISTEN_CROWDSTRIKE_FALCON_TCP_PORT: "20076"
      SOURCE_ALL_SET: CROWDSTRIKE_FALCON
      SOURCE_ALL_SET_APPEND: CROWDSTRIKE_FALCON
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20076/tcp"
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
  packs/crowdstrike_falcon/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/crowdstrike_falcon/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/crowdstrike_falcon/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/crowdstrike_falcon/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index epintel -auth admin:\$SPLUNK_PASSWORD
  packs/crowdstrike_falcon/scripts/send_tcp_20076.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/crowdstrike_falcon/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=epintel searchable.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id CROWDSTRIKE_FALCON.
  3. Replay sends 23 fixture events from test-events/crowdstrike_falcon_test_events.jsonl.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 23 events across the declared Falcon FDR/API/Event Streams sourcetypes.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, vendor/product, source-mode
     tokens, endpoint/process/network/DNS/file/device/vulnerability/intelligence/audit/RTR/identity/
     detection/policy fields, markers, and raw JSON preservation.

Fixture families covered:
  - process
  - network
  - dns
  - file
  - asset
  - devices_api
  - spotlight_api
  - eventstream_audit
  - eventstream_rtr
  - intel_api
  - eventstream_identity
  - eventstream_detection
  - eventstream_policy

Explicit gaps:
  - This harness does not prove live CrowdStrike tenant, FDR S3/SQS, Event Streams receiver, or API collector delivery.
  - It does not prove API credential custody, pagination/checkpointing, native API array/envelope unwrapping,
    collector retry/dedup behavior, RTR command/action rows, admin policy-change audit rows, Intelligence
    report events, or complete Falcon platform coverage.
  - It replays synthetic-equivalent fixture JSON through the declared listener; field validation with retained
    real tenant/source-version telemetry requires sanctioned Falcon samples or a non-production relay.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk add index epintel -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "CrowdStrike Falcon listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20076.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "crowdstrike|falcon|splunk|hec|destination|source" | head -160 || true'
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
