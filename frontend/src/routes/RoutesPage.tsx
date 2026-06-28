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
  ScrollArea,
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
  deleteRoute,
  listDestinations,
  listRoutes,
  listSources,
  upsertRoute,
  type RouteEntry,
} from '../api/operations';

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
      .filter((item) => item.id !== 'DEFAULT')
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
        <Text c="dimmed">Save selector-based routes from an onboarded source and SC4S vendor_product to a SELECT-mode destination.</Text>
      </div>

      <Alert color="cyan" title="How route changes become live" variant="light">
        A route writes a staged selector under <Code>local/config/app_parsers/selectors/</Code> that matches the SC4S vendor_product and sends matching events to a SELECT-mode destination. The route remains staged until validation and reload; prove it is live with Splunk readback of a marker event.
      </Alert>

      {actionError && <Alert color="red" title="Action failed">{actionError}</Alert>}
      {outcome && <MutationOutcome title={outcomeTitle} outcome={outcome} />}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <div>
            <Text className="panel-overline">Stage route</Text>
            <Title order={3}>Source → vendor_product → destination</Title>
          </div>
          <Group grow>
            <TextInput label="Route ID / selector name" placeholder="asa_to_siem" value={routeId} onChange={(e) => setRouteId(e.currentTarget.value)} required />
            <Select
              label="Source"
              placeholder={sourcesQuery.isError ? 'Source inventory failed to load' : sourcesQuery.data?.sources.length ? 'Select an onboarded source' : 'No sources onboarded yet'}
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
              label="SC4S vendor_product"
              placeholder={sourceVendorProduct || 'cisco_asa'}
              value={pack}
              onChange={(e) => setPack(e.currentTarget.value)}
              required
            />
            <Select
              label="Destination"
              placeholder={destinationsQuery.isError ? 'Destination inventory failed to load' : destinationOptions.length ? 'Select a destination' : 'No non-default destinations saved yet'}
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
              Resolve prerequisite inventory failures before saving a route; otherwise the selector could target stale or unknown source/destination state.
            </Alert>
          ) : null}
          <Checkbox
            label="Validate and reload SC4S now. Leave unchecked to keep this route staged."
            checked={applyNow}
            onChange={(e) => setApplyNow(e.currentTarget.checked)}
          />
          <Group>
            <Button
              loading={busyKey === 'upsert'}
              disabled={prerequisiteQueryError || !routeId.trim() || !source || !pack.trim() || !destination}
              onClick={submitRoute}
            >
              {applyNow ? 'Stage, validate, and reload' : 'Save staged route'}
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Text className="panel-overline">Saved route entries</Text>
              <Title order={3}>Saved route staging inventory</Title>
            </div>
            <Badge variant="light" color="cyan">{routesQuery.data?.routes.length ?? 0} saved</Badge>
          </Group>
          {routesQuery.isLoading ? <Loader size="sm" /> : null}
          {routesQuery.isError ? <Alert color="red" title="Failed to load routes">{operatorSafeErrorMessage(routesQuery.error)}</Alert> : null}
          {routesQuery.data?.routes.length ? (
            <ScrollArea type="auto" offsetScrollbars>
            <Table striped highlightOnHover miw={1040}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Route</Table.Th>
                  <Table.Th>Source</Table.Th>
                  <Table.Th>vendor_product</Table.Th>
                  <Table.Th>Selector path</Table.Th>
                  <Table.Th>Destination</Table.Th>
                  <Table.Th>Apply/reload mode</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {routesQuery.data.routes.map((entry) => (
                  <Table.Tr key={entry.id}>
                    <Table.Td><Code className="breakable-code-text" title={entry.id}>{entry.id}</Code></Table.Td>
                    <Table.Td><Text size="sm" className="breakable-table-text" title={entry.source}>{entry.source}</Text></Table.Td>
                    <Table.Td><Text size="sm" className="breakable-table-text" title={entry.pack}>{entry.pack}</Text></Table.Td>
                    <Table.Td>
                      {entry.selector ? (
                        <Code className="breakable-code-text" title={entry.selector}>{entry.selector}</Code>
                      ) : (
                        <Text size="sm" c="dimmed">Generated from route ID</Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Badge
                        className="breakable-badge"
                        variant="light"
                        color={entry.destination_kind === 'hec' ? 'cyan' : 'violet'}
                        title={`${entry.destination_kind.toUpperCase()} ${entry.destination_id}`}
                      >
                        {entry.destination_kind.toUpperCase()} {entry.destination_id}
                      </Badge>
                    </Table.Td>
                    <Table.Td><Badge color="gray" variant="light">{entry.apply_mode || 'reloadable'}</Badge></Table.Td>
                    <Table.Td>
                      <Button
                        color="red"
                        variant="light"
                        size="xs"
                        loading={busyKey === `delete:${entry.id}`}
                        onClick={() => removeRoute(entry)}
                      >
                        Delete
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            </ScrollArea>
          ) : !routesQuery.isLoading && !routesQuery.isError ? (
            <Paper withBorder p="md" radius="md">
              <Text c="dimmed">No route entries saved yet. Routes require an onboarded source and a saved non-default SELECT-mode destination.</Text>
            </Paper>
          ) : null}
        </Stack>
      </Card>
    </Stack>
  );
}
