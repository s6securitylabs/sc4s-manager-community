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
import { DeleteConfirmation } from '../components/DeleteConfirmation';
import { MutationOutcome, type MutationOutcomeData } from '../components/MutationOutcome';
import { operatorSafeErrorMessage } from '../lib/displayError';
import {
  deleteSource,
  getSourceCatalog,
  listSources,
  listRoutes,
  onboardSource,
  type SourceEntry,
} from '../api/operations';
import { clearPendingChange, recordPendingChange } from '../lib/pendingChanges';

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
  const [deleteCandidate, setDeleteCandidate] = useState<SourceEntry | null>(null);

  const sourcesQuery = useQuery({ queryKey: ['sources'], queryFn: ({ signal }) => listSources(signal) });
  const catalogQuery = useQuery({ queryKey: ['source-catalog'], queryFn: ({ signal }) => getSourceCatalog(signal) });
  const routesQuery = useQuery({ queryKey: ['routes'], queryFn: ({ signal }) => listRoutes(signal) });

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
      const mode = result.apply_mode === 'restart_required' ? 'restart_required' : 'reloadable';
      const pendingId = `source:${key}:${title}`;
      if (result.validation?.ok !== false && (!result.control || result.control.skipped || !result.control.ok)) recordPendingChange({ id: pendingId, summary: title, applyMode: mode });
      else if (result.ok && result.control?.ok) clearPendingChange(pendingId);
      if (key.startsWith('delete:')) setDeleteCandidate(null);
      await Promise.all([queryClient.invalidateQueries({ queryKey: ['sources'] }), queryClient.invalidateQueries({ queryKey: ['routes'] })]);
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

      <Alert color="cyan" title="Source changes are reloadable" variant="light">
        Saving stages source config. Choose Validate and reload SC4S now, or open Pending changes later. Reload success is not ingestion proof; send a marker and complete Splunk readback.
      </Alert>

      {actionError && <Alert color="red" title="Action failed">{actionError}</Alert>}
      {outcome && <MutationOutcome title={outcomeTitle} outcome={outcome} />}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <div>
            <Text className="panel-overline">Stage source onboarding</Text>
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
              required
              disabled={catalogQuery.isLoading || catalogQuery.isError}
            />
            <TextInput label="Splunk index (optional)" placeholder="netfw" value={index} onChange={(e) => setIndex(e.currentTarget.value)} />
            <TextInput label="Compliance tag (optional)" placeholder="pci" value={compliance} onChange={(e) => setCompliance(e.currentTarget.value)} />
          </Group>
          {catalogQuery.isLoading ? <Text size="sm" c="dimmed">Loading source type catalogue…</Text> : null}
          {catalogQuery.isError ? <Alert color="red" title="Unable to load source type catalogue">{operatorSafeErrorMessage(catalogQuery.error)} Source onboarding is blocked because an explicit parser/source type is required.</Alert> : null}
          <Checkbox
            label="Validate and reload SC4S now (leave unchecked to save staged config)"
            checked={applyNow}
            onChange={(e) => setApplyNow(e.currentTarget.checked)}
          />
          <Group>
            <Button loading={busyKey === 'onboard'} disabled={catalogQuery.isLoading || catalogQuery.isError || !name.trim() || !sourceMatch.trim() || !vendorProduct} onClick={submitSource}>
              {applyNow ? 'Save, validate and reload SC4S' : 'Save staged source'}
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
          {routesQuery.isError ? <Alert color="red" title="Source deletion blocked">Dependent routes could not be loaded. Retry before deleting a source.</Alert> : null}
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
                      disabled={routesQuery.isError}
                      onClick={() => setDeleteCandidate(info.row.original)}
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
          {deleteCandidate ? <DeleteConfirmation objectLabel={`source ${deleteCandidate.name}`} dependents={(routesQuery.data?.routes || []).filter((route) => route.source === deleteCandidate.name).map((route) => route.id)} busy={busyKey === `delete:${deleteCandidate.name}`} onCancel={() => setDeleteCandidate(null)} onConfirm={() => removeSource(deleteCandidate)} /> : null}
        </Stack>
      </Card>
    </Stack>
  );
}
