import { MantineProvider } from '@mantine/core';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { PackDetail } from './PackDetail';

const { packDetail } = vi.hoisted(() => ({
  packDetail: {
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
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    isLoading: false,
    isError: false,
    data: packDetail,
  }),
  useMutation: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  }),
}));

describe('PackDetail', () => {
  it('renders plain-language export copy before operators treat a pack as live', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <PackDetail packId={packDetail.id} />
      </MantineProvider>,
    );

    expect(markup).toContain('Export only — not applied to SC4S');
    expect(markup).toContain('SC4S is not updated');
    expect(markup).toContain('reload SC4S');
    expect(markup).toContain('Splunk readback');
  });

  it('uses operator-facing pack labels while preserving diagnostics', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <PackDetail packId={packDetail.id} />
      </MantineProvider>,
    );

    expect(markup).toContain('Events this pack expects to recognise');
    expect(markup).toContain('How Manager identifies it:');
    expect(markup).toContain('Diagnostics: raw match expression');
    expect(markup).toContain('^AuditTrail:');
    expect(markup).toContain('Example event file:');
    expect(markup).toContain('Included files for review/export');
    expect(markup).toContain('Pack source file:');
    expect(markup).toContain('Secret material present:');
    expect(markup).toContain('Export diagnostics');
    expect(markup).toContain('Bundle group:');
    expect(markup).toContain('File type:');
    expect(markup).toContain('Rendered from template:');
    expect(markup).toContain('Required for export:');

    expect(markup).not.toContain('Expected event families');
    expect(markup).not.toContain('Match engine:');
    expect(markup).not.toContain('Fixture path:');
    expect(markup).not.toContain('Files included in export bundle');
    expect(markup).not.toContain('Artifact group:');
    expect(markup).not.toContain('Rendered file:');
    expect(markup).not.toContain('contains secrets:');
  });
});
