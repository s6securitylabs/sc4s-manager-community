#!/usr/bin/env bash
set -euo pipefail

PACK_ID="aws_cloud_audit_security"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-aws-cloud-audit-security-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_AWS_CLOUD_AUDIT_SECURITY_PORT:-20068}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
EXPECTED_EVENT_COUNT=10
READBACK_SPL='search index=main "SC4S_AWS_CLOUD_AUDIT_SECURITY_TEST_" earliest=-2h | stats count by sourcetype source host | sort sourcetype'
COUNT_SPL='search index=main "SC4S_AWS_CLOUD_AUDIT_SECURITY_TEST_" earliest=-2h | stats count'
METADATA_ASSERT_SPL='search index=main "SC4S_AWS_CLOUD_AUDIT_SECURITY_TEST_" earliest=-2h | stats count AS total count(eval(index!="main" OR NOT in(sourcetype,"aws:cloud:cloudtrail","aws:cloud:guardduty","aws:cloud:vpcflow") OR source!="aws_cloud_audit_security")) AS metadata_mismatches'
DETAIL_SPL='search index=main "SC4S_AWS_CLOUD_AUDIT_SECURITY_TEST_" earliest=-2h | table _time index sourcetype source host vendor product aws_family aws_account_id aws_region eventName eventSource user src_user src_ip user_agent action role_name policy_arn function_name instance_id bucket object_key severity signature signature_id resource_id interface_id packets bytes log_status marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/aws_cloud_audit_security/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable AWS Cloud Audit and Security relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/aws_cloud_audit_security/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and use index=main for read-back.
  replay        Send every AWS fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected sourcetype coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_AWS_CLOUD_AUDIT_SECURITY_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
  SPLUNK_HEC_PORT, SECHUB_E2E_WORK_DIR, SECHUB_E2E_PROJECT.

Evidence boundary:
  Passing this harness is SC4S TEST -> Splunk TEST replay/read-back evidence only for the
  fixture-backed AWS CloudTrail, GuardDuty, and VPC Flow relay shapes. It is not production
  or field validation for a real AWS account, collector, EventBridge, S3/SQS, Firehose, or Cribl path.
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
      # This disposable harness mounts the pack app writable so bootstrap can
      # complete; do not treat the generated compose file as production guidance.
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_aws_cloud_audit_security
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
      SC4S_LISTEN_AWS_CLOUD_AUDIT_SECURITY_TCP_PORT: "20068"
      SOURCE_ALL_SET: AWS_CLOUD_AUDIT_SECURITY
      SOURCE_ALL_SET_APPEND: AWS_CLOUD_AUDIT_SECURITY
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20068/tcp"
    volumes:
      - ${PACK_DIR}/sc4s/app_parsers/syslog:/opt/sc4s/local/config/app_parsers/syslog:ro
      - sc4s-var:/var/lib/syslog-ng
    healthcheck:
      test: ["CMD-SHELL", "pgrep -x syslog-ng >/dev/null 2>&1 && syslog-ng-ctl stats >/tmp/sc4s-stats.out 2>&1 && ! grep -q 'Error connecting control socket' /tmp/sc4s-stats.out && netstat -ltn 2>/dev/null | grep -q ':20068 '"]
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
  packs/aws_cloud_audit_security/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/aws_cloud_audit_security/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/aws_cloud_audit_security/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  packs/aws_cloud_audit_security/scripts/send_tcp_20068.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/aws_cloud_audit_security/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=main searchable.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id AWS_CLOUD_AUDIT_SECURITY.
  3. Replay sends 10 fixture events from test-events/aws_cloud_audit_security_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 10 events across aws:cloud:cloudtrail, aws:cloud:guardduty, and aws:cloud:vpcflow.
  6. Detail SPL verifies count, index, sourcetype, source, timestamp, AWS account/region, CloudTrail, GuardDuty, and VPC Flow fields.

Fixture families covered:
  - cloudtrail_management / cloudtrail_data / cloudtrail_discovery / cloudtrail_iam_escalation / cloudtrail_execution_staging / cloudtrail_s3_impact -> aws:cloud:cloudtrail
  - guardduty_finding -> aws:cloud:guardduty
  - vpc_flow_log -> aws:cloud:vpcflow

Explicit gaps:
  - This harness does not prove any live AWS account, EventBridge, Firehose, S3/SQS, CloudWatch, Cribl, or collector envelope.
  - VPC Flow custom log formats, S3 server-access logs, Cost and Usage Reports, Security Hub wrappers, and AWS service-specific records outside the fixtures remain out of scope.
  - Field validation with retained real tenant/product telemetry is not expected to pass until sanctioned samples or a non-production AWS test feed are captured.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S AWS Cloud Audit and Security listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20068.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "aws_cloud_audit_security|aws|splunk|hec|destination|source" | head -120 || true'
  echo "== Splunk readback summary =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${READBACK_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk detail readback =="
  compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${DETAIL_SPL}" -auth "admin:${SPLUNK_PASSWORD}"
  echo "== Splunk readback count assertion =="
  local observed_count
  observed_count="$(compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${COUNT_SPL}" -auth "admin:${SPLUNK_PASSWORD}" -output csv | awk -F, 'NR==2 {gsub(/\r/, "", $1); print $1}')"
  if [[ "${observed_count}" != "${EXPECTED_EVENT_COUNT}" ]]; then
    echo "ERROR: expected ${EXPECTED_EVENT_COUNT} indexed AWS Cloud Audit and Security fixture events, observed ${observed_count:-0}" >&2
    return 1
  fi
  echo "== Splunk readback metadata assertion =="
  local metadata_result metadata_total metadata_mismatches
  metadata_result="$(compose exec -T -u splunk splunk /opt/splunk/bin/splunk search "${METADATA_ASSERT_SPL}" -auth "admin:${SPLUNK_PASSWORD}" -output csv | awk -F, 'NR==2 {gsub(/[\"\r]/, "", $1); gsub(/[\"\r]/, "", $2); print $1 "," $2}')"
  IFS=, read -r metadata_total metadata_mismatches <<<"${metadata_result}"
  if [[ "${metadata_total:-0}" != "${EXPECTED_EVENT_COUNT}" || "${metadata_mismatches:-0}" != "0" ]]; then
    echo "ERROR: observed ${metadata_mismatches:-unknown} AWS Cloud Audit and Security events with wrong index, sourcetype, or source (total ${metadata_total:-0})" >&2
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
