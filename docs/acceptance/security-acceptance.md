# Security Acceptance

## Scope

This template records evidence for Gate 3 security acceptance. Do not include
real HEC tokens, API tokens, proxy shared secrets, private keys, or full
credential-bearing environment files.

## Environment

- Date:
- Tester:
- Host:
- sc4s-manager version:
- SC4S image:
- Public route:
- Auth provider:

## Automated Dry Run

Command:

```bash
security/acceptance.sh --report /tmp/sc4s-manager-security-acceptance.md
```

Result:

- Overall:
- Report path:

## Required Checks

| Check | Expected Result | Evidence |
| --- | --- | --- |
| Manager has no Docker socket access | Manager cannot read or mount `/var/run/docker.sock` | |
| Unsupported control action rejected | Control daemon rejects anything outside the fixed action allowlist | |
| Config path traversal rejected | `../` and sibling-prefix probes return 400 | |
| Template import traversal rejected | Unsafe ZIP paths and outside template paths fail | |
| Backup diff/restore traversal rejected | Backup names cannot escape backup directory | |
| Secret redaction in schema/env/diff/backup/audit/logs/destination APIs | Secret values are replaced with `[REDACTED]` | |
| Auth enforced on mutating APIs | Requests without trusted proxy header or API token fail | |
| CSRF/origin enforcement | Mismatched origin is rejected | |
| TLS cert/key mismatch rejected | Mismatched bundle is rejected before restart | |
| No real secrets in reports | Evidence contains placeholders only | |

## Live Probe Notes

Record only HTTP status, endpoint name, sanitized response shape, and timestamps.
Do not paste raw responses if they include environment dumps or logs.

## Decision

- Accepted:
- Exceptions:
- Follow-up issues:
