import { describe, expect, it } from 'vitest';

import { catalogueDetailSchema, catalogueListResponseSchema, filenameFromContentDisposition } from './packs';

describe('filenameFromContentDisposition', () => {
  it('prefers RFC 5987 encoded filenames', () => {
    expect(filenameFromContentDisposition("attachment; filename=legacy.zip; filename*=UTF-8''source%20pack.zip")).toBe('source pack.zip');
  });

  it('parses quoted filenames', () => {
    expect(filenameFromContentDisposition('attachment; filename="vendor-export.zip"')).toBe('vendor-export.zip');
  });

  it('parses escaped quotes without ambiguous regex backtracking', () => {
    expect(filenameFromContentDisposition('attachment; filename="vendor-\\"export.zip"')).toBe('vendor-"export.zip');
  });

  it('rejects a malformed quoted filename with many escapes', () => {
    const malformed = `attachment; filename="${'\\'.repeat(10_000)}!`;
    expect(filenameFromContentDisposition(malformed)).toBeUndefined();
  });

  it('ignores malformed encoded filenames and falls back', () => {
    expect(filenameFromContentDisposition("attachment; filename=fallback.zip; filename*=UTF-8''%E0%A4%A")).toBe('fallback.zip');
  });
});

describe('catalogueListResponseSchema', () => {
  it('accepts facet metadata used by the filterable catalogue UI', () => {
    const parsed = catalogueListResponseSchema.parse({
      entries: [],
      count: 0,
      limit: 60,
      offset: 0,
      facets: {
        origins: [{ value: 'sc4s-inbuilt', label: 'SC4S built-in', count: 249 }],
        vendors: [{ value: 'cisco', label: 'Cisco', count: 12 }],
        products: [],
        relationships: [],
        trust_levels: [],
        quality_statuses: [{ value: 'validated', label: 'Validated', count: 1 }],
        source_statuses: [],
        artifact_types: [{ value: 'syslog_app_parser', label: 'syslog app parser', count: 111 }],
        capabilities: [{ value: 'log_reduction', label: 'Log reduction', count: 1 }],
        sc4s_versions: [{ value: '3.43.0', label: '3.43.0', count: 249 }],
      },
    });

    expect(parsed.facets?.origins[0].value).toBe('sc4s-inbuilt');
  });

  it('accepts product-first entries with quality score and verified flag', () => {
    const parsed = catalogueListResponseSchema.parse({
      entries: [
        {
          id: 'commvault_commcell',
          display_name: 'Commvault CommCell',
          vendor: 'commvault',
          product: 'commcell',
          origins: ['sechub-resource'],
          effective_origin: 'sechub-resource',
          relationship_to_upstream: 'new_pack',
          trust_level: 's6_verified',
          quality_status: 'validated',
          quality_score: 4,
          is_verified: true,
          capabilities: {
            parser: true,
            filters: false,
            postfilters: false,
            log_reduction: true,
            splunk_props_transforms: true,
            cim_mapping: true,
            ocsf_mapping: false,
            fixtures: true,
            syntax_validated: true,
            splunk_ingestion_validated: true,
          },
          summary: 'Validated product pack.',
          candidate_warnings: [],
        },
      ],
      count: 1,
      limit: 60,
      offset: 0,
      facets: {
        origins: [],
        vendors: [{ value: 'commvault', label: 'Commvault', count: 1 }],
        products: [{ value: 'commcell', label: 'Commcell', count: 1 }],
        relationships: [],
        trust_levels: [],
        quality_statuses: [],
        source_statuses: [],
        artifact_types: [],
        capabilities: [],
        sc4s_versions: [],
      },
    });

    expect(parsed.entries[0].product).toBe('commcell');
    expect(parsed.entries[0].quality_score).toBe(4);
    expect(parsed.entries[0].is_verified).toBe(true);
  });

  it('accepts source status facets and candidate provenance metadata for community entries', () => {
    const parsed = catalogueListResponseSchema.parse({
      entries: [
        {
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
          candidate_warnings: ['Unvalidated community candidate.'],
        },
      ],
      count: 1,
      limit: 60,
      offset: 0,
      facets: {
        origins: [{ value: 'community-extra', label: 'community-extra', count: 1 }],
        vendors: [{ value: 'pfsense', label: 'pfSense', count: 1 }],
        products: [{ value: 'filterlog', label: 'Filterlog', count: 1 }],
        relationships: [{ value: 'new_pack', label: 'new_pack', count: 1 }],
        trust_levels: [{ value: 'community_submitted', label: 'Community submitted', count: 1 }],
        quality_statuses: [{ value: 'catalogued', label: 'Catalogued', count: 1 }],
        source_statuses: [{ value: 'candidate', label: 'Candidate', count: 1 }],
        artifact_types: [],
        capabilities: [],
        sc4s_versions: [],
      },
    });

    expect(parsed.facets?.source_statuses[0].value).toBe('candidate');
  });
});

describe('catalogueDetailSchema', () => {
  it('accepts provenance and warning metadata for community candidate detail entries', () => {
    const parsed = catalogueDetailSchema.parse({
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
      candidate_warnings: ['Unvalidated community candidate.'],
      provenance: {
        origin: 'community-extra',
        source_kind: 'issue',
        url: 'https://github.com/splunk/splunk-connect-for-syslog/issues/1234',
        source_status: 'candidate',
      },
      upstream: {},
      sc4s_manager: null,
      artifacts: [],
      artifact_inventory: {},
      presets: [],
      field_contract: {},
      comparison_to_upstream: {},
      validation: {
        state: 'unvalidated_source_corpus',
      },
      known_limitations: ['No Splunk validation evidence.'],
      feedback: { likes: 0, rating_average: null, comments_url: null },
    });

    expect(parsed.provenance).not.toBeNull();
    expect(parsed.provenance?.source_kind).toBe('issue');
    expect(parsed.candidate_warnings[0]).toContain('Unvalidated');
  });
});
