import { Alert, Badge, Button, Card, Code, Group, List, Loader, Stack, Text, Title } from '@mantine/core';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { listAudit, listBackups, runControlAction, validateConfiguration } from '../api/operations';
import { MutationOutcome, type MutationOutcomeData } from '../components/MutationOutcome';
import { operatorSafeErrorMessage } from '../lib/displayError';
import { clearPendingChanges, listPendingChanges, PENDING_CHANGED_EVENT, type PendingChange } from '../lib/pendingChanges';

export function Operations() {
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<PendingChange[]>(listPendingChanges);
  const [validation, setValidation] = useState<MutationOutcomeData | null>(null);
  const [actionResult, setActionResult] = useState<MutationOutcomeData | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const backupsQuery = useQuery({ queryKey: ['operations', 'backups'], queryFn: ({ signal }) => listBackups(signal) });
  const auditQuery = useQuery({ queryKey: ['operations', 'audit'], queryFn: ({ signal }) => listAudit(signal) });

  useEffect(() => {
    const update = () => {
      setPending(listPendingChanges());
      setValidation(null);
      setActionResult(null);
    };
    window.addEventListener(PENDING_CHANGED_EVENT, update);
    return () => window.removeEventListener(PENDING_CHANGED_EVENT, update);
  }, []);

  const validate = async () => {
    setBusy('validate'); setError(null); setActionResult(null);
    try {
      const result = await validateConfiguration();
      setValidation({ ok: result.ok === true, validation: result });
    } catch (reason) {
      setError(operatorSafeErrorMessage(reason, 'Validation could not run. Control may be unavailable.'));
    } finally { setBusy(null); }
  };

  const apply = async (mode: PendingChange['applyMode']) => {
    const action = mode === 'reloadable' ? 'reload' : 'restart';
    const expectedRevision = validation?.validation?.revision;
    const validationToken = validation?.validation?.validation_token;
    if (!Number.isInteger(expectedRevision) || !validationToken) {
      setValidation(null);
      setError('Validation evidence has no server revision. Validate the current configuration again before applying.');
      return;
    }
    setBusy(action); setError(null);
    try {
      const result = await runControlAction(action, expectedRevision as number, validationToken);
      const ok = result.ok === true;
      setActionResult({ ok, apply_mode: mode, validation: result.validation, control: result.control, post_check: result.post_check });
      if (['revision_conflict', 'validation_revision_required', 'validation_token_required', 'validation_state_changed'].includes(result.code || '')) setValidation(null);
      if (ok) clearPendingChanges(mode);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['runtime'] }),
        queryClient.invalidateQueries({ queryKey: ['operations'] }),
      ]);
    } catch (reason) {
      setError(operatorSafeErrorMessage(reason, `SC4S ${action} failed. Staged files may still be present; review backup and rollback evidence.`));
    } finally { setBusy(null); }
  };

  const reloadCount = pending.filter((item) => item.applyMode === 'reloadable').length;
  const restartCount = pending.filter((item) => item.applyMode === 'restart_required').length;
  const validationPassed = validation?.validation?.ok === true && Number.isInteger(validation.validation.revision) && Boolean(validation.validation.validation_token);

  return (
    <Stack gap="lg">
      <div>
        <Title order={1}>Pending changes and operations</Title>
        <Text c="dimmed">Close the staged → validate → reload/restart → runtime post-check → Splunk readback workflow using the Manager control API.</Text>
      </div>
      <Alert color="yellow" title={`${pending.length} pending change${pending.length === 1 ? '' : 's'}`} role="status" aria-live="polite">
        This browser records changes staged through these forms for workflow guidance. Apply is permitted only against the exact server revision returned by validation; the list itself is not proof of what is live.
      </Alert>
      <Card withBorder>
        <Stack gap="sm">
          <Group justify="space-between"><Title order={3}>1. Review pending changes</Title><Badge color={pending.length ? 'yellow' : 'gray'}>{pending.length}</Badge></Group>
          {pending.length ? <List>{pending.map((item) => <List.Item key={item.id}>{item.summary} — <Code>{item.applyMode}</Code>, staged {item.stagedAt}</List.Item>)}</List> : <Text c="dimmed">No browser-recorded pending changes. Server revision protection still applies to validation and control actions.</Text>}
        </Stack>
      </Card>
      <Card withBorder>
        <Stack gap="sm">
          <Title order={3}>2. Validate staged configuration</Title>
          <Text size="sm">Validation checks syntax and TLS readiness through the narrow control daemon. It does not prove SC4S accepted events or that Splunk indexed them.</Text>
          <Group><Button loading={busy === 'validate'} onClick={validate}>Validate staged configuration</Button></Group>
          {validation ? <MutationOutcome title="Validation result" outcome={validation} /> : null}
        </Stack>
      </Card>
      <Card withBorder>
        <Stack gap="sm">
          <Title order={3}>3. Apply the correct control action</Title>
          <Text size="sm">Source and route selector changes are reloadable. Destination/environment changes require a restart and may be disruptive.</Text>
          <Group>
            <Button loading={busy === 'reload'} disabled={!validationPassed || reloadCount === 0} onClick={() => apply('reloadable')}>Reload SC4S ({reloadCount})</Button>
            <Button color="orange" loading={busy === 'restart'} disabled={!validationPassed || restartCount === 0} onClick={() => apply('restart_required')}>Restart SC4S ({restartCount})</Button>
          </Group>
          {!validationPassed ? <Text size="sm" c="dimmed">Apply controls stay disabled until validation passes and returns the current server revision.</Text> : null}
          {actionResult ? <MutationOutcome title="Validated control and runtime post-check evidence" outcome={actionResult} /> : null}
        </Stack>
      </Card>
      {error ? <Alert color="red" title="Operation failed" role="alert">{error}</Alert> : null}
      <Card withBorder>
        <Stack gap="sm">
          <Title order={3}>4. Backup and rollback handles</Title>
          {backupsQuery.isLoading ? <Loader size="sm" /> : backupsQuery.isError ? <Alert color="red">{operatorSafeErrorMessage(backupsQuery.error)}</Alert> : backupsQuery.data?.backups.length ? (
            <List>{backupsQuery.data.backups.slice(0, 10).map((backup) => <List.Item key={backup.name}><Code>{backup.name}</Code> — {backup.mtime}</List.Item>)}</List>
          ) : <Text c="dimmed">No backup handles returned.</Text>}
          <Text size="sm" c="dimmed">Restore is intentionally not automatic from this view: backend transactions do not yet guarantee rollback after every failed control/post-check outcome.</Text>
        </Stack>
      </Card>
      <Card withBorder>
        <Stack gap="sm">
          <Title order={3}>5. Recent audit evidence</Title>
          {auditQuery.isLoading ? <Loader size="sm" /> : auditQuery.isError ? <Alert color="red">{operatorSafeErrorMessage(auditQuery.error)}</Alert> : auditQuery.data?.lines.length ? (
            <Code block className="muted-code">{auditQuery.data.lines.slice(-20).join('\n')}</Code>
          ) : <Text c="dimmed">No audit records returned.</Text>}
        </Stack>
      </Card>
      <Alert color="blue" title="Final live proof">
        After apply, verify Dashboard listener/counter recovery, send a unique marker event, and capture the matching Splunk readback with timestamp/index/sourcetype. Validation or a green control response alone is not Splunk proof.
      </Alert>
    </Stack>
  );
}
