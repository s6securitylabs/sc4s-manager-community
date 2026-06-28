import { MantineProvider } from '@mantine/core';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { AppLayout } from './AppLayout';

describe('AppLayout navigation', () => {
  it('includes the SecHub Resources route alongside dashboard, catalogue, packs, and exports', () => {
    const markup = renderToStaticMarkup(
      <MantineProvider>
        <AppLayout path="/">
          <div>body</div>
        </AppLayout>
      </MantineProvider>,
    );

    expect(markup).toContain('Dashboard');
    expect(markup).toContain('SC4S Library');
    expect(markup).toContain('/library');
    expect(markup).toContain('Source Catalogue');
    expect(markup).toContain('Packs');
    expect(markup).toContain('/packs');
    expect(markup).toContain('Exports');
    expect(markup).toContain('Switch to dark mode');
    expect(markup).toContain('Operator console for Library source status, local packs, staged source changes, and export evidence.');
    const removedRemoteRoute = '/' + 'market' + 'place';
    const removedPackRoute = '/' + 'pro' + 'files';
    expect(markup).not.toContain(removedRemoteRoute);
    expect(markup).not.toContain(removedPackRoute);
  });
});
