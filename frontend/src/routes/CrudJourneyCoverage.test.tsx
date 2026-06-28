import { MantineProvider } from '@mantine/core';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

const { sourcesPayload, sourceCatalogPayload, destinationsPayload, routesPayload, queryErrors } = vi.hoisted(() => ({
  queryErrors: {} as Record<string, Error | undefined>,
  sourcesPayload: {
    sources: [
      {
        name: 'asa_lab',
        filter: 'f_asa_lab',
        source: '10.10.2.0/24',
        vendor_product: 'cisco_asa',
        index: 'netfw',
        compliance: 'pci',
        path: 'config/filters/asa_lab.conf',
        apply_mode: 'reloadable',
      },
    ],
  },
  sourceCatalogPayload: {
    supported_sc4s_version: '3.43.0',
    sources: [{ vendor_product: 'cisco_asa', label: 'Cisco ASA', default_index: 'netfw' }],
  },
  destinationsPayload: {
    supported_sc4s_version: '3.43.0',
    destinations: [
      { kind: 'hec', id: 'DEFAULT', url: 'https://splunk:8088', token: '[REDACTED]', tls_verify: 'yes' },
      { kind: 'hec', id: 'V1CRUDHEC', url: 'https://splunk2:8088', token: '[REDACTED]', mode: 'SELECT' },
      { kind: 'hec', id: 'LEAKY', url: 'https://splunk3:8088', token: 'abc123-secret', mode: 'SELECT' },
      { kind: 'syslog', id: 'SIEM', host: '10.0.0.5', port: '601', transport: 'tcp', mode: 'SELECT' },
    ],
  },
  routesPayload: {
    routes: [
      {
        id: 'asa_to_hec',
        source: 'asa_lab',
        pack: 'cisco_asa',
        destination_kind: 'hec',
        destination_id: 'V1CRUDHEC',
        selector: 'selectors/sc4s-lp-cisco_asa_d_hec_v1crudhec.conf',
        apply_mode: 'reloadable',
      },
    ],
  },
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: ({ queryKey }: { queryKey: unknown[] }) => {
    const joined = queryKey.join(':');
    if (queryErrors[joined]) return { isLoading: false, isError: true, error: queryErrors[joined], data: undefined };
    if (joined === 'sources') return { isLoading: false, isError: false, data: sourcesPayload };
    if (joined === 'source-catalog') return { isLoading: false, isError: false, data: sourceCatalogPayload };
    if (joined === 'destinations') return { isLoading: false, isError: false, data: destinationsPayload };
    if (joined === 'routes') return { isLoading: false, isError: false, data: routesPayload };
    return { isLoading: false, isError: false, data: undefined };
  },
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  useMutation: () => ({ mutate: vi.fn(), isPending: false, isError: false, error: null }),
}));

import { Destinations } from './Destinations';
import { RoutesPage } from './RoutesPage';
import { Sources } from './Sources';

describe('CRUD operator journey route coverage', () => {
  afterEach(() => {
    for (const key of Object.keys(queryErrors)) delete queryErrors[key];
  });

  it('renders the sources page with onboarding form, inventory, and staged-state language', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <Sources />
      </MantineProvider>,
    );

    expect(markup).toContain('Sources');
    expect(markup).toContain('Stage source onboarding');
    expect(markup).toContain('Source ID');
    expect(markup).toContain('Source match');
    expect(markup).toContain('asa_lab');
    expect(markup).toContain('cisco_asa');
    expect(markup).toContain('Save staged source');
    expect(markup).toContain('Validate and reload SC4S now');
    expect(markup).toContain('Delete');
  });

  it('renders the destinations page with HEC form, redacted inventory, and restart-scope warning', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <Destinations />
      </MantineProvider>,
    );

    expect(markup).toContain('Destinations');
    expect(markup).toContain('HEC URL');
    expect(markup).toContain('never echoed');
    expect(markup).toContain('Token present (redacted)');
    expect(markup).toContain('Token hidden — check server redaction');
    expect(markup).toContain('restart');
    expect(markup).toContain('V1CRUDHEC');
    expect(markup).toContain('Save staged destination');
    expect(markup).not.toContain('abc123');
    expect(markup).not.toContain('abc123-secret');
  });

  it('renders the routes page connecting source, pack, and destination with live-proof caveat', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <RoutesPage />
      </MantineProvider>,
    );

    expect(markup).toContain('Routes');
    expect(markup).toContain('Route ID');
    expect(markup).toContain('SC4S vendor_product');
    expect(markup).toContain('asa_to_hec');
    expect(markup).toContain('Splunk readback');
    expect(markup).toContain('Stage route');
    expect(markup).toContain('HEC V1CRUDHEC');
  });

  it('surfaces route prerequisite inventory failures and blocks route submission', () => {
    queryErrors.sources = new Error('sources inventory schema mismatch');
    queryErrors.destinations = new Error('destinations inventory unavailable');

    const markup = renderToStaticMarkup(
      <MantineProvider>
        <RoutesPage />
      </MantineProvider>,
    );

    expect(markup).toContain('Unable to load source prerequisites');
    expect(markup).toContain('Manager could not load this operator view. Check the service health and retry.');
    expect(markup).toContain('Unable to load destination prerequisites');
    expect(markup).toContain('destinations inventory unavailable');
    expect(markup).toContain('Route submission blocked');
    expect(markup).toContain('disabled');
  });
});
