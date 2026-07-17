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
  deleteRoute,
  listDestinations,
  listRoutes,
  listSources,
  upsertRoute,
  isConfiguredDestination,
  type RouteEntry,
} from '../api/operations';
import { clearPendingChange, recordPendingChange } from '../lib/pendingChanges';

const colHelper = createColumnHelper<RouteEntry>();

export function RoutesPage() {
  const queryClient = useQueryClient();
  const [routeId, setRouteId] = useState('');
  const [source, setSource] = useState<string | null>(null);
  const [pack, setPack] = useState('');
  const [destination, setDestination] = useState<string | null>(null);
  const [applyNow, setApplyNow] = useState(false);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<MutationOutcomeData | null>(null);
  const [outcomeTitle, setOutcomeTitle] = useState('');
  const [deleteCandidate, setDeleteCandidate] = useState<RouteEntry | null>(null);

  const routesQuery = useQuery({ queryKey: ['routes'], queryFn: ({ signal }) => listRoutes(signal) });
  const sourcesQuery = useQuery({ queryKey: ['sources'], queryFn: ({ signal }) => listSources(signal) });
  const destinationsQuery = useQuery({ queryKey: ['destinations'], queryFn: ({ signal }) => listDestinations(signal) });
  const prerequisiteQueryError = sourcesQuery.isError || destinationsQuery.isError;

  const sourceOptions = useMemo(
    () => (sourcesQuery.data?.sources || []).map((item) => ({
      value: item.name,
      label: item.vendor_product ? `${item.name} (${item.vendor_product})` : item.name,
    })),
    [sourcesQuery.data],
  );

  const destinationOptions = useMemo(
    () => (destinationsQuery.data?.destinations || [])
      .filter((item) => item.mode === 'SELECT' && isConfiguredDestination(item))
      .map((item) => ({ value: `${item.kind}:${item.id}`, label: `${item.kind.toUpperCase()} ${item.id}` })),
    [destinationsQuery.data],
  );

  async function runAction(key: string, title: string, action: () => Promise<MutationOutcomeData>) {
    setBusyKey(key);
    setActionError(null);
    setOutcome(null);
    try {
      const result = await action();
      setOutcome(result);
      setOutcomeTitle(title);
      const pendingId = `route:${key}:${title}`;
      if (result.validation?.ok !== false && (!result.control || result.control.skipped || !result.control.ok)) recordPendingChange({ id: pendingId, summary: title, applyMode: 'reloadable' });
      else if (result.ok && result.control?.ok) clearPendingChange(pendingId);
      if (key.startsWith('delete:')) setDeleteCandidate(null);
      await queryClient.invalidateQueries({ queryKey: ['routes'] });
    } catch (error) {
      setActionError(operatorSafeErrorMessage(error, 'Manager could not complete that action. Check the entered values and retry.'));
    } finally {
      setBusyKey(null);
    }
  }

  const submitRoute = () => {
    const [destinationKind, destinationId] = (destination || ':').split(':');
    return runAction('upsert', `Route ${routeId.trim()}`, () =>
      upsertRoute({
        id: routeId.trim(),
        source: source || '',
        pack: pack.trim(),
        destination_kind: destinationKind,
        destination_id: destinationId,
        apply: applyNow,
      }),
    );
  };

  const removeRoute = (entry: RouteEntry) =>
    runAction(`delete:${entry.id}`, `Delete route ${entry.id}`, () => deleteRoute(entry.id));

  const sourceVendorProduct = useMemo(() => {
    const selected = (sourcesQuery.data?.sources || []).find((item) => item.name === source);
    return selected?.vendor_product || '';
  }, [source, sourcesQuery.data]);

  return (
    <Stack gap="lg">
      <div>
        <Title order={1}>Routes</Title>
        <Text c="dimmed">Direct events from a specific source to a specific destination, based on source type.</Text>
      </div>

      <Alert color="cyan" title="Route changes are reloadable" variant="light">
        Saving stages a selector. Choose Validate and reload SC4S now, or use Pending changes later. Complete runtime post-check and Splunk readback before treating the route as live.
      </Alert>

      {actionError && <Alert color="red" title="Action failed">{actionError}</Alert>}
      {outcome && <MutationOutcome title={outcomeTitle} outcome={outcome} />}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <div>
            <Text className="panel-overline">Add a route</Text>
            <Title order={3}>Route a source to a destination</Title>
          </div>
          <Group grow>
            <TextInput label="Route ID" placeholder="asa_to_siem" value={routeId} onChange={(e) => setRouteId(e.currentTarget.value)} required />
            <Select
              label="Source"
              placeholder={sourcesQuery.isError ? 'Could not load sources' : sourcesQuery.data?.sources.length ? 'Select a source' : 'No sources configured yet'}
              data={sourceOptions}
              value={source}
              onChange={(value) => {
                setSource(value);
                const selected = (sourcesQuery.data?.sources || []).find((item) => item.name === value);
                if (selected?.vendor_product) setPack(selected.vendor_product);
              }}
              searchable
            />
            <TextInput
              label="SC4S vendor_product (source type)"
              placeholder={sourceVendorProduct || 'cisco_asa'}
              value={pack}
              onChange={(e) => setPack(e.currentTarget.value)}
              required
            />
            <Select
              label="Destination"
              placeholder={destinationsQuery.isError ? 'Could not load destinations' : destinationOptions.length ? 'Select a destination' : 'No SELECT-mode destinations saved yet'}
              data={destinationOptions}
              value={destination}
              onChange={setDestination}
              searchable
              description="Labels show type plus destination ID; full IDs remain available in the menu search and saved inventory."
            />
          </Group>
          {sourcesQuery.isError ? <Alert color="red" title="Unable to load source prerequisites">{operatorSafeErrorMessage(sourcesQuery.error)}</Alert> : null}
          {destinationsQuery.isError ? <Alert color="red" title="Unable to load destination prerequisites">{operatorSafeErrorMessage(destinationsQuery.error)}</Alert> : null}
          {prerequisiteQueryError ? (
            <Alert color="red" title="Route submission blocked">
              Source or destination data could not be loaded. Resolve the errors above before saving a route.
            </Alert>
          ) : null}
          <Checkbox
            label="Validate and reload SC4S now (leave unchecked to stage only)"
            checked={applyNow}
            onChange={(e) => setApplyNow(e.currentTarget.checked)}
          />
          <Group>
            <Button
              loading={busyKey === 'upsert'}
              disabled={prerequisiteQueryError || !routeId.trim() || !source || !pack.trim() || !destination}
              onClick={submitRoute}
            >
              {applyNow ? 'Save, validate and reload SC4S' : 'Stage route'}
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Title order={3}>Configured routes</Title>
            </div>
            <Badge variant="light" color="cyan">{routesQuery.data?.routes.length ?? 0} saved</Badge>
          </Group>
          {routesQuery.isLoading ? <Loader size="sm" /> : null}
          {routesQuery.isError ? <Alert color="red" title="Failed to load routes">{operatorSafeErrorMessage(routesQuery.error)}</Alert> : null}
          {routesQuery.data?.routes.length ? (
            <DataTable
              data={routesQuery.data.routes}
              searchPlaceholder="Search by route ID, source, destination…"
              miw={1040}
              columns={[
                colHelper.accessor('id', {
                  header: 'Route',
                  cell: (info) => <Code className="breakable-code-text">{info.getValue()}</Code>,
                }),
                colHelper.accessor('source', {
                  header: 'Source',
                  cell: (info) => <Text size="sm" className="breakable-table-text">{info.getValue()}</Text>,
                }),
                colHelper.accessor('pack', {
                  header: 'Source type',
                  cell: (info) => <Text size="sm" className="breakable-table-text">{info.getValue()}</Text>,
                }),
                colHelper.accessor('selector', {
                  header: 'Config file',
                  cell: (info) => info.getValue()
                    ? <Code className="breakable-code-text">{info.getValue()}</Code>
                    : <Text size="sm" c="dimmed">Generated from route ID</Text>,
                }),
                colHelper.display({
                  id: 'destination',
                  header: 'Destination',
                  cell: (info) => {
                    const e = info.row.original;
                    return (
                      <Badge className="breakable-badge" variant="light" color={e.destination_kind === 'hec' ? 'cyan' : 'violet'}>
                        {e.destination_kind.toUpperCase()} {e.destination_id}
                      </Badge>
                    );
                  },
                }),
                colHelper.accessor('apply_mode', {
                  header: 'Apply mode',
                  cell: (info) => <Badge color="gray" variant="light">{info.getValue() || 'reloadable'}</Badge>,
                }),
                colHelper.display({
                  id: 'actions',
                  header: '',
                  cell: (info) => (
                    <Button
                      color="red"
                      variant="light"
                      size="xs"
                      loading={busyKey === `delete:${info.row.original.id}`}
                      onClick={() => setDeleteCandidate(info.row.original)}
                    >
                      Delete
                    </Button>
                  ),
                }),
              ]}
            />
          ) : !routesQuery.isLoading && !routesQuery.isError ? (
            <Paper withBorder p="md" radius="md">
              <Text c="dimmed">No routes configured yet. Add a source and a SELECT-mode destination first.</Text>
            </Paper>
          ) : null}
          {deleteCandidate ? <DeleteConfirmation objectLabel={`route ${deleteCandidate.id}`} busy={busyKey === `delete:${deleteCandidate.id}`} onCancel={() => setDeleteCandidate(null)} onConfirm={() => removeRoute(deleteCandidate)} /> : null}
        </Stack>
      </Card>
    </Stack>
  );
}
