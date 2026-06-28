import { Alert, Button, Card, Group, Loader, Select, Stack, Text, Title } from '@mantine/core';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { exportPack, listPacks } from '../api/packs';
import { RouterAnchor } from '../components/RouterAnchor';
import { triggerBlobDownload } from '../lib/download';
import { operatorSafeErrorMessage } from '../lib/displayError';

export function Exports() {
  const [packId, setPackId] = useState<string | null>(null);
  const packsQuery = useQuery({
    queryKey: ['packs'],
    queryFn: ({ signal }) => listPacks(signal),
  });
  const exportMutation = useMutation({
    mutationFn: (id: string) => exportPack(id),
    onSuccess: ({ blob, filename }) => triggerBlobDownload(blob, filename),
  });

  if (packsQuery.isLoading) {
    return <Loader />;
  }

  if (packsQuery.isError) {
    return <Alert color="red" title="Unable to load packs">{operatorSafeErrorMessage(packsQuery.error)}</Alert>;
  }

  const data = packsQuery.data?.packs.map((pack) => ({ value: pack.id, label: pack.display_name })) ?? [];

  return (
    <Stack gap="lg">
      <div>
        <Title order={1}>Export bundles</Title>
        <Text c="dimmed">Download generated SC4S/Splunk configuration and evidence artifacts for a selected local pack. Exporting does not apply changes.</Text>
      </div>
      <Card withBorder maw={640}>
        <Stack>
          <Select label="Local pack" placeholder="Choose a local pack" data={data} value={packId} onChange={setPackId} searchable />
          <Group>
            <Button disabled={!packId} loading={exportMutation.isPending} onClick={() => packId && exportMutation.mutate(packId)}>
              Download export bundle
            </Button>
            {packId && <RouterAnchor to={`/packs/${encodeURIComponent(packId)}`}>Review pack details</RouterAnchor>}
          </Group>
          {exportMutation.isError && <Alert color="red" title="Export download failed">{operatorSafeErrorMessage(exportMutation.error, 'Manager could not prepare the export. Check the selected pack and retry.')}</Alert>}
        </Stack>
      </Card>
    </Stack>
  );
}
