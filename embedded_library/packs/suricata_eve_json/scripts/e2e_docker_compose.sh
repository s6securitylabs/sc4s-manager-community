#!/usr/bin/env bash
set -euo pipefail

PACK_ID="suricata_eve_json"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "${PACK_DIR}/../.." && pwd)"
WORK_DIR="${SECHUB_E2E_WORK_DIR:-${ROOT_DIR}/.tmp/e2e/${PACK_ID}}"
PROJECT="${SECHUB_E2E_PROJECT:-sechub-suricata-eve-json-e2e}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:-SechubE2E-ChangeMe-12345}"
HEC_TOKEN_ENV_VAR="${HEC_TOKEN_ENV_VAR:-SPLUNK_HEC_TOKEN}"
HEC_TOKEN_VALUE="${!HEC_TOKEN_ENV_VAR:-}"
SPLUNK_IMAGE="${SPLUNK_IMAGE:-splunk/splunk:9.4}"
SC4S_IMAGE="${SC4S_IMAGE:-ghcr.io/splunk/splunk-connect-for-syslog/container3:latest}"
SC4S_HOST_PORT="${SC4S_SURICATA_EVE_JSON_PORT:-20082}"
SPLUNK_WEB_PORT="${SPLUNK_WEB_PORT:-18000}"
SPLUNK_MGMT_PORT="${SPLUNK_MGMT_PORT:-18089}"
SPLUNK_HEC_PORT="${SPLUNK_HEC_PORT:-18088}"
COMPOSE_FILE="${WORK_DIR}/compose.yaml"
READBACK_SPL='search index=netids "SC4S_SURICATA_EVE_TEST_" earliest=-2h | stats count by sourcetype source host suricata_eve_family event_type | sort suricata_eve_family event_type'
DETAIL_SPL='search index=netids "SC4S_SURICATA_EVE_TEST_" earliest=-2h | table _time index sourcetype source host vendor product suricata_eve_family event_type src_ip src src_port dest_ip dest dest_port transport app action signature signature_id severity dns_query dns_query_type http_method http_status url tls_sni tls_version bytes_in bytes_out file_name file_state file_size anomaly_type anomaly_event ssh_client_software ssh_server_software ssh_client_hassh ssh_server_hassh dhcp_type dhcp_client_mac dhcp_assigned_ip dhcp_requested_ip dhcp_hostname dhcp_lease_time rdp_tx_id rdp_type rdp_protocol rdp_cookie rdp_client_name ftp_command ftp_command_data ftp_completion_code ftp_reply krb5_msg_type krb5_client krb5_service krb5_realm krb5_encryption krb5_error_code smb_command smb_status smb_status_code smb_filename smb_share smb_share_type mqtt_topic mqtt_message_id mqtt_qos mqtt_retain mqtt_client_id http2_authority http2_method http2_path http2_status http2_user_agent pgsql_tx_id pgsql_query pgsql_command_completed pgsql_data_rows pgsql_data_size netflow_pkts netflow_bytes netflow_age netflow_min_ttl netflow_max_ttl arp_hw_type arp_proto_type arp_opcode arp_src_mac arp_dest_mac ike_init_spi ike_resp_spi ike_version_major ike_exchange_type ike_exchange_type_verbose ike_alg_enc ike_alg_hash ike_alg_auth ike_alg_dh modbus_id modbus_transaction_id modbus_unit_id modbus_request_function modbus_response_function modbus_access_type modbus_category modbus_error_flags quic_version quic_sni quic_ja3_hash quic_ja3s_hash quic_ja4 quic_cyu_hash pop3_command pop3_args pop3_success pop3_status pop3_header marker _raw'

