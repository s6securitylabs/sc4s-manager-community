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
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { createColumnHelper } from '@tanstack/react-table';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { MutationOutcome, type MutationOutcomeData } from '../components/MutationOutcome';
import { operatorSafeErrorMessage } from '../lib/displayError';
import {
  deleteSource,
  getSourceCatalog,
  listSources,
  onboardSource,
  type SourceEntry,
} from '../api/operations';

const colHelper = createColumnHelper<SourceEntry>();

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
        <Text c="dimmed">Map IP addresses or hostnames to SC4S source types. Each source tells SC4S which parser to use and which Splunk index to write to.</Text>
      </div>

      <Alert color="cyan" title="Changes need a restart to take effect" variant="light">
        Saving a source writes config files but does not restart SC4S. Tick the checkbox below to apply and restart immediately, or restart later from SC4S Manager. Search Splunk for incoming events to confirm it's working.
      </Alert>

      {actionError && <Alert color="red" title="Action failed">{actionError}</Alert>}
      {outcome && <MutationOutcome title={outcomeTitle} outcome={outcome} />}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <div>
            <Text className="panel-overline">Add a source</Text>
            <Title order={3}>Add a syslog source</Title>
          </div>
          <Group grow>
            <TextInput label="Source ID" placeholder="asa_lab" value={name} onChange={(e) => setName(e.currentTarget.value)} required />
            <TextInput label="Source match: IP, CIDR, or hostname" placeholder="10.10.2.0/24" value={sourceMatch} onChange={(e) => setSourceMatch(e.currentTarget.value)} required />
          </Group>
          <Group grow>
            <Select
              label="Source type"
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
            label="Apply and restart SC4S now (leave unchecked to save without restarting)"
            checked={applyNow}
            onChange={(e) => setApplyNow(e.currentTarget.checked)}
          />
          <Group>
            <Button loading={busyKey === 'onboard'} disabled={!name.trim() || !sourceMatch.trim()} onClick={submitSource}>
              {applyNow ? 'Save and restart SC4S' : 'Save source'}
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Title order={3}>Configured sources</Title>
            </div>
            <Badge variant="light" color="cyan">{sourcesQuery.data?.sources.length ?? 0} saved</Badge>
          </Group>
          {sourcesQuery.isLoading ? <Loader size="sm" /> : null}
          {sourcesQuery.isError ? <Alert color="red" title="Failed to load sources">{operatorSafeErrorMessage(sourcesQuery.error)}</Alert> : null}
          {sourcesQuery.data?.sources.length ? (
            <DataTable
              data={sourcesQuery.data.sources}
              searchPlaceholder="Search by name, IP, source type…"
              miw={760}
              columns={[
                colHelper.accessor('name', {
                  header: 'Name',
                  cell: (info) => <Code>{info.getValue()}</Code>,
                }),
                colHelper.accessor('source', {
                  header: 'Match',
                  cell: (info) => info.getValue() || '—',
                }),
                colHelper.accessor('vendor_product', {
                  header: 'Source type',
                  cell: (info) => info.getValue() || '—',
                }),
                colHelper.accessor('index', {
                  header: 'Index',
                  cell: (info) => info.getValue() || '—',
                }),
                colHelper.accessor('compliance', {
                  header: 'Compliance',
                  cell: (info) => info.getValue() || '—',
                }),
                colHelper.accessor('apply_mode', {
                  header: 'Apply mode',
                  cell: (info) => <Badge color="gray" variant="light">{info.getValue()}</Badge>,
                }),
                colHelper.display({
                  id: 'actions',
                  header: '',
                  cell: (info) => (
                    <Button
                      color="red"
                      variant="light"
                      size="xs"
                      loading={busyKey === `delete:${info.row.original.name}`}
                      onClick={() => removeSource(info.row.original)}
                    >
                      Delete
                    </Button>
                  ),
                }),
              ]}
            />
          ) : !sourcesQuery.isLoading && !sourcesQuery.isError ? (
            <Paper withBorder p="md" radius="md">
              <Text c="dimmed">No sources configured yet. Add one above.</Text>
            </Paper>
          ) : null}
        </Stack>
      </Card>
    </Stack>
  );
}
