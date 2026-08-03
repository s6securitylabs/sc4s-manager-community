import { describe, expect, it } from 'vitest';
import { libraryCatalogueResponseSchema } from './library';

describe('published catalogue compatibility', () => {
  it('accepts non-downloadable upstream entries with a null version', () => {
    const parsed = libraryCatalogueResponseSchema.safeParse({
      source_id: 'embedded',
      entries: [{ id: 'upstream_only', version: null, download_available: false }],
      filters: {},
    });
    expect(parsed.success).toBe(true);
  });
});
