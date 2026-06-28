import { Alert, Button, Card, Code, Group, Loader, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { useMutation, useQuery } from '@tanstack/react-query';

import { exportPack, getPack } from '../api/packs';
import { triggerBlobDownload } from '../lib/download';
import { safeHttpUrl } from '../lib/url';
import { operatorSafeErrorMessage } from '../lib/displayError';

function formatTokenLabel(value: string) {
  return value
    .split(/[_-]/g)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ');
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'Not recorded';
  if (Array.isArray(value)) return value.length ? value.map(String).join(', ') : 'Not recorded';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function PackDetail({ packId }: { packId: string }) {
  const packQuery = useQuery({
    queryKey: ['packs', packId],
    enabled: Boolean(packId),
    queryFn: ({ signal }) => getPack(packId, signal),
  });
  const exportMutation = useMutation({
    mutationFn: () => exportPack(packId),
    onSuccess: ({ blob, filename }) => triggerBlobDownload(blob, filename),
  });

  if (packQuery.isLoading) {
    return <Loader />;
  }

  if (packQuery.isError) {
    return (
      <Alert color="red" title="Unable to load pack">
        {operatorSafeErrorMessage(packQuery.error)}
      </Alert>
    );
  }

  const pack = packQuery.data;
  if (!pack) {
    return <Alert color="yellow" title="No pack selected">Pack id is missing.</Alert>;
  }

  const safePackUrl = safeHttpUrl(pack.url);

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="start">
        <div>
          <Title order={1}>{pack.display_name}</Title>
          <Text c="dimmed">Local pack {pack.id} · version {pack.version}</Text>
        </div>
        <Button onClick={() => exportMutation.mutate()} loading={exportMutation.isPending}>
          Download export bundle
        </Button>
      </Group>

      {exportMutation.isError && (
        <Alert color="red" title="Export failed">{operatorSafeErrorMessage(exportMutation.error, 'Manager could not prepare the export. Check the selected pack and retry.')}</Alert>
      )}

      <Alert color="blue" title="Export only — not applied to SC4S" variant="light">
        Downloading this bundle creates a local export file only. SC4S is not updated until you import and apply it through Manager. After applying, reload SC4S and search Splunk for incoming events to confirm it is working.
      </Alert>

      <Card withBorder>
        <Stack gap="xs">
          <Text>{pack.description}</Text>
          <Text>
            <strong>Reference URL:</strong>{' '}
            {safePackUrl ? <a href={safePackUrl} target="_blank" rel="noreferrer">{pack.url}</a> : pack.url}
          </Text>
          <Text><strong>Default index:</strong> {pack.default_index}</Text>
          <Text><strong>Default Splunk source:</strong> {pack.default_source}</Text>
          <Text><strong>Recommended ingestion transport:</strong> {pack.recommended_transport}</Text>
        </Stack>
      </Card>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Card withBorder>
          <Title order={3}>Supported ingestion transports</Title>
          <Stack mt="md">
            {pack.supported_transports.map((transport) => (
              <Card key={transport.id} withBorder padding="sm">
                <Text fw={700}>{transport.label}</Text>
                <Text size="sm">{formatTokenLabel(transport.transport)} · {formatTokenLabel(transport.syslog_protocol)} · {formatTokenLabel(transport.framing)}</Text>
                <Text size="sm">Syslog envelope: {formatTokenLabel(transport.envelope)}</Text>
                <Text size="sm">Log format: {formatTokenLabel(transport.payload_format)}</Text>
                <Text size="sm">Default port: {transport.default_port}</Text>
                {transport.notes && <Text size="sm" c="dimmed">{transport.notes}</Text>}
              </Card>
            ))}
          </Stack>
        </Card>

        <Card withBorder>
          <Title order={3}>Source product log version</Title>
          <Stack mt="md" gap="xs">
            <Text size="sm">Name: {displayValue(pack.source_log_version.name)}</Text>
            <Text size="sm">Minimum version: {displayValue(pack.source_log_version.min)}</Text>
            <Text size="sm">Maximum version: {displayValue(pack.source_log_version.max)}</Text>
            <Text size="sm" c="dimmed">Notes: {displayValue(pack.source_log_version.notes)}</Text>
          </Stack>
        </Card>

        <Card withBorder>
          <Title order={3}>Recorded validation</Title>
          <Stack mt="md" gap="xs">
            <Text size="sm">Reviewed/validated by: {displayValue(pack.validation.validated_by)}</Text>
            <Text size="sm">Validation evidence date: {displayValue(pack.validation.date_validated)}</Text>
            <Text size="sm">SC4S version: {displayValue(pack.validation.sc4s_version)}</Text>
            <Text size="sm">Splunk version: {displayValue(pack.validation.splunk_version)}</Text>
            <Text size="sm">Evidence: {displayValue(pack.validation.evidence)}</Text>
          </Stack>
        </Card>

        <Card withBorder>
          <Title order={3}>Events this pack expects to recognise</Title>
          <Stack mt="md">
            {pack.event_families.map((family) => (
              <Card key={family.id} withBorder padding="sm">
                <Text fw={700}>{family.label}</Text>
                <Text size="sm">How Manager identifies it: {family.match_engine}</Text>
                <Text size="sm">Expected sourcetype: {family.expected_sourcetype}</Text>
                <Text size="sm">Primary identifier field: {family.primary_id_field}</Text>
                <details>
                  <summary>Diagnostics: raw match expression</summary>
                  <Code block className="muted-code">{family.match}</Code>
                </details>
              </Card>
            ))}
          </Stack>
        </Card>

        <Card withBorder>
          <Title order={3}>Test event fixtures</Title>
          <Stack mt="md">
            {pack.test_event_sets.map((set) => (
              <Card key={set.id} withBorder padding="sm">
                <Text fw={700}>{set.id}</Text>
                <Text size="sm">Example event file: {set.path}</Text>
                <Text size="sm">Format: {set.format} / {String(set.wire_format)}</Text>
                <Text size="sm">Events: {set.event_count}; events per file: {set.events_per_file}</Text>
                <Text size="sm">Event boundary: {set.event_boundary}; record separator: {String(set.record_separator)}</Text>
                <Text size="sm">One per line: {String(set.one_event_per_line)}; multiline: {String(set.multiline)}</Text>
                <Text size="sm">Unique events: {String(set.unique_events)}</Text>
                <Text size="sm">Marker tokens: {displayValue(set.marker_tokens)}</Text>
                <Text size="sm">Timestamp policy: {displayValue(set.timestamp_policy?.source_time_mode)}</Text>
                <Text size="sm">Expected families: {displayValue(set.expected_families)}</Text>
              </Card>
            ))}
          </Stack>
        </Card>

        <Card withBorder>
          <Title order={3}>Included files for review/export</Title>
          <Stack mt="md">
            {pack.export_artifacts.map((artifact) => (
              <Card key={artifact.id} withBorder padding="sm">
                <Text fw={700}>{artifact.id}</Text>
                <Text size="sm">Pack source file: {artifact.source_path}</Text>
                <Text size="sm">SC4S export target path: {artifact.target_path}</Text>
                <Text size="sm">Secret material present: {artifact.contains_secrets ? 'Yes' : 'No'}</Text>
                <details>
                  <summary>Export diagnostics</summary>
                  <Text size="sm">Bundle group: {artifact.group}</Text>
                  <Text size="sm">File type: {String(artifact.kind)}</Text>
                  <Text size="sm">Rendered from template: {artifact.rendered ? 'Yes' : 'No'}</Text>
                  <Text size="sm">Required for export: {artifact.required ? 'Yes' : 'No'}</Text>
                </details>
              </Card>
            ))}
          </Stack>
        </Card>
      </SimpleGrid>
    </Stack>
  );
}
