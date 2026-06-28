import { describe, expect, it } from 'vitest';

import {
  configureDestinationResponseSchema,
  deleteDestinationResponseSchema,
  deleteRouteResponseSchema,
  deleteSourceResponseSchema,
  destinationsResponseSchema,
  onboardSourceResponseSchema,
  routesResponseSchema,
  sourcesResponseSchema,
  upsertRouteResponseSchema,
} from './operations';

describe('sourcesResponseSchema', () => {
  it('accepts the backend source inventory shape', () => {
    const parsed = sourcesResponseSchema.parse({
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
    });
    expect(parsed.sources[0].filter).toBe('f_asa_lab');
  });
});

describe('onboardSourceResponseSchema', () => {
  it('keeps staged/applied state distinguishable via control.skipped', () => {
    const parsed = onboardSourceResponseSchema.parse({
      ok: true,
      apply_mode: 'reloadable',
      service: { filter: 'f_asa_lab', restart_required: true },
      validation: { ok: true, checked_at: '2026-06-12T00:00:00Z' },
      control: { ok: true, skipped: true },
      test_instructions: { udp: 'logger ...', tcp: 'printf ...' },
    });
    expect(parsed.control.skipped).toBe(true);
    expect(parsed.validation.ok).toBe(true);
  });
});

describe('deleteSourceResponseSchema', () => {
  it('requires removed_paths evidence for cleanup proof', () => {
    const parsed = deleteSourceResponseSchema.parse({
      ok: true,
      filter: 'f_asa_lab',
      removed_paths: ['/opt/sc4s/local/config/filters/asa_lab.conf'],
      validation: { ok: true },
      apply_mode: 'reloadable',
    });
    expect(parsed.removed_paths).toHaveLength(1);
  });
});

describe('destinationsResponseSchema', () => {
  it('accepts redacted tokens without re-expanding them', () => {
    const parsed = destinationsResponseSchema.parse({
      supported_sc4s_version: '3.43.0',
      destinations: [
        { kind: 'hec', id: 'DEFAULT', url: 'https://splunk:8088', token: '[REDACTED]', tls_verify: 'yes' },
        { kind: 'syslog', id: 'SIEM', host: '10.0.0.5', port: '601', transport: 'tcp', mode: 'SELECT' },
      ],
    });
    expect(parsed.destinations[0].token).toBe('[REDACTED]');
    expect(parsed.destinations[1].mode).toBe('SELECT');
  });
});

describe('configureDestinationResponseSchema', () => {
  it('accepts redacted update maps and restart-scoped apply mode', () => {
    const parsed = configureDestinationResponseSchema.parse({
      ok: true,
      kind: 'hec',
      id: 'V1CRUDHEC',
      apply_mode: 'restart_required',
      updates: { SC4S_DEST_SPLUNK_HEC_V1CRUDHEC_URL: 'https://splunk:8088', SC4S_DEST_SPLUNK_HEC_V1CRUDHEC_TOKEN: '[REDACTED]' },
      selector: null,
      backup: '/var/lib/sc4s-manager/backups/env_file.bak',
      validation: { ok: true },
      control: { ok: true, skipped: true },
    });
    expect(parsed.updates.SC4S_DEST_SPLUNK_HEC_V1CRUDHEC_TOKEN).toBe('[REDACTED]');
    expect(parsed.apply_mode).toBe('restart_required');
  });
});

describe('deleteDestinationResponseSchema', () => {
  it('lists removed env keys and selectors for cleanup evidence', () => {
    const parsed = deleteDestinationResponseSchema.parse({
      ok: true,
      kind: 'hec',
      id: 'V1CRUDHEC',
      removed_env_keys: ['SC4S_DEST_SPLUNK_HEC_V1CRUDHEC_TOKEN', 'SC4S_DEST_SPLUNK_HEC_V1CRUDHEC_URL'],
      removed_selectors: [],
      validation: { ok: true },
      apply_mode: 'restart_required',
    });
    expect(parsed.removed_env_keys).toContain('SC4S_DEST_SPLUNK_HEC_V1CRUDHEC_TOKEN');
  });
});

describe('routesResponseSchema and route mutations', () => {
  it('accepts route inventory with selector linkage', () => {
    const parsed = routesResponseSchema.parse({
      routes: [
        {
          id: 'asa_to_hec',
          source: 'asa_lab',
          pack: 'cisco_asa',
          destination_kind: 'hec',
          destination_id: 'V1CRUDHEC',
          selector: '/opt/sc4s/local/config/app_parsers/selectors/sc4s-lp-cisco_asa_d_hec_v1crudhec.conf',
          apply_mode: 'reloadable',
        },
      ],
    });
    expect(parsed.routes[0].destination_id).toBe('V1CRUDHEC');
  });

  it('parses upsert and delete responses with validation evidence', () => {
    const upsert = upsertRouteResponseSchema.parse({
      ok: true,
      route: { id: 'asa_to_hec', source: 'asa_lab', pack: 'cisco_asa', destination_kind: 'hec', destination_id: 'V1CRUDHEC' },
      validation: { ok: true },
      control: { ok: true, skipped: false },
    });
    expect(upsert.control.skipped).toBe(false);

    const removed = deleteRouteResponseSchema.parse({
      ok: true,
      id: 'asa_to_hec',
      removed_selectors: ['/opt/sc4s/local/config/app_parsers/selectors/sc4s-lp-cisco_asa_d_hec_v1crudhec.conf'],
      validation: { ok: true },
      apply_mode: 'reloadable',
    });
    expect(removed.removed_selectors).toHaveLength(1);
  });
});
