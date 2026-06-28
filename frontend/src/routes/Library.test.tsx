import { MantineProvider } from '@mantine/core';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi, afterEach } from 'vitest';

import { Library, formatSourceLine, importStateLabel } from './Library';

const { sourcesPayload, healthPayload, cataloguePayload, entryPayload, importsPayload, queryErrors } = vi.hoisted(() => ({
  queryErrors: {} as Record<string, Error | undefined>,
  sourcesPayload: {
    sources: [
      {
        source_id: 'official',
        enabled: true,
        catalogue_url: 'https://sechub.s6ops.com/data/catalogue.json',
        last_sync: '2026-06-01T00:00:00Z',
        entry_count: 396,
        manifest_download_count: 2,
      },
    ],
  },
  healthPayload: {
    source_id: 'official',
    checked_at: '2026-06-14T00:00:00Z',
    overall_ok: false,
    catalogue: { entry_count: 396 },
    manifest: { download_count: 2 },
    sample_entry: { ok: true, id: 'pan_panos' },
    sample_bundle: { name: 'sample_bundle', ok: false, error_code: 'checksum_mismatch', message: 'downloaded bundle sha256 does not match entry detail', next_action: 'Do not apply the bundle.' },
    checks: [
      { name: 'catalogue', url: 'https://sechub.s6ops.com/data/catalogue.json', ok: true },
      { name: 'manifest', url: 'https://sechub.s6ops.com/downloads/manifest.json', ok: true },
      { name: 'sample_entry', url: 'https://sechub.s6ops.com/data/entries/pan_panos.json', ok: true },
      { name: 'sample_bundle', url: 'https://sechub.s6ops.com/downloads/pan_panos.zip', ok: false, error_code: 'checksum_mismatch', message: 'downloaded bundle sha256 does not match entry detail', next_action: 'Do not apply the bundle.' },
    ],
    trust_semantics: {
      remote_labels_are_advisory: true,
      local_verification_requires_local_validation_json: true,
      remote_metadata_can_set_local_is_verified: false,
    },
  },
  cataloguePayload: {
    source_id: 'official',
    filters: { downloadable_only: 'yes' },
    entries: [
      {
        id: 'pan_panos',
        display_name: 'Palo Alto PAN-OS',
        vendor: 'Palo Alto',
        product: 'PAN-OS',
        version: '1.2.3',
        download_available: true,
      },
    ],
  },
  entryPayload: {
    source_id: 'official',
    refresh: false,
    eligibility: { download_available: true, runtime_candidate_count: 2 },
    entry: {
      id: 'pan_panos',
      display_name: 'Palo Alto PAN-OS',
      vendor: 'Palo Alto',
      product: 'PAN-OS',
      download: { filename: 'pan_panos-1.2.3.zip' },
    },
  },
  importsPayload: {
    imports: [
      {
        import_id: 'imp_pan_panos_20260601T000000Z',
        source_id: 'official',
        entry_id: 'pan_panos',
        created_at: '2026-06-01T00:00:00Z',
        apply_allowed: true,
        reference_only: false,
        runtime_files: [{ source_path: 'local/config/app_parsers/panos.conf', target_path: 'local/config/app_parsers/panos.conf' }],
        reference_files: [{ source_path: 'README.md', target_path: 'README.md' }],
      },
    ],
  },
}));

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ invalidateQueries: vi.fn(async () => undefined) }),
  useQuery: ({ queryKey }: { queryKey: unknown[] }) => {
    const joined = queryKey.join(':');
    const failure = queryErrors[joined] || (joined.startsWith('library:catalogue') ? queryErrors['library:catalogue'] : undefined) || (joined.startsWith('library:entry') ? queryErrors['library:entry'] : undefined);
    if (failure) return { isLoading: false, isError: true, error: failure, data: undefined };
    if (joined === 'library:sources') {
      return { isLoading: false, data: sourcesPayload };
    }
    if (joined.startsWith('library:source-health')) {
      return { isLoading: false, data: healthPayload };
    }
    if (joined.startsWith('library:catalogue')) {
      return { isLoading: false, data: cataloguePayload };
    }
    if (joined.startsWith('library:entry')) {
      return { isLoading: false, data: entryPayload };
    }
    if (joined === 'library:imports') {
      return { isLoading: false, data: importsPayload };
    }
    return { isLoading: false, data: undefined };
  },
}));

describe('library helpers', () => {
  it('formats official source with the canonical SecHub catalogue URL', () => {
    expect(formatSourceLine(sourcesPayload.sources[0])).toContain('sechub.s6ops.com');
  });

  it('labels import states in plain language', () => {
    expect(importStateLabel(importsPayload.imports[0])).toBe('Ready to install');
    expect(importStateLabel({ ...importsPayload.imports[0], reference_only: true, apply_allowed: false })).toBe('Reference files only');
    expect(importStateLabel({ ...importsPayload.imports[0], reference_only: false, apply_allowed: false })).toBe('Check required');
  });
});

describe('Library route', () => {
  afterEach(() => {
    for (const key of Object.keys(queryErrors)) delete queryErrors[key];
  });

  it('renders the browse-download-check-install flow with plain-language labels', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <Library />
      </MantineProvider>,
    );

    expect(markup).toContain('SecHub packs');
    expect(markup).toContain('Download');
    expect(markup).toContain('Check pack');
    expect(markup).toContain('Install to SC4S');
    expect(markup).toContain('SC4S config files to install');
    expect(markup).toContain('Connection checks');
    expect(markup).toContain('SecHub review labels are a starting point, not proof');
    expect(markup).toContain('Nothing is installed until you approve it');
    expect(markup).toContain('checksum_mismatch');
    expect(markup).toContain('Do not apply the bundle');
  });

  it('surfaces source, catalogue, detail, and import query failures instead of trusted empty states', () => {
    queryErrors['library:sources'] = new Error('sources schema mismatch');
    queryErrors['library:catalogue'] = new Error('catalogue schema mismatch');
    queryErrors['library:entry'] = new Error('detail schema mismatch');
    queryErrors['library:imports'] = new Error('imports schema mismatch');

    const markup = renderToStaticMarkup(
      <MantineProvider>
        <Library />
      </MantineProvider>,
    );

    expect(markup).toContain('Could not load SecHub sources');
    expect(markup).toContain('Manager could not load this operator view. Check the service health and retry.');
    expect(markup).toContain('Could not load pack list from SecHub');
    expect(markup).not.toContain('catalogue schema mismatch');
    expect(markup).toContain('Could not load pack details');
    expect(markup).not.toContain('detail schema mismatch');
    expect(markup).toContain('Could not load checked packs');
    expect(markup).not.toContain('imports schema mismatch');
    expect(markup).not.toContain('No packs checked yet');
  });
});
