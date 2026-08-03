import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Code,
  Group,
  Loader,
  Pagination,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

const LIBRARY_PAGE_SIZE = 10;
import { operatorSafeErrorMessage } from '../lib/displayError';

import {
  applyLibraryImport,
  getLibrarySourceHealth,
  getLibraryEntry,
  listLibraryCatalogue,
  listLibraryImports,
  listLibrarySources,
  validateLibraryImport,
  type LibraryCatalogueEntry,
  type LibraryImportRecord,
} from '../api/library';

function formatSourceLine(source: Record<string, unknown>) {
  const snapshot = source.snapshot as Record<string, unknown> | undefined;
  return `Embedded snapshot · ${String(snapshot?.source_revision || 'revision unavailable')}`;
}

function importStateLabel(item: LibraryImportRecord) {
  if (item.reference_only) return 'Reference files only';
  if (item.apply_allowed) return 'Ready to install';
  return 'Check required';
}

function importStateTone(item: LibraryImportRecord) {
  if (item.reference_only) return 'gray';
  if (item.apply_allowed) return 'cyan';
  return 'yellow';
}

export function Library() {
  const queryClient = useQueryClient();
  const [sourceId] = useState('embedded');
  const [search, setSearch] = useState('');
  const [downloadableOnly, setDownloadableOnly] = useState(true);
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);
  const [libPage, setLibPage] = useState(1);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const sourcesQuery = useQuery({
    queryKey: ['library', 'sources'],
    queryFn: ({ signal }) => listLibrarySources(signal),
  });

  const healthQuery = useQuery({
    queryKey: ['library', 'source-health', sourceId],
    queryFn: ({ signal }) => getLibrarySourceHealth(sourceId, signal),
  });

  useEffect(() => { setLibPage(1); }, [search, downloadableOnly, sourceId]);

  const catalogueParams = useMemo(() => {
    const next: Record<string, string> = { source_id: sourceId };
    if (downloadableOnly) next.downloadable_only = 'yes';
    if (search.trim()) next.search = search.trim();
    return next;
  }, [downloadableOnly, search, sourceId]);

  const catalogueQuery = useQuery({
    queryKey: ['library', 'catalogue', catalogueParams],
    queryFn: ({ signal }) => listLibraryCatalogue(catalogueParams, signal),
  });

  useEffect(() => {
    const firstEntry = catalogueQuery.data?.entries?.[0]?.id;
    if (!selectedEntryId && firstEntry) {
      setSelectedEntryId(firstEntry);
    }
  }, [catalogueQuery.data, selectedEntryId]);

  const detailQuery = useQuery({
    queryKey: ['library', 'entry', sourceId, selectedEntryId],
    queryFn: ({ signal }) => getLibraryEntry(sourceId, selectedEntryId || '', signal),
    enabled: Boolean(selectedEntryId),
  });

  const importsQuery = useQuery({
    queryKey: ['library', 'imports'],
    queryFn: ({ signal }) => listLibraryImports(signal),
  });

  async function runAction(key: string, action: () => Promise<unknown>, success: string) {
    setBusyKey(key);
    setActionError(null);
    setActionMessage(null);
    try {
      await action();
      setActionMessage(success);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['library', 'sources'] }),
        queryClient.invalidateQueries({ queryKey: ['library', 'catalogue'] }),
        queryClient.invalidateQueries({ queryKey: ['library', 'entry'] }),
        queryClient.invalidateQueries({ queryKey: ['library', 'imports'] }),
      ]);
    } catch (error) {
      setActionError(operatorSafeErrorMessage(error, 'Manager could not complete that action. Check the entered values and retry.'));
    } finally {
      setBusyKey(null);
    }
  }

  const selectedEntry = detailQuery.data?.entry || null;
  const selectedEligibility = detailQuery.data?.eligibility || null;

  const allEntries = catalogueQuery.data?.entries ?? [];
  const libTotalPages = Math.ceil(allEntries.length / LIBRARY_PAGE_SIZE);
  const pagedEntries = allEntries.slice((libPage - 1) * LIBRARY_PAGE_SIZE, libPage * LIBRARY_PAGE_SIZE);

  return (
    <Stack gap="lg">
      <div>
        <Title order={1}>SC4S Library</Title>
        <Text c="dimmed">Browse the embedded offline Library snapshot and stage SC4S configuration for local validation. Splunk knowledge remains reference-only.</Text>
      </div>

      <Alert color="cyan" title="Nothing is installed until you approve it" variant="light">
        Embedded packs are staged locally but not active. Only after you check a pack and click <strong>Install to SC4S</strong> do any config files change on your instance. Only SC4S config files are installed — Splunk knowledge, scripts, docs, and test events are kept as reference only.
      </Alert>
      {detailQuery.isError ? <Alert color="red" title="Could not load pack details">{operatorSafeErrorMessage(detailQuery.error)}</Alert> : null}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between" align="start">
            <div>
              <Text className="panel-overline">Snapshot integrity</Text>
              <Title order={3}>Local integrity check</Title>
              <Text size="sm" c="dimmed">Verifies the committed snapshot metadata and local pack manifests. No network request is made.</Text>
            </div>
            <Badge color={healthQuery.data?.overall_ok ? 'green' : healthQuery.isError ? 'red' : 'gray'} variant="light">
              {healthQuery.data?.overall_ok ? 'Snapshot valid' : healthQuery.isError ? 'Snapshot invalid' : 'Checking'}
            </Badge>
          </Group>
          <Alert color="yellow" title="Embedded availability is not local proof" variant="light">
            This pinned source material is available offline. Your own SC4S and Splunk validation still decides whether a pack is safe to run in your environment.
          </Alert>
          {healthQuery.isLoading ? <Loader size="sm" /> : null}
          {healthQuery.isError ? <Alert color="red" title="Embedded snapshot is invalid">{operatorSafeErrorMessage(healthQuery.error, 'The embedded snapshot could not be validated. Do not stage packs until it is repaired.')}</Alert> : null}
          {healthQuery.data ? (
            <Stack gap="xs">
              <Text size="sm" c="dimmed">{healthQuery.data.catalogue.entry_count} packs available locally · checked: {healthQuery.data.checked_at}</Text>
              {healthQuery.data.checks.map((check) => (
                <Paper key={check.name} withBorder p="sm" radius="md">
                  <Group justify="space-between" align="start">
                    <div>
                      <Text fw={600}>{check.name.replace(/_/g, ' ')}</Text>
                      {!check.ok ? <Text size="sm">{check.message || 'check failed'} {check.next_action ? `What to do: ${check.next_action}` : ''}</Text> : null}
                    </div>
                    <Badge color={check.ok ? 'green' : 'red'} variant="light">{check.ok ? 'OK' : check.error_code || 'failed'}</Badge>
                  </Group>
                </Paper>
              ))}
            </Stack>
          ) : null}
        </Stack>
      </Card>

      {actionMessage && <Alert color="green" title="Done">{actionMessage}</Alert>}
      {actionError && <Alert color="red" title="Something went wrong">{actionError}</Alert>}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between" align="start">
            <div>
              <Text className="panel-overline">Pack provenance</Text>
              <Title order={3}>Embedded immutable snapshot</Title>
              <Text size="sm" c="dimmed">This Library is shipped with Manager. It does not poll, refresh, or download from a remote source at runtime.</Text>
            </div>
          </Group>
          {sourcesQuery.isLoading ? <Loader size="sm" /> : null}
          {sourcesQuery.isError ? <Alert color="red" title="Could not load Library sources">{operatorSafeErrorMessage(sourcesQuery.error)}</Alert> : null}
          {sourcesQuery.data?.sources?.map((source) => (
            <Paper key={source.source_id} withBorder p="md" radius="md">
              <Stack gap={4}>
                <Group justify="space-between">
                  <Text fw={600}>{formatSourceLine(source)}</Text>
                  <Badge color={source.enabled ? 'green' : 'red'} variant="light">{source.enabled ? 'Enabled' : 'Disabled'}</Badge>
                </Group>
                <Text size="sm" c="dimmed">{source.entry_count ?? 0} packs available locally</Text>
              </Stack>
            </Paper>
          ))}
        </Stack>
      </Card>

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <div>
              <Text className="panel-overline">Available packs</Text>
              <Title order={3}>SC4S Library packs</Title>
            </div>
            <Checkbox label="Downloadable only" checked={downloadableOnly} onChange={(event) => setDownloadableOnly(event.currentTarget.checked)} />
          </Group>
          <TextInput placeholder="Search packs — pan, fortinet, commvault…" value={search} onChange={(event) => setSearch(event.currentTarget.value)} />
          {catalogueQuery.isLoading ? <Loader size="sm" /> : null}
          {catalogueQuery.isError ? <Alert color="red" title="Could not load SC4S Library packs">{operatorSafeErrorMessage(catalogueQuery.error)}</Alert> : null}
          {allEntries.length > 0 && (
            <Group justify="space-between" align="center">
              <Text size="xs" c="dimmed">
                {((libPage - 1) * LIBRARY_PAGE_SIZE) + 1}–{Math.min(libPage * LIBRARY_PAGE_SIZE, allEntries.length)} of {allEntries.length} packs
              </Text>
              {libTotalPages > 1 && <Pagination total={libTotalPages} value={libPage} onChange={setLibPage} size="xs" />}
            </Group>
          )}
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
            {pagedEntries.map((entry: LibraryCatalogueEntry) => (
              <Paper key={entry.id} withBorder p="md" radius="md" style={{ display: 'flex', flexDirection: 'column' }}>
                <Stack gap="sm" style={{ flex: 1 }}>
                  <Group justify="space-between" align="start" wrap="nowrap">
                    <Text fw={700} size="sm">{entry.display_name || entry.id}</Text>
                    <Badge size="xs" color={entry.download_available ? 'green' : 'gray'} variant="light" style={{ whiteSpace: 'nowrap' }}>
                      {entry.download_available ? 'Available' : 'Not yet'}
                    </Badge>
                  </Group>
                  {entry.version && <Text size="xs" c="dimmed">Version {entry.version}</Text>}
                  <Group gap="xs" mt="auto" pt="xs">
                    <Button size="xs" variant={selectedEntryId === entry.id ? 'filled' : 'light'} onClick={() => setSelectedEntryId(selectedEntryId === entry.id ? null : entry.id)}>
                      {selectedEntryId === entry.id ? 'Hide details' : 'View details'}
                    </Button>
                    <Button
                      size="xs"
                      color="cyan"
                      disabled={!entry.download_available}
                      loading={busyKey === `validate:${entry.id}`}
                      onClick={() => runAction(`validate:${entry.id}`, () => validateLibraryImport(sourceId, entry.id), `Pack checked locally. Review the results below and click "Install to SC4S" if everything looks good.`)}
                    >
                      Check pack
                    </Button>
                  </Group>
                </Stack>
              </Paper>
            ))}
          </SimpleGrid>
          {libTotalPages > 1 && (
            <Group justify="center">
              <Pagination total={libTotalPages} value={libPage} onChange={setLibPage} size="sm" />
            </Group>
          )}
        </Stack>
      </Card>

      {selectedEntryId && (
        <Card withBorder padding="lg">
          <Stack gap="md">
            <Group justify="space-between" align="start">
              <div>
                <Text className="panel-overline">Pack details</Text>
                <Title order={3}>{selectedEntry ? String(selectedEntry.display_name || selectedEntry.id || selectedEntryId) : selectedEntryId}</Title>
              </div>
              <Button size="xs" variant="subtle" color="gray" onClick={() => setSelectedEntryId(null)}>Close</Button>
            </Group>
            {detailQuery.isLoading ? <Loader size="sm" /> : null}
            {detailQuery.isError ? <Alert color="red" title="Could not load pack details">{operatorSafeErrorMessage(detailQuery.error)}</Alert> : null}
            {selectedEntry && selectedEligibility ? (
              <Stack gap="sm">
                <Group>
                  <Badge color={selectedEligibility.download_available ? 'green' : 'gray'} variant="light">{selectedEligibility.download_available ? 'Embedded locally' : 'Unavailable'}</Badge>
                  <Badge color={selectedEligibility.runtime_candidate_count > 0 ? 'cyan' : 'gray'} variant="light">
                    {selectedEligibility.runtime_candidate_count} SC4S config file{selectedEligibility.runtime_candidate_count === 1 ? '' : 's'} to install
                  </Badge>
                </Group>
                <Text size="sm" c="dimmed">Only SC4S config files are installed. Splunk knowledge, scripts, docs, and test events are staged locally for reference but not applied automatically.</Text>
              </Stack>
            ) : null}
          </Stack>
        </Card>
      )}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between" align="start">
            <div>
              <Text className="panel-overline">Checked packs</Text>
              <Title order={3}>Packs ready to install</Title>
            </div>
            <Badge variant="light" color="violet">Not installed yet</Badge>
          </Group>
          {importsQuery.isLoading ? <Loader size="sm" /> : null}
          {importsQuery.isError ? <Alert color="red" title="Could not load checked packs">{operatorSafeErrorMessage(importsQuery.error)}</Alert> : null}
          {importsQuery.data?.imports?.length && !importsQuery.isError ? (
            importsQuery.data.imports.map((item) => (
              <Paper key={item.import_id} withBorder p="md" radius="md">
                <Stack gap="sm">
                  <Group justify="space-between" align="start">
                    <div>
                      <Text fw={700}>{item.entry_id}</Text>
                      <Text size="sm" c="dimmed">Checked: {item.created_at || 'unknown'} · ID: <Code>{item.import_id}</Code></Text>
                    </div>
                    <Badge color={importStateTone(item)} variant="light">{importStateLabel(item)}</Badge>
                  </Group>
                  <Text size="sm" c="dimmed">
                    SC4S config files to install: {item.runtime_files?.length || 0} · Reference files: {item.reference_files?.length || 0}
                  </Text>
                  <Group>
                    <Button
                      color="cyan"
                      disabled={!item.apply_allowed}
                      loading={busyKey === `apply:${item.import_id}`}
                      onClick={() => runAction(`apply:${item.import_id}`, () => applyLibraryImport(item.import_id, true), `SC4S config files installed. Reload SC4S and check Splunk for incoming events to confirm.`)}
                    >
                      Install to SC4S
                    </Button>
                  </Group>
                </Stack>
              </Paper>
            ))
          ) : !importsQuery.isLoading && !importsQuery.isError ? (
            <Text c="dimmed">No packs checked yet. Select an embedded pack above and click "Check pack" first.</Text>
          ) : null}
        </Stack>
      </Card>
    </Stack>
  );
}

export { formatSourceLine, importStateLabel };
