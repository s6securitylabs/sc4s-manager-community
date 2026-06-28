import { describe, expect, it } from 'vitest';

import { hrefForAppPath, normalizeAppPath, normalizeBasePath } from './navigation';

describe('normalizeBasePath', () => {
  it('keeps root base as an empty prefix', () => {
    expect(normalizeBasePath('/')).toBe('');
  });

  it('normalizes subpath base URLs without creating protocol-relative prefixes', () => {
    expect(normalizeBasePath('/sc4s/')).toBe('/sc4s');
    expect(normalizeBasePath('https://example.test/sc4s/')).toBe('/sc4s');
  });
});

describe('normalizeAppPath', () => {
  it('collapses repeated leading slashes so internal paths cannot become protocol-relative URLs', () => {
    expect(normalizeAppPath('//evil.test/pack')).toBe('/evil.test/pack');
  });

  it('removes query strings and fragments from router paths', () => {
    expect(normalizeAppPath('/packs?id=x#frag')).toBe('/packs');
  });
});

describe('hrefForAppPath', () => {
  it('keeps generated internal hrefs rooted in the application', () => {
    expect(hrefForAppPath('//evil.test/pack')).not.toMatch(/^\/\//);
  });
});
