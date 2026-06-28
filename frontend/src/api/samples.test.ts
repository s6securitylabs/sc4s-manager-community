import { describe, expect, it } from 'vitest';

import {
  candidateMatchSchema,
  classifyResponseSchema,
  expectedMetadataSchema,
  previewResponseSchema,
} from './samples';

const ciscoAsaClassify = {
  ok: true,
  format_hints: ['rfc5424'],
  timestamp_hint: '2026-01-15T12:00:00Z',
  host_hint: 'firewall01',
  redacted_sample_preview: '<134>1 2026-01-15T12:00:00Z firewall01 ASA - - %ASA-6-302013: Built outbound TCP',
  stored: false as const,
  limitations: ['Classification is heuristic only; no SC4S parser is run.', 'Results are not stored or promoted.'],
};

const ciscoAsaPreview = {
  classification: ciscoAsaClassify,
  candidate_matches: [
    {
      pack_id: 'cisco_asa',
      vendor_product: 'cisco_asa',
      reason: 'Sample contains %ASA- or %FTD- marker tokens characteristic of Cisco ASA/FTD syslog messages.',
      confidence: 'high' as const,
      requires_operator_review: true,
    },
  ],
  expected_metadata: {
    index: 'netfw',
    sourcetype: 'cisco_asa',
    source: 'cisco_asa',
    host: 'firewall01',
    timestamp_policy: 'unknown_requires_validation',
  },
  next_actions: [
    'Review matched pack/parser candidates — this is a preview, not a validated match.',
  ],
  validated: false as const,
};

const unknownFallback = {
  classification: {
    ok: true,
    format_hints: ['raw_headerless'],
    timestamp_hint: null,
    host_hint: null,
    redacted_sample_preview: '2026-01-15 12:00:00 INFO Application started',
    stored: false as const,
    limitations: ['Classification is heuristic only; no SC4S parser is run.'],
  },
  candidate_matches: [],
  expected_metadata: {
    index: null,
    sourcetype: null,
    source: null,
    host: null,
    timestamp_policy: 'unknown_requires_validation',
  },
  next_actions: ['Identify the source vendor and product.'],
  validated: false as const,
};

describe('samples API schemas', () => {
  describe('classifyResponseSchema', () => {
    it('accepts a Cisco ASA classification result', () => {
      const result = classifyResponseSchema.parse(ciscoAsaClassify);
      expect(result.ok).toBe(true);
      expect(result.format_hints).toContain('rfc5424');
      expect(result.stored).toBe(false);
    });

    it('enforces stored is always false', () => {
      expect(() =>
        classifyResponseSchema.parse({ ...ciscoAsaClassify, stored: true }),
      ).toThrow();
    });

    it('accepts null timestamp and host hints for unknown samples', () => {
      const result = classifyResponseSchema.parse(unknownFallback.classification);
      expect(result.timestamp_hint).toBeNull();
      expect(result.host_hint).toBeNull();
    });

    it('accepts raw_headerless format hint', () => {
      const result = classifyResponseSchema.parse(unknownFallback.classification);
      expect(result.format_hints).toContain('raw_headerless');
    });
  });

  describe('candidateMatchSchema', () => {
    it('accepts a high-confidence Cisco ASA candidate', () => {
      const result = candidateMatchSchema.parse(ciscoAsaPreview.candidate_matches[0]);
      expect(result.vendor_product).toBe('cisco_asa');
      expect(result.confidence).toBe('high');
      expect(result.requires_operator_review).toBe(true);
    });

    it('rejects unknown confidence values', () => {
      expect(() =>
        candidateMatchSchema.parse({ ...ciscoAsaPreview.candidate_matches[0], confidence: 'very_high' }),
      ).toThrow();
    });
  });

  describe('expectedMetadataSchema', () => {
    it('accepts matched metadata with index and sourcetype', () => {
      const result = expectedMetadataSchema.parse(ciscoAsaPreview.expected_metadata);
      expect(result.index).toBe('netfw');
      expect(result.sourcetype).toBe('cisco_asa');
    });

    it('accepts null index and sourcetype for unmatched samples', () => {
      const result = expectedMetadataSchema.parse(unknownFallback.expected_metadata);
      expect(result.index).toBeNull();
      expect(result.sourcetype).toBeNull();
    });
  });

  describe('previewResponseSchema', () => {
    it('accepts a Cisco ASA preview response with candidate matches', () => {
      const result = previewResponseSchema.parse(ciscoAsaPreview);
      expect(result.validated).toBe(false);
      expect(result.candidate_matches).toHaveLength(1);
      expect(result.candidate_matches[0].vendor_product).toBe('cisco_asa');
    });

    it('enforces validated is always false', () => {
      expect(() =>
        previewResponseSchema.parse({ ...ciscoAsaPreview, validated: true }),
      ).toThrow();
    });

    it('accepts an empty candidate_matches array for unknown/fallback path', () => {
      const result = previewResponseSchema.parse(unknownFallback);
      expect(result.candidate_matches).toHaveLength(0);
      expect(result.next_actions.length).toBeGreaterThan(0);
    });

    it('carries classification data through the preview result', () => {
      const result = previewResponseSchema.parse(ciscoAsaPreview);
      expect(result.classification.format_hints).toContain('rfc5424');
      expect(result.classification.stored).toBe(false);
    });

    it('accepts extra fields via passthrough for forward compatibility', () => {
      const result = previewResponseSchema.parse({
        ...ciscoAsaPreview,
        future_field: 'some_value',
      });
      expect((result as Record<string, unknown>)['future_field']).toBe('some_value');
    });
  });
});
