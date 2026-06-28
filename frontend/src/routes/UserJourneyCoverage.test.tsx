import { MantineProvider } from '@mantine/core';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

const { packsPayload, cataloguePayload, librarySourcesPayload, libraryImportsPayload, packDetailPayload, runtimeStatePayload, queryErrors } = vi.hoisted(() => ({
  queryErrors: {} as Record<string, Error | undefined>,
  packsPayload: {
    count: 2,
    packs: [
      {
        id: 'commvault_commcell',
        schema_version: '0.1',
        version: '1.0.0',
        url: 'https://example.test/commvault',
        description: 'Commvault pack with test events and exports.',
        display_name: 'Commvault CommCell',
        vendor: 'Commvault',
        product: 'CommCell',
        default_index: 'commvault',
        default_source: 'commvault_commcell',
        listener: { source_id: 'commvault_commcell', transport: 'tls', port: 20029, env: {} },
        sourcetypes: { audit: 'commvault:commcell:audittrail' },
        event_families: [
          {
            id: 'audit',
            label: 'AuditTrail',
            match_engine: 'pcre',
            match: '^AuditTrail:',
            expected_sourcetype: 'commvault:commcell:audittrail',
            primary_id_field: 'Opid',
            required_fields: ['Opid'],
            timestamp_fields: ['Utctimestamp'],
          },
        ],
        artifacts: {},
        supported_transports: [
          {
            id: 'tls-6514',
            label: 'TLS 6514',
            transport: 'tls',
            syslog_protocol: 'rfc5425',
            framing: 'octet_counted',
            envelope: 'ietf_rfc5424',
            payload_format: 'custom_application',
            recommended: true,
            default_port: 6514,
          },
        ],
        recommended_transport: 'tls-6514',
        source_log_version: { name: 'Commvault', min: null, max: null, notes: null },
        validation: { date_validated: null, validated_by: null, source_log_version: null, sc4s_version: null, splunk_version: null, evidence: null },
        test_event_sets: [
          {
            id: 'audit',
            path: 'test-events/commvault.txt',
            format: 'raw',
            wire_format: 'raw',
            event_count: 1,
            events_per_file: 'single',
            event_boundary: 'line',
            record_separator: '\n',
            one_event_per_line: true,
            multiline: false,
            unique_events: true,
            marker_tokens: ['marker'],
            timestamp_policy: {
              source_time_mode: 'field_with_timezone',
              primary_field: 'Utctimestamp',
              primary_timezone: 'UTC',
              fallback_time_mode: 'receiver_time',
              fallback_timezone: 'UTC',
              requires_source_timezone_when_fields_missing: false,
            },
            field_delimiting: null,
            expected_families: ['audit'],
          },
        ],
        export_artifacts: [
          {
            id: 'sc4s_parser',
            group: 'sc4s',
            source_path: 'sc4s/app_parsers/syslog/app-commvault_commcell.conf',
            target_path: 'local/config/app_parsers/syslog/app-commvault_commcell.conf',
            kind: 'syslog_ng_parser',
            rendered: false,
            contains_secrets: false,
            required: true,
          },
        ],
      },
    ],
  },
  cataloguePayload: {
    count: 396,
    limit: 60,
    offset: 0,
    entries: [
      {
        id: 'a10',
        display_name: 'a10 a10',
        vendor: 'a10',
        product: 'a10',
        origins: ['sc4s-inbuilt'],
        effective_origin: 'sc4s-inbuilt',
        relationship_to_upstream: 'upstream_only',
        trust_level: 'unverified',
        quality_status: 'catalogued',
        quality_score: 2,
        is_verified: false,
        capabilities: {
          parser: true,
          filters: false,
          postfilters: false,
          log_reduction: false,
          splunk_props_transforms: false,
          cim_mapping: false,
          ocsf_mapping: false,
          fixtures: false,
          syntax_validated: false,
          splunk_ingestion_validated: false,
        },
        summary: 'Upstream SC4S catalogue coverage for a10 a10.',
        source_status: null,
        provenance_url: null,
        candidate_warnings: [],
      },
    ],
    facets: {
      origins: [{ value: 'sechub-resource', label: 'SecHub Resources SC4S pack', count: 3 }],
      vendors: [],
      products: [],
      relationships: [],
      trust_levels: [],
      quality_statuses: [{ value: 'validated', label: 'Validated', count: 12 }],
      source_statuses: [{ value: 'candidate', label: 'Community candidate', count: 5 }],
      artifact_types: [],
      capabilities: [],
      sc4s_versions: [],
    },
  },
  librarySourcesPayload: {
    sources: [
      {
        source_id: 'official',
        enabled: true,
        catalogue_url: 'https://sechub.s6ops.com/data/catalogue.json',
      },
    ],
  },
  libraryImportsPayload: {
    imports: [
      {
        import_id: 'imp_pan_panos_20260603T000000Z',
        source_id: 'official',
        entry_id: 'pan_panos',
        created_at: '2026-06-03T00:00:00Z',
        apply_allowed: true,
        reference_only: false,
        runtime_files: [{ source_path: 'local/config/app_parsers/panos.conf', target_path: 'local/config/app_parsers/panos.conf' }],
        reference_files: [{ source_path: 'README.md', target_path: 'README.md' }],
      },
    ],
  },
  packDetailPayload: null as unknown,
  runtimeStatePayload: {
    ok: true,
    generated_at: '2026-06-14T00:00:00Z',
    manager: { version: '1.0.0', health: 'ok' },
    control_daemon: { ok: true, provider: 'unix_socket' },
    sc4s: {
      running: true,
      status: 'running',
      health: 'healthy',
      image: 'ghcr.io/splunk/sc4s:3.43.0',
      image_version: '3.43.0',
      supported_version: '3.43.0',
      version_drift: false,
    },
    listeners: [
      { protocol: 'tcp', port: 514, desired: true, live: true, bind: '0.0.0.0' },
    ],
    counters: [
      { name: 'source.s_DEFAULT', component: 'source', metric: 'processed', value: 5000 },
    ],
    destinations: [
      { id: 'd_hec_DEFAULT', kind: 'splunk_hec', written: 4800, dropped: 0, queued: null },
    ],
    warnings: [],
    redaction: { secrets_present: true },
  },
}));

