import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Loader,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { CatalogueFacetItem, CatalogueListEntry, listCatalogue } from '../api/packs';
import { RouterAnchor } from '../components/RouterAnchor';
import { operatorSafeErrorMessage } from '../lib/displayError';

const ORIGIN_LABELS: Record<string, string> = {
  'sc4s-inbuilt': 'SC4S built-in',
  'sc4s-inbuilt-lite': 'SC4S Lite',
  'sechub-resource': 'SC4S Library pack',
  'community-extra': 'Community candidate',
};

const SOURCE_STATUS_LABELS: Record<string, string> = {
  candidate: 'Community candidate',
  validated: 'Source-review validation evidence',
  draft: 'Draft candidate',
  deprecated: 'Deprecated source',
};

export type CatalogueFilters = {
  q: string;
  origin: string | null;
  product: string | null;
  vendor: string | null;
  review_status?: string | null;
  min_quality_score: string | null;
  artifact_type: string | null;
  source_status: string | null;
  is_verified: boolean;
  has_reduction: boolean;
  has_splunk_knowledge: boolean;
};

export const EMPTY_FILTERS: CatalogueFilters = {
  q: '',
  origin: null,
  product: null,
  vendor: null,
  review_status: null,
  min_quality_score: null,
  artifact_type: null,
  source_status: null,
  is_verified: false,
  has_reduction: false,
  has_splunk_knowledge: false,
};

function facetOptions(items?: CatalogueFacetItem[]) {
  return (items || []).map((item) => ({ value: item.value, label: `${item.label} (${item.count})` }));
}

function formatTokenLabel(value: string) {
  return value
    .split(/[_-]/g)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ');
}

function originLabel(origin: string) {
  return ORIGIN_LABELS[origin] || formatTokenLabel(origin);
}

function sourceStatusLabel(sourceStatus?: string | null) {
  if (!sourceStatus) return null;
  return SOURCE_STATUS_LABELS[sourceStatus] || formatTokenLabel(sourceStatus);
}

