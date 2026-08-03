#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-20068}"
EVENT_FILE="${3:-$(dirname "$0")/../test-events/aws_cloud_audit_security_test_events.txt}"
HOSTNAME="${SC4S_TEST_HOSTNAME:-aws-cloud-audit-security-test}"
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  printf '<134>1 %s %s AWS_CLOUD_AUDIT_SECURITY - - - %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$HOSTNAME" "$line"
done < "$EVENT_FILE" | nc "$HOST" "$PORT"