const detailedPack = {
  ...packsPayload.packs[0],
  export_artifacts: [
    {
      id: 'sc4s_parser',
      group: 'sc4s',
      source_path: 'sc4s/app_parsers/syslog/app-commvault_commcell.conf',
      target_path: 'local/config/app_parsers/syslog/app-commvault_commcell.conf',
      kind: 'syslog_ng_parser',
      rendered: false,
      contains_secrets: false,
      required: true,
    },
    {
      id: 'test_events',
      group: 'test_events',
      source_path: 'test-events/commvault.txt',
      target_path: 'test-events/commvault.txt',
      kind: 'fixture',
      rendered: false,
      contains_secrets: false,
      required: false,
    },
  ],
};

vi.mock('@tanstack/react-query', () => ({
  useQuery: ({ queryKey }: { queryKey: unknown[] }) => {
    const joined = queryKey.join(':');
    if (queryErrors[joined]) return { isLoading: false, isError: true, error: queryErrors[joined], data: undefined };
    if (joined === 'packs') {
      return { isLoading: false, isError: false, data: packsPayload };
    }
    if (joined === 'catalogue:[object Object]') {
      return { isLoading: false, isError: false, data: cataloguePayload };
    }
    if (joined === 'library:sources') {
      return { isLoading: false, isError: false, data: librarySourcesPayload };
    }
    if (joined === 'library:imports') {
      return { isLoading: false, isError: false, data: libraryImportsPayload };
    }
    if (joined === 'packs:commvault_commcell') {
      return { isLoading: false, isError: false, data: detailedPack };
    }
    if (joined === 'runtime:state') {
      return { isLoading: false, isError: false, data: runtimeStatePayload };
    }
    return { isLoading: false, isError: false, data: undefined };
  },
  useMutation: () => ({ mutate: vi.fn(), isPending: false, isError: false, error: null }),
}));

import { Dashboard } from './Dashboard';
import { Exports } from './Exports';
import { PackDetail } from './PackDetail';
import { PacksList } from './PacksList';

describe('user journey route coverage', () => {
  afterEach(() => {
    for (const key of Object.keys(queryErrors)) delete queryErrors[key];
  });

  it('renders dashboard cards for catalogue, packs, library, and Manager connection', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <Dashboard />
      </MantineProvider>,
    );

    expect(markup).toContain('Dashboard');
    expect(markup).toContain('SecHub sources');
    expect(markup).toContain('packs checked');
    expect(markup).toContain('Manager connection');
    expect(markup).toMatch(/Checking|Connected/);
  });

  it('renders runtime health section with state distinctions when runtime data is available', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <Dashboard />
      </MantineProvider>,
    );

    // Runtime health section exists
    expect(markup).toContain('Runtime health');
    // SC4S process card
    expect(markup).toContain('SC4S process');
    // Listeners card
    expect(markup).toContain('Listeners');
    // Counter summary
    expect(markup).toContain('Counter summary');
    // Destinations card
    expect(markup).toContain('Destinations');
    // Saved/staged vs live distinction — SC4S is not proven live by saved config alone
    expect(markup).toContain('Saved config does not prove SC4S');
    expect(markup).toContain('Splunk readback');
  });

  it('surfaces dashboard catalogue/library query failures and does not trust failed import counts', () => {
    queryErrors.catalogue = new Error('catalogue contract parse failed');
    queryErrors['library:sources'] = new Error('library sources contract parse failed');
    queryErrors['library:imports'] = new Error('imports contract parse failed');

    const markup = renderToStaticMarkup(
      <MantineProvider>
        <Dashboard />
      </MantineProvider>,
    );

    expect(markup).toContain('Unable to load source catalogue');
    expect(markup).toContain('Manager could not load this operator view. Check the service health and retry.');
    expect(markup).toContain('Could not load SecHub sources');
    expect(markup).not.toContain('library sources contract parse failed');
    expect(markup).toContain('Could not load checked packs');
    expect(markup).not.toContain('imports contract parse failed');
    expect(markup).toContain('SecHub connection unavailable — check source health');
    expect(markup).not.toContain('0 packs checked');
  });

  it('renders pack list and detail evidence without implying applied/live state', () => {
    const listMarkup = renderToStaticMarkup(
      <MantineProvider>
        <PacksList />
      </MantineProvider>,
    );
    const detailMarkup = renderToStaticMarkup(
      <MantineProvider>
        <PackDetail packId="commvault_commcell" />
      </MantineProvider>,
    );

    expect(listMarkup).toContain('Local packs');
    expect(listMarkup).toContain('Commvault CommCell');
    expect(detailMarkup).toContain('Supported ingestion transports');
    expect(detailMarkup).toContain('Test event fixtures');
    expect(detailMarkup).toContain('Included files for review/export');
    expect(detailMarkup).toContain('Recorded validation');
  });

  it('renders export workflow language as evidence-only download flow', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <Exports />
      </MantineProvider>,
    );

    expect(markup).toContain('Export bundles');
    expect(markup).toContain('Download generated SC4S/Splunk configuration and evidence artifacts for a selected local pack. Exporting does not apply changes.');
    expect(markup).toContain('Download export bundle');
    expect(markup).toContain('Local pack');
  });
});
