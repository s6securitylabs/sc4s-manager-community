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
  ScrollArea,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { MutationOutcome, type MutationOutcomeData } from '../components/MutationOutcome';
import { operatorSafeErrorMessage } from '../lib/displayError';
import {
  configureDestination,
  deleteDestination,
  listDestinations,
  type DestinationEntry,
} from '../api/operations';

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

  const destinationsQuery = useQuery({ queryKey: ['destinations'], queryFn: ({ signal }) => listDestinations(signal) });

  async function runAction(key: string, title: string, action: () => Promise<MutationOutcomeData>) {
    setBusyKey(key);
    setActionError(null);
    setOutcome(null);
    try {
      const result = await action();
      setOutcome(result);
      setOutcomeTitle(title);
      setToken('');
      await queryClient.invalidateQueries({ queryKey: ['destinations'] });
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
        <Text c="dimmed">Save Splunk HEC and syslog/BSD forwarding targets. Secrets stay in the environment file and are redacted on readback.</Text>
      </div>

      <Alert color="cyan" title="Restart boundary" variant="light">
        Destination changes are restart-scoped. Saving writes staged environment-file changes; they take effect only after validation and SC4S restart.
      </Alert>

      {actionError && <Alert color="red" title="Action failed">{actionError}</Alert>}
      {outcome && <MutationOutcome title={outcomeTitle} outcome={outcome} />}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <div>
            <Text className="panel-overline">Stage destination change</Text>
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
            <TextInput label="Destination ID / SC4S target name" placeholder="SIEM" value={destId} onChange={(e) => setDestId(e.currentTarget.value)} required />
            <Select
              label="Routing mode"
              data={[
                { value: 'GLOBAL', label: 'GLOBAL' },
                { value: 'SELECT', label: 'SELECT' },
              ]}
              value={mode}
              onChange={setMode}
              description="GLOBAL receives all routed events by default; SELECT receives only explicit selector-routed events."
            />
          </Group>
          {kind === 'hec' ? (
            <Group grow>
              <TextInput label="HEC URL" placeholder="https://splunk.example:8088" value={url} onChange={(e) => setUrl(e.currentTarget.value)} required />
              <PasswordInput label="HEC token (write-only, never echoed)" value={token} onChange={(e) => setToken(e.currentTarget.value)} autoComplete="off" />
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
              label="Selector vendor_product — only matching events route to this destination"
              placeholder="cisco_asa"
              value={selectorVendorProduct}
              onChange={(e) => setSelectorVendorProduct(e.currentTarget.value)}
            />
          ) : null}
          <Checkbox
            label="Validate and restart SC4S now. Leave unchecked to keep this destination staged in the environment file."
            checked={applyNow}
            onChange={(e) => setApplyNow(e.currentTarget.checked)}
          />
          <Group>
            <Button
              loading={busyKey === 'configure'}
              disabled={!destId.trim() || (kind === 'hec' ? !url.trim() : !host.trim())}
              onClick={submitDestination}
            >
              {applyNow ? 'Save, validate, and restart' : 'Save staged destination'}
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Text className="panel-overline">Saved destination entries</Text>
              <Title order={3}>Saved destination staging inventory</Title>
            </div>
            <Badge variant="light" color="cyan">{destinationsQuery.data?.destinations.length ?? 0} saved</Badge>
          </Group>
          {destinationsQuery.isLoading ? <Loader size="sm" /> : null}
          {destinationsQuery.isError ? <Alert color="red" title="Failed to load destinations">{operatorSafeErrorMessage(destinationsQuery.error)}</Alert> : null}
          {destinationsQuery.data?.destinations.length ? (
            <ScrollArea type="auto" offsetScrollbars>
            <Table striped highlightOnHover miw={840}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Destination type</Table.Th>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Target</Table.Th>
                  <Table.Th>Mode</Table.Th>
                  <Table.Th>Token status</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {destinationsQuery.data.destinations.map((entry) => (
                  <Table.Tr key={`${entry.kind}:${entry.id}`}>
                    <Table.Td><Badge variant="light" color={entry.kind === 'hec' ? 'cyan' : 'violet'}>{entry.kind}</Badge></Table.Td>
                    <Table.Td><Code className="breakable-code-text" title={entry.id}>{entry.id}</Code></Table.Td>
                    <Table.Td>
                      <Text
                        size="sm"
                        className="breakable-table-text"
                        title={entry.url || (entry.host ? `${entry.host}:${entry.port || ''} ${entry.transport || ''}` : '—')}
                      >
                        {entry.url || (entry.host ? `${entry.host}:${entry.port || ''} ${entry.transport || ''}` : '—')}
                      </Text>
                    </Table.Td>
                    <Table.Td><Badge variant="light" color={entry.mode === 'SELECT' ? 'yellow' : 'gray'}>{entry.mode || 'GLOBAL'}</Badge></Table.Td>
                    <Table.Td><DestinationTokenStatus token={entry.token} /></Table.Td>
                    <Table.Td>
                      {entry.id !== 'DEFAULT' ? (
                        <Button
                          color="red"
                          variant="light"
                          size="xs"
                          loading={busyKey === `delete:${entry.kind}:${entry.id}`}
                          onClick={() => removeDestination(entry)}
                        >
                          Delete
                        </Button>
                      ) : (
                        <Badge variant="light" color="gray">default target</Badge>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            </ScrollArea>
          ) : !destinationsQuery.isLoading && !destinationsQuery.isError ? (
            <Paper withBorder p="md" radius="md">
              <Text c="dimmed">No destination entries saved yet. Add one above; it remains staged until validation and SC4S restart.</Text>
            </Paper>
          ) : null}
        </Stack>
      </Card>
    </Stack>
  );
}
