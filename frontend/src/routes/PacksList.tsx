import { Alert, Badge, Card, Group, Loader, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';

import { listPacks } from '../api/packs';
import { RouterAnchor } from '../components/RouterAnchor';
import { operatorSafeErrorMessage } from '../lib/displayError';

export function PacksList() {
  const packsQuery = useQuery({
    queryKey: ['packs'],
    queryFn: ({ signal }) => listPacks(signal),
  });

  if (packsQuery.isLoading) {
    return <Loader />;
  }

  if (packsQuery.isError) {
    return (
      <Alert color="red" title="Unable to load packs">
        {operatorSafeErrorMessage(packsQuery.error)}
      </Alert>
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Title order={1}>Local packs</Title>
          <Text c="dimmed">{packsQuery.data?.count ?? 0} local or built-in packs saved in Manager; review and export before apply.</Text>
        </div>
      </Group>

      <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }}>
        {packsQuery.data?.packs.map((pack) => (
          <Card key={pack.id} withBorder shadow="sm" padding="lg">
            <Stack gap="sm">
              <Group justify="space-between" align="start">
                <div>
                  <RouterAnchor to={`/packs/${encodeURIComponent(pack.id)}`} fw={700} size="lg">
                    {pack.display_name}
                  </RouterAnchor>
                  <Text size="sm" c="dimmed">{pack.vendor} / {pack.product}</Text>
                </div>
                <Badge>Version {pack.version}</Badge>
              </Group>
              <Text lineClamp={3}>{pack.description}</Text>
              <Group gap="xs">
                {pack.supported_transports.map((transport) => (
                  <Badge key={transport.id} variant={transport.recommended ? 'filled' : 'light'}>
                    {transport.transport} port {transport.default_port}
                  </Badge>
                ))}
              </Group>
            </Stack>
          </Card>
        ))}
      </SimpleGrid>
    </Stack>
  );
}
