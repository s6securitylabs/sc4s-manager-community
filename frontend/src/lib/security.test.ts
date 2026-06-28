import { describe, expect, it } from 'vitest';

import { sanitizeDownloadFilename } from './download';
import { safeHttpUrl } from './url';

describe('sanitizeDownloadFilename', () => {
  it('removes path separators and control characters', () => {
    expect(sanitizeDownloadFilename('../bad/name\u0000.zip')).toBe('bad-name.zip');
  });

  it('uses fallback for empty filenames', () => {
    expect(sanitizeDownloadFilename('...', 'fallback.zip')).toBe('fallback.zip');
  });
});

describe('safeHttpUrl', () => {
  it('allows http and https URLs', () => {
    expect(safeHttpUrl('https://example.com/docs')).toBe('https://example.com/docs');
  });

  it('blocks javascript URLs', () => {
    expect(safeHttpUrl('javascript:alert(1)')).toBeUndefined();
  });
});
