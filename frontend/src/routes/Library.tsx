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
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { operatorSafeErrorMessage } from '../lib/displayError';

import {
  applyLibraryImport,
  downloadLibraryBundle,
  getLibrarySourceHealth,
  getLibraryEntry,
  listLibraryCatalogue,
  listLibraryImports,
  listLibrarySources,
  syncLibrarySource,
  validateLibraryImport,
  type LibraryCatalogueEntry,
  type LibraryImportRecord,
} from '../api/library';

function formatSourceLine(source: Record<string, unknown>) {
  const sourceId = String(source.source_id || 'unknown');
  const primary = String(source.catalogue_url || '');
  return `${sourceId} → ${primary}`;
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
  const [sourceId, setSourceId] = useState('official');
  const [search, setSearch] = useState('');
  const [downloadableOnly, setDownloadableOnly] = useState(true);
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const sourcesQuery = useQuery({
    queryKey: ['library', 'sources'],
    queryFn: ({ signal }) => listLibrarySources(signal),
  });

  const healthQuery = useQuery({
    queryKey: ['library', 'source-health', sourceId || 'official'],
    queryFn: ({ signal }) => getLibrarySourceHealth(sourceId || 'official', signal),
  });

  useEffect(() => {
    const firstSource = sourcesQuery.data?.sources?.[0]?.source_id;
    if (firstSource && !sourceId) {
      setSourceId(firstSource);
    }
  }, [sourceId, sourcesQuery.data]);

  const catalogueParams = useMemo(() => {
    const next: Record<string, string> = { source_id: sourceId || 'official' };
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
    queryFn: ({ signal }) => getLibraryEntry(sourceId || 'official', selectedEntryId || '', false, signal),
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

  return (
    <Stack gap="lg">
      <div>
        <Title order={1}>SecHub packs</Title>
        <Text c="dimmed">Browse packs from SecHub and install them into your SC4S instance. Nothing changes on your instance until you explicitly install a pack.</Text>
      </div>

      <Alert color="cyan" title="Nothing is installed until you approve it" variant="light">
        Downloaded packs are stored locally but not active. Only after you check a pack and click <strong>Install to SC4S</strong> do any config files change on your instance. Only SC4S config files are installed — Splunk apps, scripts, docs, and test events are kept as reference only.
      </Alert>

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Group justify="space-between" align="start">
            <div>
              <Text className="panel-overline">SecHub connection</Text>
              <Title order={3}>Connection checks</Title>
              <Text size="sm" c="dimmed">Verifies that Manager can reach SecHub, browse the pack list, and download a test bundle.</Text>
            </div>
            <Badge color={healthQuery.data?.overall_ok ? 'green' : healthQuery.isError ? 'red' : 'gray'} variant="light">
              {healthQuery.data?.overall_ok ? 'SecHub reachable' : healthQuery.isError ? 'Connection failed' : 'Checking'}
            </Badge>
          </Group>
          <Alert color="yellow" title="SecHub review labels are a starting point, not proof" variant="light">
            SecHub review labels tell you what S6 has checked. Your own SC4S and Splunk validation still decides whether a pack is safe to run in your environment.
          </Alert>
          {healthQuery.isLoading ? <Loader size="sm" /> : null}
          {healthQuery.isError ? <Alert color="red" title="Could not reach SecHub">{operatorSafeErrorMessage(healthQuery.error, 'Could not reach SecHub. Check your network connection and try again.')}</Alert> : null}
          {healthQuery.data ? (
            <Stack gap="xs">
              <Text size="sm" c="dimmed">Packs available: {healthQuery.data.catalogue.entry_count} · downloadable bundles: {healthQuery.data.manifest.download_count} · last checked: {healthQuery.data.checked_at}</Text>
              {healthQuery.data.checks.map((check) => (
                <Paper key={check.name} withBorder p="sm" radius="md">
                  <Group justify="space-between" align="start">
                    <div>
                      <Text fw={600}>{check.name}</Text>
                      <Text size="xs" c="dimmed">{check.url || 'no URL recorded'}</Text>
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
              <Text className="panel-overline">Pack source</Text>
              <Title order={3}>SecHub (sechub.s6ops.com)</Title>
              <Text size="sm" c="dimmed">Packs are fetched from SecHub. Refresh to pull the latest list.</Text>
            </div>
            <Button
              loading={busyKey === 'sync'}
              onClick={() => runAction('sync', () => syncLibrarySource(sourceId || 'official'), 'Pack list refreshed from SecHub.')}
              variant="light"
            >
              Refresh pack list
            </Button>
          </Group>
          {sourcesQuery.isLoading ? <Loader size="sm" /> : null}
          {sourcesQuery.isError ? <Alert color="red" title="Could not load SecHub sources">{operatorSafeErrorMessage(sourcesQuery.error)}</Alert> : null}
          {sourcesQuery.data?.sources?.map((source) => (
            <Paper key={source.source_id} withBorder p="md" radius="md">
              <Stack gap={4}>
                <Group justify="space-between">
                  <Text fw={600}>{formatSourceLine(source)}</Text>
                  <Badge color={source.enabled ? 'green' : 'red'} variant="light">{source.enabled ? 'Enabled' : 'Disabled'}</Badge>
                </Group>
                <Text size="sm" c="dimmed">Last refreshed: {source.last_sync || 'never'} · packs cached: {source.entry_count ?? 0} · downloadable bundles: {source.manifest_download_count ?? 0}</Text>
              </Stack>
            </Paper>
          ))}
        </Stack>
      </Card>

      <Group align="start" grow>
        <Card withBorder padding="lg">
          <Stack gap="md">
            <div>
              <Text className="panel-overline">Available packs</Text>
              <Title order={3}>Packs from SecHub</Title>
            </div>
            <TextInput label="Search packs" placeholder="pan, fortinet, commvault" value={search} onChange={(event) => setSearch(event.currentTarget.value)} />
            <Checkbox label="Show downloadable packs only" checked={downloadableOnly} onChange={(event) => setDownloadableOnly(event.currentTarget.checked)} />
            {catalogueQuery.isLoading ? <Loader size="sm" /> : null}
            {catalogueQuery.isError ? <Alert color="red" title="Could not load pack list from SecHub">{operatorSafeErrorMessage(catalogueQuery.error)}</Alert> : null}
            {catalogueQuery.data?.entries?.map((entry: LibraryCatalogueEntry) => (
              <Paper key={entry.id} withBorder p="md" radius="md">
                <Stack gap="sm">
                  <Group justify="space-between" align="start">
                    <div>
                      <Text fw={700}>{entry.display_name || entry.id}</Text>
                      <Text size="sm" c="dimmed">{entry.vendor || 'Unknown vendor'} / {entry.product || 'Unknown product'} · version {entry.version || 'unknown'}</Text>
                    </div>
                    <Badge color={entry.download_available ? 'green' : 'gray'} variant="light">{entry.download_available ? 'Download available' : 'No download yet'}</Badge>
                  </Group>
                  <Group>
                    <Button variant={selectedEntryId === entry.id ? 'filled' : 'light'} onClick={() => setSelectedEntryId(entry.id)}>View details</Button>
                    <Button
                      variant="default"
                      loading={busyKey === `download:${entry.id}`}
                      onClick={() => runAction(`download:${entry.id}`, () => downloadLibraryBundle(sourceId || 'official', entry.id), `Pack downloaded. Click "Check pack" to validate it before installing.`)}
                    >
                      Download
                    </Button>
                    <Button
                      color="cyan"
                      loading={busyKey === `validate:${entry.id}`}
                      onClick={() => runAction(`validate:${entry.id}`, () => validateLibraryImport(sourceId || 'official', entry.id), `Pack checked. Review the results below and click "Install to SC4S" if everything looks good.`)}
                    >
                      Check pack
                    </Button>
                  </Group>
                </Stack>
              </Paper>
            ))}
          </Stack>
        </Card>

        <Card withBorder padding="lg">
          <Stack gap="md">
            <div>
              <Text className="panel-overline">Pack details</Text>
              <Title order={3}>{selectedEntry ? String(selectedEntry.display_name || selectedEntry.id || selectedEntryId) : 'Select a pack'}</Title>
            </div>
            {detailQuery.isLoading ? <Loader size="sm" /> : null}
            {detailQuery.isError ? <Alert color="red" title="Could not load pack details">{operatorSafeErrorMessage(detailQuery.error)}</Alert> : null}
            {!selectedEntry && !detailQuery.isLoading && !detailQuery.isError ? (
              <Text c="dimmed">Select a pack from the list to see what is included and whether it can be installed.</Text>
            ) : null}
            {selectedEntry && selectedEligibility ? (
              <Stack gap="sm">
                <Group>
                  <Badge color={selectedEligibility.download_available ? 'green' : 'gray'} variant="light">{selectedEligibility.download_available ? 'Download available' : 'Not downloadable'}</Badge>
                  <Badge color={selectedEligibility.runtime_candidate_count > 0 ? 'cyan' : 'gray'} variant="light">
                    {selectedEligibility.runtime_candidate_count} SC4S config file{selectedEligibility.runtime_candidate_count === 1 ? '' : 's'} to install
                  </Badge>
                </Group>
                <Text size="sm" c="dimmed">Only SC4S config files are installed. Splunk apps, scripts, docs, and test events are downloaded for reference but not applied automatically.</Text>
              </Stack>
            ) : null}
          </Stack>
        </Card>
      </Group>

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
                      onClick={() => runAction(`apply:${item.import_id}`, () => applyLibraryImport(item.import_id, true), `SC4S config files installed. Reload SC4S and verify with Splunk readback.`)}
                    >
                      Install to SC4S
                    </Button>
                  </Group>
                </Stack>
              </Paper>
            ))
          ) : !importsQuery.isLoading && !importsQuery.isError ? (
            <Text c="dimmed">No packs checked yet. Download a pack above and click "Check pack" first.</Text>
          ) : null}
        </Stack>
      </Card>
    </Stack>
  );
}

export { formatSourceLine, importStateLabel };