usage() {
  cat <<'USAGE'
Usage: packs/suricata_eve_json/scripts/e2e_docker_compose.sh <plan|write-compose|up|replay|readback|run|down>

Idempotent disposable Suricata EVE JSON relay pipeline harness.

Stages:
  plan          Print the one-shot docker compose command and required evidence stages; no Docker required.
  write-compose Write .tmp/e2e/suricata_eve_json/compose.yaml only; no Docker required.
  up            Recreate the disposable Splunk + SC4S stack and pre-create the netids index.
  replay        Send every Suricata EVE JSON fixture through the pack TCP listener.
  readback      Query Splunk for indexed fixture markers and expected Suricata EVE family coverage.
  run           up + replay + readback.
  down          Remove the disposable stack and volumes.

Environment overrides:
  SPLUNK_IMAGE, SC4S_IMAGE, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN,
  SC4S_SURICATA_EVE_JSON_PORT, SPLUNK_WEB_PORT, SPLUNK_MGMT_PORT,
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
      - ${PACK_DIR}/splunk:/opt/splunk/etc/apps/sechub_suricata_eve_json:ro
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
      SC4S_LISTEN_SURICATA_EVE_JSON_TCP_PORT: "20082"
      SOURCE_ALL_SET: SURICATA_EVE_JSON
      SOURCE_ALL_SET_APPEND: SURICATA_EVE_JSON
      SC4S_ARCHIVE_GLOBAL: "no"
      SC4S_DEBUG_CONTAINER: "yes"
    ports:
      - "${SC4S_HOST_PORT}:20082/tcp"
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
  packs/suricata_eve_json/scripts/e2e_docker_compose.sh run

Equivalent explicit stack commands:
  packs/suricata_eve_json/scripts/e2e_docker_compose.sh write-compose
  docker compose -f .tmp/e2e/suricata_eve_json/compose.yaml -p ${PROJECT} up -d --wait --force-recreate --renew-anon-volumes
  docker compose -f .tmp/e2e/suricata_eve_json/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk add index netids -auth admin:\$SPLUNK_PASSWORD || true
  packs/suricata_eve_json/scripts/send_tcp_20082.sh 127.0.0.1 ${SC4S_HOST_PORT}
  docker compose -f .tmp/e2e/suricata_eve_json/compose.yaml -p ${PROJECT} exec -T splunk /opt/splunk/bin/splunk search '${READBACK_SPL}' -auth admin:\$SPLUNK_PASSWORD

Required evidence stages:
  1. Splunk TEST healthy with HEC enabled and index=netids present.
  2. SC4S TEST healthy and listening on tcp/${SC4S_HOST_PORT} for source_id SURICATA_EVE_JSON.
  3. Replay sends 22 fixture events from test-events/suricata_eve_json_test_events.txt.
  4. SC4S/syslog-ng stats/logs show listener/parser/destination movement.
  5. Splunk readback returns 22 events across Suricata alert, dns, http, tls, flow, fileinfo, anomaly, ssh, dhcp, rdp, ftp, krb5, smb, mqtt, http2, pgsql, netflow, arp, ike, modbus, quic, and pop3 fixture families.
  6. Detail SPL verifies count, index, sourcetype, source, host, timestamp and required Suricata family fields.

Fixture families covered:
  - alert -> suricata:eve
  - dns -> suricata:eve
  - http -> suricata:eve
  - tls -> suricata:eve
  - flow -> suricata:eve
  - fileinfo -> suricata:eve
  - anomaly -> suricata:eve
  - ssh -> suricata:eve
  - dhcp -> suricata:eve
  - rdp -> suricata:eve
  - ftp -> suricata:eve
  - krb5 -> suricata:eve
  - smb -> suricata:eve
  - mqtt -> suricata:eve
  - http2 -> suricata:eve
  - pgsql -> suricata:eve
  - netflow -> suricata:eve
  - arp -> suricata:eve
  - ike -> suricata:eve
  - modbus -> suricata:eve
  - quic -> suricata:eve
  - pop3 -> suricata:eve

Explicit gaps:
  - live Suricata sensor/source-version emission, ruleset behavior, and local eve-log configuration are not proven by this harness.
  - collector wrappers, file-tail buffering, syslog envelope rewrites, archive decompression, and Cribl/Fluent Bit/Vector delivery semantics remain unverified.
  - Suricata TSV logs, non-EVE outputs, stats-volume routing, local policy extensions, and real PCAP-derived traffic/source coverage remain deferred until exact source-shape evidence is added.
PLAN
}

up() {
  require_docker
  write_compose
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  compose up -d --wait --force-recreate --renew-anon-volumes
  compose exec -T splunk /opt/splunk/bin/splunk add index netids -auth "admin:${SPLUNK_PASSWORD}" >/tmp/${PACK_ID}_add_index.log 2>&1 || true
  echo "Splunk TEST: http://127.0.0.1:${SPLUNK_WEB_PORT}"
  echo "SC4S Suricata EVE JSON listener: 127.0.0.1:${SC4S_HOST_PORT}"
}

replay() {
  "${PACK_DIR}/scripts/send_tcp_20082.sh" 127.0.0.1 "${SC4S_HOST_PORT}"
}

readback() {
  require_docker
  echo "== SC4S stats sample =="
  compose exec -T sc4s sh -lc 'syslog-ng-ctl stats 2>/dev/null | grep -Ei "suricata|eve|json|splunk|hec|destination|source" | head -80 || true'
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
