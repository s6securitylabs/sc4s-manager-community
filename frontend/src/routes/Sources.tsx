import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Code,
  Group,
  Loader,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { MutationOutcome, type MutationOutcomeData } from '../components/MutationOutcome';
import { operatorSafeErrorMessage } from '../lib/displayError';
import {
  deleteSource,
  getSourceCatalog,
  listSources,
  onboardSource,
  type SourceEntry,
} from '../api/operations';

export function Sources() {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [sourceMatch, setSourceMatch] = useState('');
  const [vendorProduct, setVendorProduct] = useState<string | null>(null);
  const [index, setIndex] = useState('');
  const [compliance, setCompliance] = useState('');
  const [applyNow, setApplyNow] = useState(false);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<MutationOutcomeData | null>(null);
  const [outcomeTitle, setOutcomeTitle] = useState('');

  const sourcesQuery = useQuery({ queryKey: ['sources'], queryFn: ({ signal }) => listSources(signal) });
  const catalogQuery = useQuery({ queryKey: ['source-catalog'], queryFn: ({ signal }) => getSourceCatalog(signal) });

  const catalogOptions = useMemo(
    () => (catalogQuery.data?.sources || []).map((item) => ({
      value: item.vendor_product,
      label: item.label ? `${item.label} (${item.vendor_product})` : item.vendor_product,
    })),
    [catalogQuery.data],
  );

  async function runAction(key: string, title: string, action: () => Promise<MutationOutcomeData>) {
    setBusyKey(key);
    setActionError(null);
    setOutcome(null);
    try {
      const result = await action();
      setOutcome(result);
      setOutcomeTitle(title);
      await queryClient.invalidateQueries({ queryKey: ['sources'] });
    } catch (error) {
      setActionError(operatorSafeErrorMessage(error, 'Manager could not complete that action. Check the entered values and retry.'));
    } finally {
      setBusyKey(null);
    }
  }

  const submitSource = () =>
    runAction('onboard', `Source ${name}`, () =>
      onboardSource({
        name: name.trim(),
        source: sourceMatch.trim(),
        vendor_product: vendorProduct || '',
        index: index.trim(),
        compliance: compliance.trim(),
        apply: applyNow,
      }),
    );

  const removeSource = (entry: SourceEntry) =>
    runAction(`delete:${entry.name}`, `Delete source ${entry.name}`, () => deleteSource(entry.name));

  return (
    <Stack gap="lg">
      <div>
        <Title order={1}>Sources</Title>
        <Text c="dimmed">Save staged source filters by network match, map them to SC4S vendor_product, index, and compliance tags, then optionally validate and reload SC4S.</Text>
      </div>

      <Alert color="cyan" title="When this becomes live" variant="light">
        Onboarding writes staged filter and context CSV changes under <Code>local/config/filters/</Code>. SC4S uses the change only after validation and reload; prove it is live with Splunk readback.
      </Alert>

      {actionError && <Alert color="red" title="Action failed">{actionError}</Alert>}
      {outcome && <MutationOutcome title={outcomeTitle} outcome={outcome} />}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <div>
            <Text className="panel-overline">Stage source onboarding</Text>
            <Title order={3}>Add a staged syslog source</Title>
          </div>
          <Group grow>
            <TextInput label="Source ID" placeholder="asa_lab" value={name} onChange={(e) => setName(e.currentTarget.value)} required />
            <TextInput label="Source match: IP, CIDR, or hostname" placeholder="10.10.2.0/24" value={sourceMatch} onChange={(e) => setSourceMatch(e.currentTarget.value)} required />
          </Group>
          <Group grow>
            <Select
              label="SC4S vendor_product"
              placeholder="cisco_asa"
              data={catalogOptions}
              value={vendorProduct}
              onChange={setVendorProduct}
              searchable
              clearable
            />
            <TextInput label="Splunk index (optional)" placeholder="netfw" value={index} onChange={(e) => setIndex(e.currentTarget.value)} />
            <TextInput label="Compliance tag (optional)" placeholder="pci" value={compliance} onChange={(e) => setCompliance(e.currentTarget.value)} />
          </Group>
          <Checkbox
            label="Validate and reload SC4S now. Leave unchecked to keep this source staged."
            checked={applyNow}
            onChange={(e) => setApplyNow(e.currentTarget.checked)}
          />
          <Group>
            <Button loading={busyKey === 'onboard'} disabled={!name.trim() || !sourceMatch.trim()} onClick={submitSource}>
              {applyNow ? 'Stage, validate, and reload' : 'Save staged source'}
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Text className="panel-overline">Saved source entries</Text>
              <Title order={3}>Saved source staging inventory</Title>
            </div>
            <Badge variant="light" color="cyan">{sourcesQuery.data?.sources.length ?? 0} saved</Badge>
          </Group>
          {sourcesQuery.isLoading ? <Loader size="sm" /> : null}
          {sourcesQuery.isError ? <Alert color="red" title="Failed to load sources">{operatorSafeErrorMessage(sourcesQuery.error)}</Alert> : null}
          {sourcesQuery.data?.sources.length ? (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Name</Table.Th>
                  <Table.Th>Match</Table.Th>
                  <Table.Th>SC4S vendor_product</Table.Th>
                  <Table.Th>Index</Table.Th>
                  <Table.Th>Compliance</Table.Th>
                  <Table.Th>Apply/reload mode</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {sourcesQuery.data.sources.map((entry) => (
                  <Table.Tr key={entry.filter}>
                    <Table.Td><Code>{entry.name}</Code></Table.Td>
                    <Table.Td>{entry.source || '—'}</Table.Td>
                    <Table.Td>{entry.vendor_product || '—'}</Table.Td>
                    <Table.Td>{entry.index || '—'}</Table.Td>
                    <Table.Td>{entry.compliance || '—'}</Table.Td>
                    <Table.Td><Badge color="gray" variant="light">{entry.apply_mode}</Badge></Table.Td>
                    <Table.Td>
                      <Button
                        color="red"
                        variant="light"
                        size="xs"
                        loading={busyKey === `delete:${entry.name}`}
                        onClick={() => removeSource(entry)}
                      >
                        Delete
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : !sourcesQuery.isLoading && !sourcesQuery.isError ? (
            <Paper withBorder p="md" radius="md">
              <Text c="dimmed">No source entries saved yet. Add one above; it remains staged until validation, reload, and live Splunk readback.</Text>
            </Paper>
          ) : null}
        </Stack>
      </Card>
    </Stack>
  );
}
