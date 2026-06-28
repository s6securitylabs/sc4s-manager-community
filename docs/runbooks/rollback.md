# Rollback Runbook

## Scope

Rollback restores the last known-good sc4s-manager application release and service
configuration. It must not discard SC4S local configuration changes unless the
incident commander explicitly approves restoring those files from backup.

## Preconditions

- A named backup from the corresponding install or upgrade.
- Recorded previous application version and systemd unit checksums.
- Access to service logs and health endpoints.

## Rollback Steps

1. Declare rollback and freeze non-emergency changes.
2. Capture current service status, logs, health output, and config validation
   result for incident evidence.
3. Stop the manager service.
4. Restore the previous application release under `/opt/sc4s-manager`.
5. Restore previous systemd unit files if they changed in the failed upgrade.
6. Reload systemd and restart `sc4s-manager-control.socket`,
   `sc4s-manager-control.service`, and `sc4s-manager.service`.
7. Run `/health`, `/api/health`, config validation, version drift, and redaction
   smoke tests.
8. Confirm SC4S remains healthy and ingestion counters continue moving.
9. Record the rollback decision, commands, timestamps, and sanitized evidence.

## Validation

Rollback is complete only when the manager is healthy, the control socket
responds, SC4S status is healthy, and no secrets appear in reports or logs.
