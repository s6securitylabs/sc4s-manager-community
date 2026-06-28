import { MantineProvider } from '@mantine/core';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { CatalogueListEntry } from '../api/packs';
import { CatalogueListCard, buildCatalogueParams } from './CatalogueList';

const candidateEntry: CatalogueListEntry = {
  id: 'community_pfsense_filterlog_issue',
  display_name: 'Community pfSense Filterlog issue candidate',
  vendor: 'pfsense',
  product: 'filterlog',
  origins: ['community-extra'],
  effective_origin: 'community-extra',
  relationship_to_upstream: 'new_pack',
  trust_level: 'community_submitted',
  quality_status: 'catalogued',
  quality_score: 2,
  is_verified: false,
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
  summary: 'Issue snippet only.',
  source_status: 'candidate',
  provenance_url: 'https://github.com/splunk/splunk-connect-for-syslog/issues/1234',
  candidate_warnings: ['Community issue snippet only. Not validated for production.'],
};

describe('buildCatalogueParams', () => {
  it('includes source status filters for community candidate views', () => {
    expect(
      buildCatalogueParams({
        q: '',
        origin: 'community-extra',
        product: null,
        vendor: null,
        min_quality_score: null,
        source_status: 'candidate',
        has_reduction: false,
        has_splunk_knowledge: false,
      }),
    ).toEqual({ limit: '60', origin: 'community-extra', source_status: 'candidate' });
  });
});

describe('CatalogueListCard', () => {
  it('renders explicit unvalidated candidate warnings', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <CatalogueListCard entry={candidateEntry} />
      </MantineProvider>,
    );

    expect(markup).toContain('Community candidate');
    expect(markup).toContain('Not validated for production');
    expect(markup).toContain('github.com');
  });
});
