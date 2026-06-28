import {
  Alert,
  Badge,
  Card,
  Group,
  List,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { useQuery } from '@tanstack/react-query';

import { listCatalogue, listPacks } from '../api/packs';
import { listLibraryImports, listLibrarySources } from '../api/library';
import { getRuntimeState } from '../api/runtime';
import { RouterAnchor } from '../components/RouterAnchor';
import { operatorSafeErrorMessage } from '../lib/displayError';

function RuntimeHealthSection() {
  const runtimeQuery = useQuery({
    queryKey: ['runtime', 'state'],
    queryFn: ({ signal }) => getRuntimeState(signal),
    retry: 1,
  });

  if (runtimeQuery.isLoading) {
    return (
      <Stack gap="sm">
        <Title order={2}>Runtime health</Title>
        <Text c="dimmed" size="sm">Loading runtime state…</Text>
      </Stack>
    );
  }

  if (runtimeQuery.isError || !runtimeQuery.data) {
    return (
      <Stack gap="sm">
        <Title order={2}>Runtime health</Title>
        <Alert color="orange" title="Runtime state unavailable">
          Unable to load runtime state. The Manager service may be unreachable. Check Manager logs for details.
        </Alert>
        <Text size="xs" c="dimmed">
          Saved config does not prove SC4S is processing events — use Splunk readback to confirm.
        </Text>
      </Stack>
    );
  }

  const rt = runtimeQuery.data;
  const errors = rt.warnings.filter((w) => w.severity === 'error');
  const warnOnly = rt.warnings.filter((w) => w.severity === 'warning');
  const desiredNotLive = rt.listeners.filter((l) => l.desired && !l.live);
  const counterSummary = rt.counters.reduce<Record<string, number>>((acc, c) => {
    if (c.metric === 'processed' || c.metric === 'written' || c.metric === 'dropped') {
      acc[c.metric] = (acc[c.metric] ?? 0) + c.value;
    }
    return acc;
  }, {});

  return (
    <Stack gap="sm">
      <Group align="baseline">
        <Title order={2}>Runtime health</Title>
        <Badge color={rt.ok ? 'green' : errors.length > 0 ? 'red' : 'yellow'} size="sm">
          {rt.ok ? 'Healthy' : errors.length > 0 ? 'Errors' : 'Warnings'}
        </Badge>
      </Group>

      <Alert color="blue" variant="light">
        <Text size="xs">
          Saved config does not prove SC4S is processing events — use Splunk readback to confirm.
        </Text>
      </Alert>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
        {/* Manager + control daemon card */}
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">Manager</Text>
          <Text fw={500}>{rt.manager.version}</Text>
          <Text size="xs" c="dimmed" mt={4}>
            Manager service:{' '}
            <Badge color={rt.control_daemon.ok ? 'green' : 'red'} size="xs">
              {rt.control_daemon.ok ? 'reachable' : 'unreachable'}
            </Badge>
          </Text>
          {rt.control_daemon.error && (
            <Text size="xs" c="red" mt={2}>{rt.control_daemon.error}</Text>
          )}
        </Card>

        {/* SC4S process card */}
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">SC4S process</Text>
          <Group gap="xs" align="center">
            <Badge color={rt.sc4s.running ? 'green' : 'red'} size="sm">
              {rt.sc4s.status ?? (rt.sc4s.running ? 'running' : 'stopped')}
            </Badge>
            {rt.sc4s.health && (
              <Badge color={rt.sc4s.health === 'healthy' ? 'green' : 'orange'} size="xs" variant="light">
                {rt.sc4s.health}
              </Badge>
            )}
          </Group>
          {rt.sc4s.image_version && (
            <Text size="xs" c={rt.sc4s.version_drift ? 'red' : 'dimmed'} mt={4}>
              {rt.sc4s.version_drift ? '⚠ ' : ''}Image: {rt.sc4s.image_version}
              {rt.sc4s.version_drift && ` (supported: ${rt.sc4s.supported_version})`}
            </Text>
          )}
        </Card>

        {/* Listener card */}
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">Listeners</Text>
          {rt.listeners.length === 0 ? (
            <Text size="sm" c="dimmed">No desired listeners configured</Text>
          ) : (
            <List size="xs" spacing={2}>
              {rt.listeners.map((l) => (
                <List.Item key={`${l.protocol}-${l.port}`}>
                  <Group gap={4}>
                    <Text size="xs">
                      {l.protocol.toUpperCase()} {l.port}
                    </Text>
                    <Badge
                      color={l.live ? 'green' : l.desired ? 'red' : 'gray'}
                      size="xs"
                      variant="light"
                    >
                      {l.live ? 'live' : l.desired ? 'not live' : 'undesired'}
                    </Badge>
                  </Group>
                </List.Item>
              ))}
            </List>
          )}
          {desiredNotLive.length > 0 && (
            <Text size="xs" c="red" mt={4}>
              {desiredNotLive.length} desired port{desiredNotLive.length > 1 ? 's' : ''} not listening
            </Text>
          )}
        </Card>

        {/* Counter summary card */}
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">Counter summary</Text>
          {rt.counters.length === 0 ? (
            <Text size="xs" c="dimmed">No metrics (control daemon may be unreachable)</Text>
          ) : (
            <Stack gap={2} mt={4}>
              {Object.entries(counterSummary).map(([metric, total]) => (
                <Group key={metric} justify="space-between">
                  <Text size="xs" c="dimmed">{metric}</Text>
                  <Text size="xs" fw={500}>{total.toLocaleString()}</Text>
                </Group>
              ))}
              <Text size="xs" c="dimmed" mt={2}>{rt.counters.length} total rows</Text>
            </Stack>
          )}
        </Card>

        {/* Destinations card */}
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">Destinations</Text>
          {rt.destinations.length === 0 ? (
            <Text size="xs" c="dimmed">No destination metrics available</Text>
          ) : (
            <Table fz="xs" mt={4}>
              <Table.Tbody>
                {rt.destinations.map((d) => (
                  <Table.Tr key={d.id}>
                    <Table.Td>{d.id}</Table.Td>
                    <Table.Td>
                      <Text size="xs" c="green">{d.written.toLocaleString()} written</Text>
                      {d.dropped > 0 && (
                        <Text size="xs" c="red">{d.dropped.toLocaleString()} dropped</Text>
                      )}
                      {d.queued != null && d.queued > 0 && (
                        <Text size="xs" c="orange">{d.queued.toLocaleString()} queued</Text>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>

        {/* Warnings/errors card */}
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">Runtime warnings</Text>
          {rt.warnings.length === 0 ? (
            <Text size="xs" c="green" mt={4}>No warnings</Text>
          ) : (
            <Stack gap={4} mt={4}>
              {errors.map((w, i) => (
                <Alert key={i} color="red" variant="light" p={6}>
                  <Text size="xs" fw={500}>{w.code}</Text>
                  <Text size="xs">{w.message}</Text>
                </Alert>
              ))}
              {warnOnly.map((w, i) => (
                <Alert key={i} color="yellow" variant="light" p={6}>
                  <Text size="xs" fw={500}>{w.code}</Text>
                  <Text size="xs">{w.message}</Text>
                </Alert>
              ))}
            </Stack>
          )}
        </Card>
      </SimpleGrid>

      <Text size="xs" c="dimmed">
        State generated at: {rt.generated_at}
      </Text>
    </Stack>
  );
}

export function Dashboard() {
  const packsQuery = useQuery({
    queryKey: ['packs'],
    queryFn: ({ signal }) => listPacks(signal),
  });
  const catalogueQuery = useQuery({
    queryKey: ['catalogue'],
    queryFn: ({ signal }) => listCatalogue({}, signal),
  });
  const librarySourcesQuery = useQuery({
    queryKey: ['library', 'sources'],
    queryFn: ({ signal }) => listLibrarySources(signal),
  });
  const libraryImportsQuery = useQuery({
    queryKey: ['library', 'imports'],
    queryFn: ({ signal }) => listLibraryImports(signal),
  });

  return (
    <Stack gap="lg">
      <div>
        <Title order={1}>Dashboard</Title>
        <Text c="dimmed">
          Overview of source catalogue coverage, local packs, SC4S Library imports, and Manager
          connection.
        </Text>
      </div>

      {packsQuery.isError && (
        <Alert color="red" title="Unable to load packs">
          {operatorSafeErrorMessage(packsQuery.error)}
        </Alert>
      )}
      {catalogueQuery.isError && (
        <Alert color="red" title="Unable to load source catalogue">
          {operatorSafeErrorMessage(catalogueQuery.error)}
        </Alert>
      )}
      {librarySourcesQuery.isError && (
        <Alert color="red" title="Could not load SecHub sources">
          {operatorSafeErrorMessage(librarySourcesQuery.error)}
        </Alert>
      )}
      {libraryImportsQuery.isError && (
        <Alert color="red" title="Could not load checked packs">
          {operatorSafeErrorMessage(libraryImportsQuery.error)}
        </Alert>
      )}

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">Source catalogue entries</Text>
          <Group justify="space-between" align="end">
            <Title order={2}>{catalogueQuery.data?.count ?? '—'}</Title>
            <RouterAnchor to="/catalogue">Browse</RouterAnchor>
          </Group>
        </Card>
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">Local packs</Text>
          <Group justify="space-between" align="end">
            <Title order={2}>{packsQuery.data?.count ?? '—'}</Title>
            <RouterAnchor to="/packs">Browse</RouterAnchor>
          </Group>
        </Card>
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">SecHub sources</Text>
          <Group justify="space-between" align="end">
            <div>
              <Title order={2}>{librarySourcesQuery.data?.sources?.length ?? '—'}</Title>
              <Text size="xs" c="dimmed">
                {libraryImportsQuery.isError ? 'SecHub connection unavailable — check source health' : `${libraryImportsQuery.data?.imports?.length ?? 0} packs checked`}
              </Text>
            </div>
            <RouterAnchor to="/library">Open</RouterAnchor>
          </Group>
        </Card>
        <Card withBorder shadow="sm" padding="lg">
          <Text size="sm" c="dimmed">Manager connection</Text>
          <Badge
            color={
              packsQuery.isSuccess && catalogueQuery.isSuccess
                ? 'green'
                : packsQuery.isError || catalogueQuery.isError
                  ? 'red'
                  : 'gray'
            }
          >
            {packsQuery.isSuccess && catalogueQuery.isSuccess
              ? 'Connected'
              : packsQuery.isError || catalogueQuery.isError
                ? 'Connection error'
                : 'Checking'}
          </Badge>
        </Card>
      </SimpleGrid>

      <RuntimeHealthSection />
    </Stack>
  );
}
