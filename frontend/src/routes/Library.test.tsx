import { MantineProvider } from '@mantine/core';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi, afterEach } from 'vitest';

import { Library, formatSourceLine, importStateLabel } from './Library';

const { sourcesPayload, healthPayload, cataloguePayload, entryPayload, importsPayload, queryErrors } = vi.hoisted(() => ({
  queryErrors: {} as Record<string, Error | undefined>,
  sourcesPayload: {
    sources: [
      {
        source_id: 'embedded',
        enabled: true,
        entry_count: 67,
        snapshot: { source_revision: '839c21b2e8d2739b84eaf2075cad8a7d9ee0710f' },
      },
    ],
  },
  healthPayload: {
    source_id: 'embedded',
    checked_at: '2026-06-14T00:00:00Z',
    overall_ok: true,
    catalogue: { entry_count: 67 },
    manifest: { download_count: 0 },
    sample_entry: { ok: true, id: 'pan_panos' },
    sample_bundle: { ok: true, skipped: true },
    checks: [
      { name: 'snapshot_integrity', ok: true },
    ],
    trust_semantics: {
      remote_labels_are_advisory: true,
      local_verification_requires_local_validation_json: true,
      remote_metadata_can_set_local_is_verified: false,
    },
  },
  cataloguePayload: {
    source_id: 'embedded',
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
    source_id: 'embedded',
    refresh: false,
    eligibility: { download_available: true, runtime_candidate_count: 2 },
    entry: {
      id: 'pan_panos',
      display_name: 'Palo Alto PAN-OS',
      vendor: 'Palo Alto',
      product: 'PAN-OS',
      source_type: 'embedded_library',
    },
  },
  importsPayload: {
    imports: [
      {
        import_id: 'imp_pan_panos_20260601T000000Z',
        source_id: 'embedded',
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
  it('formats the pinned embedded snapshot revision', () => {
    expect(formatSourceLine(sourcesPayload.sources[0])).toContain('839c21b2e8d2739b84eaf2075cad8a7d9ee0710f');
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

  it('renders the embedded check-and-install flow with plain-language labels', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <Library />
      </MantineProvider>,
    );

    expect(markup).toContain('SC4S Library');
    expect(markup).toContain('Check pack');
    expect(markup).toContain('Install to SC4S');
    expect(markup).toContain('SC4S config files to install');
    expect(markup).toContain('Local integrity check');
    expect(markup).toContain('Embedded availability is not local proof');
    expect(markup).toContain('Nothing is installed until you approve it');
    expect(markup).toContain('It does not poll, refresh, or download from a remote source at runtime');
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

    expect(markup).toContain('Could not load Library sources');
    expect(markup).toContain('Manager could not load this operator view. Check the service health and retry.');
    expect(markup).toContain('Could not load SC4S Library packs');
    expect(markup).not.toContain('catalogue schema mismatch');
    expect(markup).toContain('Could not load pack details');
    expect(markup).not.toContain('detail schema mismatch');
    expect(markup).toContain('Could not load checked packs');
    expect(markup).not.toContain('imports schema mismatch');
    expect(markup).not.toContain('No packs checked yet');
  });
});
