import {
  Alert,
  Anchor,
  Badge,
  Card,
  Group,
  List,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core';
import { useQuery } from '@tanstack/react-query';

import { type CatalogueDetail as CatalogueDetailEntry, getCatalogueEntry } from '../api/packs';
import { operatorSafeErrorMessage } from '../lib/displayError';

function formatTokenLabel(value: string) {
  return value
    .split(/[_-]/g)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ');
}

function originLabel(origin: string) {
  const labels: Record<string, string> = {
    'sc4s-inbuilt': 'SC4S built-in',
    'sc4s-inbuilt-lite': 'SC4S Lite',
    'sechub-resource': 'SC4S Library pack',
    'sechub-resources-pack': 'SC4S Library pack',
    'community-extra': 'Community candidate',
  };
  return labels[origin] || formatTokenLabel(origin);
}

function provenanceHostLabel(url?: string | null) {
  if (!url) return null;
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

function reviewStateLabel(entry: CatalogueDetailEntry) {
  if (entry.review_status) return formatTokenLabel(entry.review_status);
  if (entry.source_status === 'candidate') return 'Community candidate';
  if (entry.is_verified) return 'Validation evidence recorded';
  return formatTokenLabel(entry.quality_status);
}

function reviewTone(entry: CatalogueDetailEntry) {
  if (entry.review_status === 'deprecated') return 'red';
  if (entry.review_status === 'reviewed') return 'cyan';
  if (entry.review_status === 'unreviewed') return 'yellow';
  if (entry.source_status === 'candidate') return 'yellow';
  if (entry.is_verified) return 'cyan';
  if (entry.quality_status === 'deprecated') return 'red';
  return 'gray';
}

function truthyString(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value : null;
}

function capabilityItems(entry: CatalogueDetailEntry) {
  const map = [
    { key: 'parser', label: 'Parser' },
    { key: 'filters', label: 'Filter' },
    { key: 'postfilters', label: 'Post-filter' },
    { key: 'log_reduction', label: 'Log reduction' },
    { key: 'splunk_props_transforms', label: 'Splunk knowledge' },
    { key: 'cim_mapping', label: 'CIM mapping' },
    { key: 'ocsf_mapping', label: 'OCSF mapping' },
    { key: 'fixtures', label: 'Test events' },
    { key: 'syntax_validated', label: 'Syntax validated' },
    { key: 'splunk_ingestion_validated', label: 'Splunk tested' },
  ] as const;
  return map.filter((item) => Boolean(entry.capabilities[item.key])).map((item) => item.label);
}

function EmptyEvidence({ title, body }: { title: string; body: string }) {
  return (
    <Paper className="catalogue-empty-box" p="md">
      <Stack gap={4}>
        <Text fw={600}>{title}</Text>
        <Text size="sm" c="dimmed">{body}</Text>
      </Stack>
    </Paper>
  );
}

function EvidencePair({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={2}>
      <Text className="panel-overline">{label}</Text>
      <Text size="sm">{value}</Text>
    </Stack>
  );
}

function CapabilityPanel({ entry }: { entry: CatalogueDetailEntry }) {
  const enabled = capabilityItems(entry);
  return (
    <Card className="catalogue-detail-card" withBorder>
      <Stack gap="md">
        <div>
          <Text className="panel-overline">Included components</Text>
          <Title order={3}>What's included</Title>
        </div>

        {enabled.length > 0 ? (
          <div className="catalogue-chip-row">
            {enabled.map((label) => (
              <Badge key={label} color="cyan" variant="light">{label}</Badge>
            ))}
          </div>
        ) : (
          <EmptyEvidence title="No components recorded yet" body="This entry does not yet expose parser, fixture, reduction, or Splunk-validation signals." />
        )}

      </Stack>
    </Card>
  );
}

function ArtifactsPanel({ entry }: { entry: CatalogueDetailEntry }) {
  const artifactGroups = Object.entries(entry.artifact_inventory || {});

  return (
    <Card className="catalogue-detail-card" withBorder>
      <Stack gap="md">
        <div>
          <Text className="panel-overline">Files</Text>
          <Title order={3}>Files included in this source</Title>
        </div>

        {artifactGroups.length > 0 ? (
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            {artifactGroups.map(([kind, paths]) => (
              <Paper key={kind} withBorder p="md" radius="md">
                <Stack gap="xs">
                  <Group justify="space-between">
                    <Text fw={600}>{formatTokenLabel(kind)}</Text>
                    <Badge variant="light" color="cyan">{paths.length}</Badge>
                  </Group>
                  <List spacing="xs" size="sm">
                    {paths.slice(0, 5).map((path) => (
                      <List.Item key={path}><Text className="catalogue-code" span>{path}</Text></List.Item>
                    ))}
                  </List>
                  {paths.length > 5 && <Text size="xs" c="dimmed">+{paths.length - 5} more path(s)</Text>}
                </Stack>
              </Paper>
            ))}
          </SimpleGrid>
        ) : (
          <EmptyEvidence title="No artifact inventory recorded" body="No recorded file groups are available for this source entry." />
        )}

      </Stack>
    </Card>
  );
}

function PresetsPanel({ entry }: { entry: CatalogueDetailEntry }) {
  const presets = Array.isArray(entry.presets) ? entry.presets : [];
  return (
    <Card className="catalogue-detail-card" withBorder>
      <Stack gap="md">
        <div>
          <Text className="panel-overline">Presets</Text>
          <Title order={3}>Recorded preset variants</Title>
        </div>

        {presets.length > 0 ? (
          <Stack gap="sm">
            {presets.map((preset, index) => {
              const presetLabel = truthyString(preset.label) || truthyString(preset.id) || `Preset ${index + 1}`;
              const presetDescription = truthyString(preset.description);
              const presetNotes = truthyString(preset.notes);
              return (
              <Paper key={String(preset.id || index)} withBorder p="md" radius="md">
                <Stack gap={4}>
                  <Group justify="space-between">
                    <Text fw={600}>{presetLabel}</Text>
                    {preset.enabled_by_default ? <Badge color="cyan" variant="light">Default preset</Badge> : null}
                  </Group>
                  {presetDescription ? <Text size="sm">{presetDescription}</Text> : null}
                  {presetNotes ? <Text size="sm" c="dimmed">{presetNotes}</Text> : null}
                </Stack>
              </Paper>
            )})}
          </Stack>
        ) : (
          <EmptyEvidence title="No presets recorded" body="This entry reports no preset bundles or reduction options." />
        )}
      </Stack>
    </Card>
  );
}

export function CatalogueDetail({ entryId }: { entryId: string }) {
  const entryQuery = useQuery({
    queryKey: ['catalogue', entryId],
    enabled: Boolean(entryId),
    queryFn: ({ signal }) => getCatalogueEntry(entryId, signal),
  });

  if (entryQuery.isLoading) {
    return <Loader />;
  }

  if (entryQuery.isError) {
    return (
      <Alert color="red" title="Unable to load catalogue entry">
        {operatorSafeErrorMessage(entryQuery.error)}
      </Alert>
    );
  }

  const entry = entryQuery.data;
  if (!entry) {
    return <Alert color="yellow" title="No catalogue entry selected">Entry id is missing.</Alert>;
  }

  const candidateWarnings = entry.candidate_warnings ?? [];
  const knownLimitations = Array.isArray(entry.known_limitations) ? entry.known_limitations : [];
  const presets = Array.isArray(entry.presets) ? entry.presets : [];
  const provenanceHost = provenanceHostLabel(entry.provenance?.url || entry.provenance_url);
  const showCandidateWarning = entry.source_status === 'candidate' || entry.effective_origin === 'community-extra' || candidateWarnings.length > 0;
  const validationSummary = truthyString(entry.validation?.summary);

  return (
    <Stack gap="lg">
      <Paper className="catalogue-hero" withBorder p="xl" radius="lg">
        <Stack gap="lg">
          <Group justify="space-between" align="start">
            <Group gap="md" align="start" wrap="nowrap">
              <ThemeIcon size={54} radius="lg" variant="light" color={reviewTone(entry)}>
                <Text fw={700}>{entry.vendor.slice(0, 1).toUpperCase()}</Text>
              </ThemeIcon>
              <Stack gap={4}>
                <Text className="panel-overline">Source catalogue entry</Text>
                <Title order={1}>{entry.display_name}</Title>
                <Text c="dimmed">
                  <span className="catalogue-code">{entry.id}</span> · {entry.vendor} / {entry.product}
                </Text>
              </Stack>
            </Group>
            <Group gap="xs">
              <Badge color={reviewTone(entry)} variant={entry.source_status === 'candidate' ? 'light' : 'filled'}>
                {reviewStateLabel(entry)}
              </Badge>
              <Badge variant="light" color="gray">Evidence score {entry.quality_score}/5</Badge>
            </Group>
          </Group>

          <Text className="readable-panel-text" maw={900}>{entry.summary}</Text>

          <Alert color="blue" title="Viewing only — not applied to SC4S" variant="light">
            Nothing is applied to SC4S until you import and install a pack through the SC4S Library page, validate locally, and capture runtime plus Splunk readback evidence.
          </Alert>

          <div className="catalogue-chip-row">
            {entry.origins.map((origin) => (
              <Badge key={origin} variant={origin === entry.effective_origin ? 'filled' : 'light'} color={origin === entry.effective_origin ? 'cyan' : 'gray'}>
                {originLabel(origin)}
              </Badge>
            ))}
          </div>
        </Stack>
      </Paper>

      {showCandidateWarning && (
        <Alert color="yellow" title="Unvalidated community candidate" variant="light">
          <Stack gap={4}>
            {candidateWarnings.length > 0 ? (
              candidateWarnings.map((warning) => (
                <Text key={warning} size="sm">{warning}</Text>
              ))
            ) : (
              <Text size="sm">Community candidate only. Not validated for production or Splunk ingestion.</Text>
            )}
            <Text size="xs" c="dimmed">
              Community issues, PRs, and snippets are for review only and remain discovery inputs until maintainer review, local validation, and Splunk evidence support promotion.
            </Text>
          </Stack>
        </Alert>
      )}

      {knownLimitations.length > 0 && (
        <Alert color="orange" title="Known limitations" variant="light">
          <List spacing="xs" size="sm">
            {knownLimitations.map((item) => (
              <List.Item key={item}>{item}</List.Item>
            ))}
          </List>
        </Alert>
      )}

      <SimpleGrid cols={{ base: 1, lg: 3 }}>
        <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
          <Text className="panel-overline">Primary catalogue origin</Text>
          <Title order={3}>{originLabel(entry.effective_origin)}</Title>
          <Text size="sm" c="dimmed">Primary catalogue origin for this entry.</Text>
        </Paper>
        <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
          <Text className="panel-overline">Files included</Text>
          <Title order={3}>{entry.artifacts.length}</Title>
          <Text size="sm" c="dimmed">Files recorded for this catalogue entry.</Text>
        </Paper>
        <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
          <Text className="panel-overline">Presets</Text>
          <Title order={3}>{presets.length}</Title>
          <Text size="sm" c="dimmed">Optional preset bundles or reduction choices reported for this entry.</Text>
        </Paper>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, xl: 2 }} spacing="lg">
        <Card className="catalogue-detail-card" withBorder>
          <Stack gap="md">
            <div>
              <Text className="panel-overline">Review status and provenance</Text>
              <Title order={3}>Identity and review status</Title>
            </div>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <EvidencePair label="Review status" value={reviewStateLabel(entry)} />
              <EvidencePair label="Primary catalogue origin" value={originLabel(entry.effective_origin)} />
            </SimpleGrid>
            {validationSummary ? <EvidencePair label="Validation summary" value={validationSummary} /> : <EmptyEvidence title="No human-readable validation summary recorded" body="Review machine evidence paths and complete local validation before use." />}
            {provenanceHost && (entry.provenance?.url || entry.provenance_url) ? (
              <Paper withBorder p="md" radius="md">
                <Text className="panel-overline">Provenance URL</Text>
                <Anchor href={entry.provenance?.url || entry.provenance_url || undefined} target="_blank" rel="noreferrer">
                  {provenanceHost}
                </Anchor>
              </Paper>
            ) : (
              <EmptyEvidence title="No provenance URL recorded" body="This entry does not currently expose an external provenance link." />
            )}
          </Stack>
        </Card>

        <CapabilityPanel entry={entry} />
        <ArtifactsPanel entry={entry} />
        <PresetsPanel entry={entry} />
      </SimpleGrid>
    </Stack>
  );
}
