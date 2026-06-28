import {
  Alert,
  Anchor,
  Badge,
  Card,
  Divider,
  Group,
  Loader,
  List,
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

function truthyString(value: unknown) {
  return typeof value === 'string' && value.trim() ? value : null;
}

function capabilityItems(entry: CatalogueDetailEntry) {
  const map = [
    { key: 'parser', label: 'Parser artifact recorded' },
    { key: 'filters', label: 'Filter artifact recorded' },
    { key: 'postfilters', label: 'Postfilter artifact recorded' },
    { key: 'log_reduction', label: 'Log reduction artifact recorded' },
    { key: 'splunk_props_transforms', label: 'Splunk props/transforms recorded' },
    { key: 'cim_mapping', label: 'CIM mapping recorded' },
    { key: 'ocsf_mapping', label: 'OCSF mapping recorded' },
    { key: 'fixtures', label: 'Test fixtures recorded' },
    { key: 'syntax_validated', label: 'Syntax check evidence recorded' },
    { key: 'splunk_ingestion_validated', label: 'Splunk ingestion evidence recorded' },
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
          <Text className="panel-overline">Recorded capability evidence</Text>
          <Title order={3}>Capabilities reported by evidence</Title>
        </div>

        {enabled.length > 0 ? (
          <div className="catalogue-chip-row">
            {enabled.map((label) => (
              <Badge key={label} color="cyan" variant="light">{label}</Badge>
            ))}
          </div>
        ) : (
          <EmptyEvidence title="No capability evidence recorded yet" body="This entry does not yet expose parser, fixture, reduction, or Splunk-validation signals." />
        )}

      </Stack>
    </Card>
  );
}

function ValidationPanel({ entry }: { entry: CatalogueDetailEntry }) {
  const state = truthyString(entry.validation?.state) || 'Unknown';
  const lastVerifiedAt = truthyString(entry.validation?.last_verified_at) || 'Not recorded';
  const validatedBy = truthyString(entry.validation?.validated_by) || 'Not recorded';
  const summary = truthyString(entry.validation?.summary);
  const evidencePaths = Array.isArray(entry.validation?.evidence_paths) ? entry.validation.evidence_paths : [];

  return (
    <Card className="catalogue-evidence-card" withBorder>
      <Stack gap="md">
        <div>
          <Text className="panel-overline">Review and validation evidence</Text>
          <Title order={3}>Catalogue review state</Title>
        </div>

        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <EvidencePair label="Recorded validation state" value={formatTokenLabel(state)} />
          <EvidencePair label="Last evidence timestamp" value={lastVerifiedAt} />
          <EvidencePair label="Reviewed/validated by" value={validatedBy} />
          <EvidencePair label="Review status" value={entry.review_status ? formatTokenLabel(entry.review_status) : reviewStateLabel(entry)} />
          <EvidencePair label="Community rating" value="Not recorded" />
          <EvidencePair label="Manager evidence score" value={`${entry.quality_score}/5 · ${formatTokenLabel(entry.quality_status)}`} />
        </SimpleGrid>

        {summary ? (
          <Paper withBorder p="md" radius="md">
            <Text className="panel-overline">Validation summary</Text>
            <Text size="sm">{summary}</Text>
          </Paper>
        ) : (
          <EmptyEvidence title="No human-readable validation summary recorded" body="This entry has not yet published human-readable fixture or Splunk-evidence notes." />
        )}

        {evidencePaths.length > 0 ? (
          <Stack gap="xs">
            <Text className="panel-overline">Evidence file paths</Text>
            <List spacing="xs" size="sm">
              {evidencePaths.map((path) => (
                <List.Item key={path}><Text className="catalogue-code" span>{path}</Text></List.Item>
              ))}
            </List>
          </Stack>
        ) : (
          <EmptyEvidence title="No evidence file paths recorded" body="No evidence file paths are recorded for this entry." />
        )}
      </Stack>
    </Card>
  );
}

function ComparisonPanel({ entry }: { entry: CatalogueDetailEntry }) {
  const comparison = entry.comparison_to_upstream || {};
  const eventDelta = Array.isArray(comparison.event_family_delta) ? comparison.event_family_delta : [];
  const fieldDelta = Array.isArray(comparison.field_extraction_delta) ? comparison.field_extraction_delta : [];
  const fixtureSummary = truthyString(comparison.fixture_validation_summary);

  return (
    <Card className="catalogue-detail-card" withBorder>
      <Stack gap="md">
        <div>
          <Text className="panel-overline">Comparison with upstream SC4S</Text>
          <Title order={3}>Relationship to upstream and recorded differences</Title>
        </div>

        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <EvidencePair label="Relationship" value={formatTokenLabel(truthyString(comparison.relationship) || entry.relationship_to_upstream)} />
          <EvidencePair label="Reduction added" value={comparison.reduction_added ? 'Yes' : 'No'} />
          <EvidencePair label="Splunk knowledge added" value={comparison.splunk_knowledge_added ? 'Yes' : 'No'} />
          <EvidencePair label="Changed event families" value={String(eventDelta.length)} />
        </SimpleGrid>

        <Divider color="rgba(138, 158, 184, 0.18)" />

        {eventDelta.length > 0 ? (
          <Stack gap="xs">
            <Text className="panel-overline">Event families added or changed</Text>
            <div className="catalogue-chip-row">
              {eventDelta.map((value) => (
                <Badge key={value} variant="light" color="cyan">{value}</Badge>
              ))}
            </div>
          </Stack>
        ) : (
          <EmptyEvidence title="No event-family delta recorded" body="The entry does not currently report distinct upstream event-family changes." />
        )}

        {fieldDelta.length > 0 ? (
          <Stack gap="xs">
            <Text className="panel-overline">Changed field extractions</Text>
            <div className="catalogue-chip-row">
              {fieldDelta.map((value) => (
                <Badge key={value} variant="light" color="violet">{value}</Badge>
              ))}
            </div>
          </Stack>
        ) : (
          <EmptyEvidence title="No field extraction delta recorded" body="No field-level additions are reported for this entry." />
        )}

        {fixtureSummary ? (
          <Paper withBorder p="md" radius="md">
            <Text className="panel-overline">Fixture validation summary</Text>
            <Text size="sm">{fixtureSummary}</Text>
          </Paper>
        ) : (
          <EmptyEvidence title="No fixture validation summary recorded" body="This entry does not yet include fixture-driven summary text." />
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
          <Text className="panel-overline">Recorded artifacts</Text>
          <Title order={3}>Artifact inventory by type</Title>
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
            Catalogue entries, downloaded artifacts, and capability evidence are for review only. Nothing is applied to SC4S until you import and install a pack through Manager. After installing, reload SC4S and use Splunk readback to confirm.
          </Alert>

          <div className="catalogue-chip-row">
            {entry.origins.map((origin) => (
              <Badge key={origin} variant={origin === entry.effective_origin ? 'filled' : 'light'} color={origin === entry.effective_origin ? 'cyan' : 'gray'}>
                {originLabel(origin)}
              </Badge>
            ))}
            <Badge variant="light" color="gray">{formatTokenLabel(entry.relationship_to_upstream)}</Badge>
            <Badge variant="light" color="gray">Trust level: {formatTokenLabel(entry.trust_level)}</Badge>
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
              Community issues, PRs, and snippets remain discovery inputs until maintainer review, local validation, and Splunk evidence support promotion.
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

      <SimpleGrid cols={{ base: 1, lg: 4 }}>
        <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
          <Text className="panel-overline">Primary catalogue origin</Text>
          <Title order={3}>{originLabel(entry.effective_origin)}</Title>
          <Text size="sm" c="dimmed">Primary catalogue origin for this entry.</Text>
        </Paper>
        <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
          <Text className="panel-overline">Provenance source type</Text>
          <Title order={3}>{entry.provenance?.source_kind ? formatTokenLabel(entry.provenance.source_kind) : 'Not recorded'}</Title>
          <Text size="sm" c="dimmed">Where this catalogue record came from: SC4S Library, community input, or upstream SC4S inventory.</Text>
        </Paper>
        <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
          <Text className="panel-overline">Recorded artifacts</Text>
          <Title order={3}>{entry.artifacts.length}</Title>
          <Text size="sm" c="dimmed">Files or snippets recorded for this catalogue entry; not necessarily applied locally.</Text>
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
              <EvidencePair label="Validation state" value={formatTokenLabel(truthyString(entry.validation?.state) || 'Unknown')} />
              <EvidencePair label="Primary catalogue origin" value={originLabel(entry.effective_origin)} />
              <EvidencePair label="Source review state" value={entry.source_status ? formatTokenLabel(entry.source_status) : 'Not recorded'} />
            </SimpleGrid>
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
        <ValidationPanel entry={entry} />
        <ComparisonPanel entry={entry} />
        <ArtifactsPanel entry={entry} />
        <PresetsPanel entry={entry} />
      </SimpleGrid>
    </Stack>
  );
}