function provenanceHostLabel(url?: string | null) {
  if (!url) return null;
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

function reviewStateLabel(entry: CatalogueListEntry) {
  if (entry.review_status) return formatTokenLabel(entry.review_status);
  if (entry.source_status === 'candidate') return 'Community candidate';
  if (entry.is_verified) return 'Validation evidence recorded';
  return formatTokenLabel(entry.quality_status);
}

function reviewTone(entry: CatalogueListEntry) {
  if (entry.review_status === 'deprecated') return 'red';
  if (entry.review_status === 'reviewed') return 'cyan';
  if (entry.review_status === 'unreviewed') return 'yellow';
  if (entry.source_status === 'candidate') return 'yellow';
  if (entry.is_verified) return 'cyan';
  if (entry.quality_status === 'deprecated') return 'red';
  return 'gray';
}

function activeFilters(filters: CatalogueFilters) {
  return [
    filters.q.trim() ? `Search: ${filters.q.trim()}` : null,
    filters.origin ? `Origin: ${originLabel(filters.origin)}` : null,
    filters.product ? `Product: ${filters.product}` : null,
    filters.vendor ? `Vendor: ${filters.vendor}` : null,
    filters.review_status ? `Review status: ${formatTokenLabel(filters.review_status)}` : null,
    filters.min_quality_score ? `Manager evidence ≥ ${filters.min_quality_score}/5` : null,
    filters.artifact_type ? `Recorded file: ${formatTokenLabel(filters.artifact_type)}` : null,
    filters.source_status ? `Status: ${sourceStatusLabel(filters.source_status)}` : null,
    filters.is_verified ? 'Recorded validation evidence only' : null,
    filters.has_reduction ? 'Has log reduction' : null,
    filters.has_splunk_knowledge ? 'Has Splunk props/transforms' : null,
  ].filter((value): value is string => Boolean(value));
}

function candidateWarning(entry: CatalogueListEntry) {
  return entry.candidate_warnings?.[0] || 'Community candidate only. Not validated for production or Splunk ingestion.';
}

function capabilityBadges(entry: CatalogueListEntry) {
  const items = [
    entry.capabilities.parser ? { label: 'Parser', color: 'cyan' } : null,
    entry.capabilities.splunk_props_transforms ? { label: 'Splunk knowledge', color: 'violet' } : null,
    entry.capabilities.log_reduction ? { label: 'Reduction', color: 'orange' } : null,
    entry.capabilities.fixtures ? { label: 'Fixtures', color: 'teal' } : null,
    entry.capabilities.syntax_validated ? { label: 'Syntax checked', color: 'lime' } : null,
    entry.capabilities.splunk_ingestion_validated ? { label: 'Splunk validated', color: 'green' } : null,
  ];
  return items.filter((value): value is { label: string; color: string } => Boolean(value));
}

function statText(entry: CatalogueListEntry) {
  const capabilityCount = capabilityBadges(entry).length;
  return `${capabilityCount} validated capability signal${capabilityCount === 1 ? '' : 's'} · quality ${entry.quality_score}/5`;
}

export function buildCatalogueParams(filters: CatalogueFilters) {
  const next: Record<string, string> = { limit: '60' };
  if (filters.q.trim()) next.q = filters.q.trim();
  if (filters.origin) next.origin = filters.origin;
  if (filters.product) next.product = filters.product;
  if (filters.vendor) next.vendor = filters.vendor;
  if (filters.review_status) next.review_status = filters.review_status;
  if (filters.min_quality_score) next.min_quality_score = filters.min_quality_score;
  if (filters.artifact_type) next.artifact_type = filters.artifact_type;
  if (filters.source_status) next.source_status = filters.source_status;
  if (filters.is_verified) next.is_verified = 'true';
  if (filters.has_reduction) next.has_reduction = 'true';
  if (filters.has_splunk_knowledge) next.has_splunk_knowledge = 'true';
  return next;
}

export function CatalogueListCard({ entry }: { entry: CatalogueListEntry }) {
  const candidateWarnings = entry.candidate_warnings ?? [];
  const provenanceHost = provenanceHostLabel(entry.provenance_url);
  const showCandidateWarning = entry.source_status === 'candidate' || entry.effective_origin === 'community-extra' || candidateWarnings.length > 0;
  const badges = capabilityBadges(entry);

  return (
    <Card className="catalogue-list-card" withBorder padding="lg">
      <Stack gap="md" h="100%">
        <Group justify="space-between" align="start" wrap="nowrap">
          <Group gap="sm" align="start" wrap="nowrap">
            <ThemeIcon size={42} radius="md" variant="light" color={reviewTone(entry)}>
              <Text fw={700} size="sm">{entry.vendor.slice(0, 1).toUpperCase()}</Text>
            </ThemeIcon>
            <Stack gap={2}>
              <Text className="panel-overline">{originLabel(entry.effective_origin)}</Text>
              <RouterAnchor to={`/catalogue/${encodeURIComponent(entry.id)}`} fw={700} size="lg">
                {entry.display_name}
              </RouterAnchor>
              <Text size="sm" c="dimmed">
                {entry.vendor} / {entry.product}
              </Text>
            </Stack>
          </Group>
          <Badge color={reviewTone(entry)} variant={entry.review_status === 'unreviewed' || entry.source_status === 'candidate' ? 'light' : 'filled'}>
            {reviewStateLabel(entry)}
          </Badge>
        </Group>

        <Text className="readable-panel-text" lineClamp={3}>{entry.summary}</Text>

        <div className="catalogue-chip-row">
          <Badge variant="light" color="gray">{formatTokenLabel(entry.relationship_to_upstream)}</Badge>
          <Badge variant="light" color="gray">No community rating</Badge>
          <Badge variant="light" color="gray">Manager evidence score {entry.quality_score}/5</Badge>
          {entry.source_status && (
            <Badge color="yellow" variant="outline">
              {sourceStatusLabel(entry.source_status)}
            </Badge>
          )}
        </div>

        {showCandidateWarning ? (
          <Alert color="yellow" title="Unvalidated candidate" variant="light">
            <Stack gap={4}>
              <Text size="sm">{candidateWarning(entry)}</Text>
              {provenanceHost && entry.provenance_url && (
                <Text size="xs" c="dimmed">
                  Review source evidence:{' '}
                  <Anchor href={entry.provenance_url} target="_blank" rel="noreferrer">
                    {provenanceHost}
                  </Anchor>
                </Text>
              )}
            </Stack>
          </Alert>
        ) : (
          <Paper withBorder p="sm" radius="md">
            <Stack gap={4}>
              <Text className="panel-overline">Evidence posture</Text>
              <Text size="sm">{statText(entry)}</Text>
              <Text size="xs" c="dimmed">
                Shown only from catalogue provenance, capability, and recorded validation evidence.
              </Text>
            </Stack>
          </Paper>
        )}

        <Stack gap="xs">
          <Text className="panel-overline">Catalogue origins</Text>
          <div className="catalogue-chip-row">
            {entry.origins.map((origin) => (
              <Badge key={origin} variant={origin === entry.effective_origin ? 'filled' : 'light'} color={origin === entry.effective_origin ? 'cyan' : 'gray'}>
                {originLabel(origin)}
              </Badge>
            ))}
          </div>
        </Stack>

        <Stack gap="xs" mt="auto">
          <Text className="panel-overline">Recorded capabilities</Text>
          {badges.length > 0 ? (
            <div className="catalogue-chip-row">
              {badges.map((badge) => (
                <Badge key={badge.label} color={badge.color} variant="light">
                  {badge.label}
                </Badge>
              ))}
            </div>
          ) : (
            <Text size="sm" c="dimmed">
              No parser, reduction, fixture, or Splunk ingestion evidence is recorded yet.
            </Text>
          )}
        </Stack>

        <Group justify="space-between" align="center" mt="xs">
          <Text size="sm" c="dimmed">Review provenance, evidence, and recorded files before download, import, or apply.</Text>
          <Button component={RouterAnchor} to={`/catalogue/${encodeURIComponent(entry.id)}`} variant="light" color="cyan">
            View details
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

export function CatalogueList() {
  const [filters, setFilters] = useState<CatalogueFilters>(EMPTY_FILTERS);

  const params = useMemo(() => buildCatalogueParams(filters), [filters]);

  const catalogueQuery = useQuery({
    queryKey: ['catalogue', params],
    queryFn: ({ signal }) => listCatalogue(params, signal),
  });

  const facets = catalogueQuery.data?.facets;
  const selectedFilters = activeFilters(filters);

  if (catalogueQuery.isLoading) {
    return <Loader />;
  }

  if (catalogueQuery.isError) {
    return (
      <Alert color="red" title="Unable to load catalogue">
        {operatorSafeErrorMessage(catalogueQuery.error)}
      </Alert>
    );
  }

  const totalEntries = catalogueQuery.data?.count ?? 0;
  const reviewedCount = facets?.review_statuses?.find((item) => item.value === 'reviewed')?.count ?? 0;
  const candidateCount = facets?.source_statuses.find((item) => item.value === 'candidate')?.count ?? 0;
  const curatedOrigins = facets?.origins.find((item) => item.value === 'sechub-resource')?.count ?? 0;

  return (
    <Stack gap="lg">
      <Paper className="catalogue-hero" withBorder p="xl" radius="lg">
        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="xl">
          <Stack gap="sm">
            <Text className="panel-overline">Catalogue review</Text>
            <Title order={1}>SC4S source catalogue</Title>
            <Text className="readable-panel-text" maw={760}>
              Review SC4S built-ins, SC4S Library entries, and community candidates with explicit provenance, review status, trust boundaries, and capability evidence. Catalogue evidence does not mean local import, apply, or production readiness.
            </Text>
          </Stack>
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
            <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
              <Text className="panel-overline">Catalogue entries</Text>
              <Title order={2}>{totalEntries}</Title>
              <Text size="sm" c="dimmed">Entries matching the current filters.</Text>
            </Paper>
            <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
              <Text className="panel-overline">S6-reviewed entries</Text>
              <Title order={2}>{reviewedCount}</Title>
              <Text size="sm" c="dimmed">Reviewed by S6; still requires local validation before production use.</Text>
            </Paper>
            <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
              <Text className="panel-overline">Unreviewed community candidates</Text>
              <Title order={2}>{candidateCount}</Title>
              <Text size="sm" c="dimmed">Discovery inputs that require maintainer review, local validation, and Splunk evidence before promotion.</Text>
            </Paper>
          </SimpleGrid>
        </SimpleGrid>
      </Paper>

      <Alert color="yellow" title="Community candidate boundary" variant="light">
        Community issue and PR snippets remain discovery inputs only. They are Unreviewed until maintainer review, and still need local validation before production use.
      </Alert>

      <Paper className="catalogue-filter-panel" withBorder p="lg" radius="lg">
        <Stack gap="md">
          <Group justify="space-between" align="end">
            <div>
              <Text className="panel-overline">Search and filters</Text>
              <Text size="sm" c="dimmed">Search first, then filter by origin, review status, recorded file type, or Manager evidence.</Text>
            </div>
            {selectedFilters.length > 0 && (
              <Button variant="light" onClick={() => setFilters(EMPTY_FILTERS)}>
                Clear {selectedFilters.length} filter{selectedFilters.length === 1 ? '' : 's'}
              </Button>
            )}
          </Group>

          <TextInput
            label="Search source catalogue"
            placeholder="Vendor, product, sourcetype, parser, issue candidate..."
            value={filters.q}
            onChange={(event) => setFilters((current) => ({ ...current, q: event.currentTarget.value }))}
          />

          <SimpleGrid cols={{ base: 1, sm: 2, xl: 3 }}>
            <Select
              label="Origin"
              placeholder="Any origin"
              data={facetOptions(facets?.origins)}
              clearable
              value={filters.origin}
              onChange={(origin) => setFilters((current) => ({ ...current, origin }))}
            />
            <Select
              label="Product"
              placeholder="Any product"
              data={facetOptions(facets?.products)}
              searchable
              clearable
              value={filters.product}
              onChange={(product) => setFilters((current) => ({ ...current, product }))}
            />
            <Select
              label="Vendor"
              placeholder="Any vendor"
              data={facetOptions(facets?.vendors)}
              searchable
              clearable
              value={filters.vendor}
              onChange={(vendor) => setFilters((current) => ({ ...current, vendor }))}
            />
            <Select
              label="Review status"
              placeholder="Any review status"
              data={facetOptions(facets?.review_statuses)}
              clearable
              value={filters.review_status}
              onChange={(review_status) => setFilters((current) => ({ ...current, review_status }))}
            />
            <Select
              label="Source review state"
              placeholder="Any source status"
              data={facetOptions(facets?.source_statuses)}
              clearable
              value={filters.source_status}
              onChange={(source_status) => setFilters((current) => ({ ...current, source_status }))}
            />
            <Select
              label="Manager evidence score"
              placeholder="Any evidence score"
              data={[
                { value: '1', label: '1/5 or better' },
                { value: '2', label: '2/5 or better' },
                { value: '3', label: '3/5 or better' },
                { value: '4', label: '4/5 or better' },
                { value: '5', label: '5/5 only' },
              ]}
              clearable
              value={filters.min_quality_score}
              onChange={(min_quality_score) => setFilters((current) => ({ ...current, min_quality_score }))}
            />
            <Select
              label="Recorded file type"
              placeholder="Any file type"
              data={facetOptions(facets?.artifact_types)}
              clearable
              value={filters.artifact_type}
              onChange={(artifact_type) => setFilters((current) => ({ ...current, artifact_type }))}
            />
          </SimpleGrid>

          <Group gap="xl" wrap="wrap">
            <Checkbox
              label="Recorded validation evidence only"
              checked={filters.is_verified}
              onChange={(event) => setFilters((current) => ({ ...current, is_verified: event.currentTarget.checked }))}
            />
            <Checkbox
              label="Has log reduction"
              checked={filters.has_reduction}
              onChange={(event) => setFilters((current) => ({ ...current, has_reduction: event.currentTarget.checked }))}
            />
            <Checkbox
              label="Has Splunk knowledge"
              checked={filters.has_splunk_knowledge}
              onChange={(event) => setFilters((current) => ({ ...current, has_splunk_knowledge: event.currentTarget.checked }))}
            />
          </Group>

          {selectedFilters.length > 0 && (
            <Stack gap="xs">
              <Text className="panel-overline">Active filters</Text>
              <div className="catalogue-chip-row">
                {selectedFilters.map((label) => (
                  <Badge key={label} variant="light" color="cyan">
                    {label}
                  </Badge>
                ))}
              </div>
            </Stack>
          )}
        </Stack>
      </Paper>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
          <Text className="panel-overline">SC4S Library entries</Text>
          <Title order={3}>{curatedOrigins}</Title>
          <Text size="sm" c="dimmed">Catalogue entries from the curated SC4S Library pack source.</Text>
        </Paper>
        <Paper className="catalogue-summary-card" withBorder p="md" radius="lg">
          <Text className="panel-overline">Review status</Text>
          <Title order={3}>{catalogueQuery.data?.entries.length ?? 0} shown</Title>
          <Text size="sm" c="dimmed">Every visible card keeps candidate and validation warnings in view.</Text>
        </Paper>
      </SimpleGrid>

      {catalogueQuery.data?.entries.length === 0 ? (
        <Paper className="catalogue-empty-box" p="xl">
          <Stack gap="sm" align="start">
            <Text className="panel-overline">No catalogue entries match</Text>
            <Title order={3}>Broaden the search</Title>
            <Text c="dimmed">
              Try clearing filters or widening the search. Unreviewed community candidates remain visually separated from reviewed or validated entries so the trust boundary stays obvious.
            </Text>
            <Button variant="light" onClick={() => setFilters(EMPTY_FILTERS)}>Reset filters</Button>
          </Stack>
        </Paper>
      ) : (
        <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }}>
          {catalogueQuery.data?.entries.map((entry) => (
            <CatalogueListCard key={entry.id} entry={entry} />
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
}
