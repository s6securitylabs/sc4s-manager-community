import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Loader,
  Pagination,
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
import { useEffect, useMemo, useState } from 'react';

const CATALOGUE_PAGE_SIZE = 30;

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
  validated: 'Validated by S6',
  draft: 'Draft',
  deprecated: 'Deprecated',
};

export type CatalogueFilters = {
  q: string;
  origin: string | null;
  product: string | null;
  vendor: string | null;
  review_status?: string | null;
  min_quality_score: string | null;
  source_status: string | null;
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
  source_status: null,
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
    filters.source_status ? `Status: ${sourceStatusLabel(filters.source_status)}` : null,
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

export function buildCatalogueParams(filters: CatalogueFilters, page = 1) {
  const next: Record<string, string> = {
    limit: String(CATALOGUE_PAGE_SIZE),
    offset: String((page - 1) * CATALOGUE_PAGE_SIZE),
  };
  if (filters.q.trim()) next.q = filters.q.trim();
  if (filters.origin) next.origin = filters.origin;
  if (filters.product) next.product = filters.product;
  if (filters.vendor) next.vendor = filters.vendor;
  if (filters.review_status) next.review_status = filters.review_status;
  if (filters.min_quality_score) next.min_quality_score = filters.min_quality_score;
  if (filters.source_status) next.source_status = filters.source_status;
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
        ) : null}

        <Stack gap="xs" mt="auto">
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
              No capabilities recorded yet.
            </Text>
          )}
        </Stack>

        <Group justify="space-between" align="center" mt="xs">
          <Text size="sm" c="dimmed">Check the details before downloading.</Text>
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
  const [page, setPage] = useState(1);

  useEffect(() => { setPage(1); }, [filters]);

  const params = useMemo(() => buildCatalogueParams(filters, page), [filters, page]);

  const catalogueQuery = useQuery({
    queryKey: ['catalogue', params],
    queryFn: ({ signal }) => listCatalogue(params, signal),
    placeholderData: (prev) => prev,
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
  const totalPages = Math.ceil(totalEntries / CATALOGUE_PAGE_SIZE);
  const reviewedCount = facets?.review_statuses?.find((item) => item.value === 'reviewed')?.count ?? 0;

  return (
    <Stack gap="lg">
      <Paper className="catalogue-hero" withBorder p="xl" radius="lg">
        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="xl">
          <Stack gap="sm">
            <Text className="panel-overline">Catalogue review</Text>
            <Title order={1}>SC4S source catalogue</Title>
            <Text className="readable-panel-text" maw={760}>
              Browse SC4S source types. Find the parser for your device, check what's included, and download it.
            </Text>
          </Stack>
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
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
          </SimpleGrid>
        </SimpleGrid>
      </Paper>

      <Alert color="yellow" title="Community sources — not yet reviewed" variant="light">
        Community sources appear in this catalogue but have not been reviewed by S6. They require local validation before use in production.
      </Alert>

      <Paper className="catalogue-filter-panel" withBorder p="lg" radius="lg">
        <Stack gap="md">
          <Group justify="space-between" align="end">
            <div>
              <Text className="panel-overline">Search and filters</Text>
              <Text size="sm" c="dimmed">Search by vendor, product, or device type. Filter by origin or review status.</Text>
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
          </SimpleGrid>

          <Group gap="xl" wrap="wrap">
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
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Text size="sm" c="dimmed">
              Showing {((page - 1) * CATALOGUE_PAGE_SIZE) + 1}–{Math.min(page * CATALOGUE_PAGE_SIZE, totalEntries)} of {totalEntries} entries
            </Text>
            {totalPages > 1 && (
              <Pagination total={totalPages} value={page} onChange={setPage} size="sm" />
            )}
          </Group>
          <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }}>
            {catalogueQuery.data?.entries.map((entry) => (
              <CatalogueListCard key={entry.id} entry={entry} />
            ))}
          </SimpleGrid>
          {totalPages > 1 && (
            <Group justify="center">
              <Pagination total={totalPages} value={page} onChange={setPage} />
            </Group>
          )}
        </Stack>
      )}
    </Stack>
  );
}
