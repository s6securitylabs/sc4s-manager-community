import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Code,
  Group,
  Loader,
  NumberInput,
  Paper,
  PasswordInput,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { createColumnHelper } from '@tanstack/react-table';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { DataTable } from '../components/DataTable';
import { DeleteConfirmation } from '../components/DeleteConfirmation';
import { MutationOutcome, type MutationOutcomeData } from '../components/MutationOutcome';
import { operatorSafeErrorMessage } from '../lib/displayError';
import {
  configureDestination,
  deleteDestination,
  isConfiguredDestination,
  listDestinations,
  listRoutes,
  type DestinationEntry,
} from '../api/operations';
import { clearPendingChange, recordPendingChange } from '../lib/pendingChanges';

const colHelper = createColumnHelper<DestinationEntry>();

type DestinationKind = 'hec' | 'syslog' | 'bsd';

function DestinationTokenStatus({ token }: { token?: string | null }) {
  if (!token) return <>—</>;
  if (token === '[REDACTED]') return <Badge color="gray" variant="light">Token present (redacted)</Badge>;
  return <Badge color="red" variant="light">Token hidden — check server redaction</Badge>;
}

export function Destinations() {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<DestinationKind>('hec');
  const [destId, setDestId] = useState('');
  const [url, setUrl] = useState('');
  const [token, setToken] = useState('');
  const [tlsVerify, setTlsVerify] = useState<string | null>(null);
  const [host, setHost] = useState('');
  const [port, setPort] = useState<number | string>('');
  const [transport, setTransport] = useState<string | null>('tcp');
  const [mode, setMode] = useState<string | null>('GLOBAL');
  const [selectorVendorProduct, setSelectorVendorProduct] = useState('');
  const [applyNow, setApplyNow] = useState(false);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<MutationOutcomeData | null>(null);
  const [outcomeTitle, setOutcomeTitle] = useState('');
  const [deleteCandidate, setDeleteCandidate] = useState<DestinationEntry | null>(null);

  const destinationsQuery = useQuery({ queryKey: ['destinations'], queryFn: ({ signal }) => listDestinations(signal) });
  const routesQuery = useQuery({ queryKey: ['routes'], queryFn: ({ signal }) => listRoutes(signal) });
  const configuredDestinations = (destinationsQuery.data?.destinations || []).filter(isConfiguredDestination);

  async function runAction(key: string, title: string, action: () => Promise<MutationOutcomeData>) {
    setBusyKey(key);
    setActionError(null);
    setOutcome(null);
    try {
      const result = await action();
      setOutcome(result);
      setOutcomeTitle(title);
      setToken('');
      const pendingId = `destination:${key}:${title}`;
      if (result.validation?.ok !== false && (!result.control || result.control.skipped || !result.control.ok)) recordPendingChange({ id: pendingId, summary: title, applyMode: 'restart_required' });
      else if (result.ok && result.control?.ok) clearPendingChange(pendingId);
      if (key.startsWith('delete:')) setDeleteCandidate(null);
      await Promise.all([queryClient.invalidateQueries({ queryKey: ['destinations'] }), queryClient.invalidateQueries({ queryKey: ['routes'] })]);
    } catch (error) {
      setActionError(operatorSafeErrorMessage(error, 'Manager could not complete that action. Check the entered values and retry.'));
    } finally {
      setBusyKey(null);
    }
  }

  const submitDestination = () => {
    const payload: Record<string, unknown> = { kind, id: destId.trim(), mode: mode || 'GLOBAL', apply: applyNow };
    if (kind === 'hec') {
      payload.url = url.trim();
      if (token) payload.token = token;
      if (tlsVerify) payload.tls_verify = tlsVerify;
    } else {
      payload.host = host.trim();
      payload.port = port || (kind === 'syslog' ? 601 : 514);
      payload.transport = transport || 'tcp';
      if (mode === 'SELECT') payload.selector_vendor_product = selectorVendorProduct.trim();
    }
    return runAction('configure', `Destination ${destId.trim().toUpperCase()}`, () => configureDestination(payload));
  };

  const removeDestination = (entry: DestinationEntry) =>
    runAction(`delete:${entry.kind}:${entry.id}`, `Delete destination ${entry.id}`, () => deleteDestination(entry.kind, entry.id));

  return (
    <Stack gap="lg">
      <div>
        <Title order={1}>Destinations</Title>
        <Text c="dimmed">Configure where SC4S sends events — Splunk HEC for indexing, or syslog to forward to another system. Secret tokens are never echoed after saving.</Text>
      </div>

      <Alert color="cyan" title="Destination changes require restart" variant="light">
        Saving stages destination config. Choose Validate and restart SC4S now, or use Pending changes later. Restart can be disruptive and is not Splunk delivery proof.
      </Alert>

      {actionError && <Alert color="red" title="Action failed">{actionError}</Alert>}
      {outcome && <MutationOutcome title={outcomeTitle} outcome={outcome} />}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <div>
            <Text className="panel-overline">Add a destination</Text>
            <Title order={3}>Add or edit a forwarding target</Title>
          </div>
          <Group grow>
            <Select
              label="Destination type"
              data={[
                { value: 'hec', label: 'Splunk HEC' },
                { value: 'syslog', label: 'Syslog (IETF)' },
                { value: 'bsd', label: 'Syslog (BSD)' },
              ]}
              value={kind}
              onChange={(value) => setKind((value as DestinationKind) || 'hec')}
            />
            <TextInput label="Destination ID" placeholder="SIEM" value={destId} onChange={(e) => setDestId(e.currentTarget.value)} required />
            <Select
              label="Routing mode"
              data={[
                { value: 'GLOBAL', label: 'GLOBAL' },
                { value: 'SELECT', label: 'SELECT' },
              ]}
              value={mode}
              onChange={setMode}
              description="GLOBAL sends all events here by default. SELECT sends only events from specific routes you define."
            />
          </Group>
          {kind === 'hec' ? (
            <Group grow>
              <TextInput label="HEC URL" placeholder="https://splunk.example:8088" value={url} onChange={(e) => setUrl(e.currentTarget.value)} required />
              <PasswordInput label="HEC token (hidden after saving)" value={token} onChange={(e) => setToken(e.currentTarget.value)} autoComplete="off" />
              <Select
                label="Verify TLS certificate"
                data={[
                  { value: 'yes', label: 'yes' },
                  { value: 'no', label: 'no' },
                ]}
                value={tlsVerify}
                onChange={setTlsVerify}
                clearable
                placeholder="default"
              />
            </Group>
          ) : (
            <Group grow>
              <TextInput label="Host" placeholder="10.0.0.5" value={host} onChange={(e) => setHost(e.currentTarget.value)} required />
              <NumberInput label="Port" placeholder={kind === 'syslog' ? '601' : '514'} value={port} onChange={setPort} min={1} max={65535} />
              <Select
                label="Transport"
                data={[
                  { value: 'tcp', label: 'tcp' },
                  { value: 'udp', label: 'udp' },
                  { value: 'tls', label: 'tls' },
                ]}
                value={transport}
                onChange={setTransport}
              />
            </Group>
          )}
          {kind !== 'hec' && mode === 'SELECT' ? (
            <TextInput
              label="Filter by source type — only events from this source type go to this destination"
              placeholder="cisco_asa"
              value={selectorVendorProduct}
              onChange={(e) => setSelectorVendorProduct(e.currentTarget.value)}
            />
          ) : null}
          <Checkbox
            label="Validate and restart SC4S now (leave unchecked to save staged config)"
            checked={applyNow}
            onChange={(e) => setApplyNow(e.currentTarget.checked)}
          />
          <Group>
            <Button
              loading={busyKey === 'configure'}
              disabled={!destId.trim() || (kind === 'hec' ? !url.trim() : !host.trim())}
              onClick={submitDestination}
            >
              {applyNow ? 'Save, validate and restart SC4S' : 'Save staged destination'}
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Title order={3}>Configured destinations</Title>
            </div>
            <Badge variant="light" color="cyan">{configuredDestinations.length} configured</Badge>
          </Group>
          {destinationsQuery.isLoading ? <Loader size="sm" /> : null}
          {destinationsQuery.isError ? <Alert color="red" title="Failed to load destinations">{operatorSafeErrorMessage(destinationsQuery.error)}</Alert> : null}
          {routesQuery.isError ? <Alert color="red" title="Destination deletion blocked">Dependent routes could not be loaded. Retry before deleting a destination.</Alert> : null}
          {destinationsQuery.data?.destinations.length ? (
            <DataTable
              data={destinationsQuery.data.destinations}
              searchPlaceholder="Search by ID, type, target…"
              miw={840}
              columns={[
                colHelper.accessor('kind', {
                  header: 'Type',
                  cell: (info) => (
                    <Badge variant="light" color={info.getValue() === 'hec' ? 'cyan' : 'violet'}>{info.getValue()}</Badge>
                  ),
                }),
                colHelper.accessor('id', {
                  header: 'ID',
                  cell: (info) => <Code className="breakable-code-text">{info.getValue()}</Code>,
                }),
                colHelper.display({
                  id: 'target',
                  header: 'Target',
                  cell: (info) => {
                    const e = info.row.original;
                    const label = e.url || (e.host ? `${e.host}:${e.port || ''} ${e.transport || ''}`.trim() : '—');
                    return <Text size="sm" className="breakable-table-text">{label}</Text>;
                  },
                }),
                colHelper.accessor('mode', {
                  header: 'Mode',
                  cell: (info) => (
                    <Badge variant="light" color={info.getValue() === 'SELECT' ? 'yellow' : 'gray'}>{info.getValue() || 'GLOBAL'}</Badge>
                  ),
                }),
                colHelper.display({
                  id: 'token',
                  header: 'Token',
                  cell: (info) => <DestinationTokenStatus token={info.row.original.token} />,
                }),
                colHelper.display({
                  id: 'actions',
                  header: '',
                  cell: (info) => {
                    const e = info.row.original;
                    return e.id !== 'DEFAULT' ? (
                      <Button
                        color="red"
                        variant="light"
                        size="xs"
                        loading={busyKey === `delete:${e.kind}:${e.id}`}
                        disabled={routesQuery.isError}
                        onClick={() => setDeleteCandidate(e)}
                      >
                        Delete
                      </Button>
                    ) : (
                      <Badge variant="light" color={isConfiguredDestination(e) ? 'green' : 'orange'}>{isConfiguredDestination(e) ? 'configured default' : 'DEFAULT setup required'}</Badge>
                    );
                  },
                }),
              ]}
            />
          ) : !destinationsQuery.isLoading && !destinationsQuery.isError ? (
            <Paper withBorder p="md" radius="md">
              <Text c="dimmed">No destinations configured yet. Add one above.</Text>
            </Paper>
          ) : null}
          {deleteCandidate ? <DeleteConfirmation objectLabel={`destination ${deleteCandidate.id}`} dependents={(routesQuery.data?.routes || []).filter((route) => route.destination_kind === deleteCandidate.kind && route.destination_id === deleteCandidate.id).map((route) => route.id)} busy={busyKey === `delete:${deleteCandidate.kind}:${deleteCandidate.id}`} onCancel={() => setDeleteCandidate(null)} onConfirm={() => removeDestination(deleteCandidate)} /> : null}
        </Stack>
      </Card>
    </Stack>
  );
}
