import { MantineProvider } from '@mantine/core';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { CatalogueDetail } from './CatalogueDetail';

const { candidateDetail } = vi.hoisted(() => ({
  candidateDetail: {
    id: 'community_pfsense_filterlog_issue',
    display_name: 'Community pfSense Filterlog issue candidate',
    vendor: 'pfsense',
    product: 'filterlog',
    summary: 'Issue snippet only.',
    origins: ['community-extra'],
    effective_origin: 'community-extra',
    relationship_to_upstream: 'new_pack',
    trust_level: 'community_submitted',
    quality_status: 'catalogued',
    quality_score: 2,
    is_verified: false,
    source_status: 'candidate',
    candidate_warnings: ['Community issue snippet only. Not validated for production.'],
    provenance_url: 'https://github.com/splunk/splunk-connect-for-syslog/issues/1234',
    provenance: {
      source_kind: 'issue',
      source_status: 'candidate',
      url: 'https://github.com/splunk/splunk-connect-for-syslog/issues/1234',
    },
    capabilities: {
      parser: false,
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
    validation: {
      state: 'candidate',
      last_verified_at: null,
      validated_by: null,
      summary: null,
      evidence_paths: [],
    },
    upstream: null,
    sc4s_manager: null,
    comparison_to_upstream: null,
    field_contract: null,
    presets: [],
    feedback: {
      likes: 0,
      rating_average: null,
      comments_url: null,
    },
    artifact_inventory: {},
    artifacts: [],
    known_limitations: [],
  },
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    isLoading: false,
    isError: false,
    data: candidateDetail,
  }),
}));

describe('CatalogueDetail', () => {
  it('renders unvalidated community-candidate review and provenance guidance', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <CatalogueDetail entryId={candidateDetail.id} />
      </MantineProvider>,
    );

    expect(markup).toContain('Unvalidated community candidate');
    expect(markup).toContain('Community issue snippet only. Not validated for production.');
    expect(markup).toContain('Review status and provenance');
    expect(markup).toContain('Review status');
    expect(markup).toContain('Community candidate');
    expect(markup).toContain('Viewing only — not applied to SC4S');
    expect(markup).toContain('for review only');
    expect(markup).toContain('import and install a pack');
    expect(markup).toContain('Splunk readback');
    expect(markup).toContain('Provenance URL');
    expect(markup).toContain('github.com');
    expect(markup).toContain('No human-readable validation summary recorded');
    expect(markup).toContain('No artifact inventory recorded');
  });
});
