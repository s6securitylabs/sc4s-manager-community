import '@mantine/core/styles.css';
import './styles.css';

import { MantineProvider, createTheme } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { useEffect, useMemo, useState } from 'react';
import ReactDOM from 'react-dom/client';

import { AppLayout } from './components/AppLayout';
import { CatalogueDetail } from './routes/CatalogueDetail';
import { CatalogueList } from './routes/CatalogueList';
import { Dashboard } from './routes/Dashboard';
import { Exports } from './routes/Exports';
import { Library } from './routes/Library';
import { Destinations } from './routes/Destinations';
import { OnboardingPreview } from './routes/OnboardingPreview';
import { PackDetail } from './routes/PackDetail';
import { PacksList } from './routes/PacksList';
import { RoutesPage } from './routes/RoutesPage';
import { Sources } from './routes/Sources';
import { appPathFromLocation, safeDecodeURIComponent } from './lib/navigation';

const queryClient = new QueryClient();

const theme = createTheme({
  primaryColor: 'cyan',
  defaultRadius: 'md',
  fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
  headings: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
    fontWeight: '700',
  },
  colors: {
    dark: [
      '#eef7fb',
      '#c9d8e6',
      '#aab8c9',
      '#8a9eb8',
      '#6f829f',
      '#506079',
      '#2a3446',
      '#171f33',
      '#131b2e',
      '#0b1326',
    ],
    cyan: [
      '#dbfbff',
      '#b0f5ff',
      '#7ceeff',
      '#44e8ff',
      '#1fd5f0',
      '#10b8d2',
      '#0596af',
      '#037488',
      '#035764',
      '#013846',
    ],
  },
  components: {
    Badge: {
      defaultProps: {
        radius: 'sm',
      },
    },
    Card: {
      defaultProps: {
        radius: 'lg',
      },
    },
  },
});

function currentPath() {
  return appPathFromLocation();
}

function AppRouter() {
  const [path, setPath] = useState(currentPath());

  useEffect(() => {
    const onPopState = () => setPath(currentPath());
    const onNavigate = (event: Event) => setPath((event as CustomEvent<string>).detail || currentPath());
    window.addEventListener('popstate', onPopState);
    window.addEventListener('sc4s:navigate', onNavigate);
    return () => {
      window.removeEventListener('popstate', onPopState);
      window.removeEventListener('sc4s:navigate', onNavigate);
    };
  }, []);

  const route = useMemo(() => {
    if (path === '/') return <Dashboard />;
    if (path === '/library') return <Library />;
    if (path === '/catalogue') return <CatalogueList />;
    if (path.startsWith('/catalogue/')) {
      const entryId = safeDecodeURIComponent(path.replace('/catalogue/', ''));
      if (entryId) return <CatalogueDetail entryId={entryId} />;
    }
    if (path === '/packs') return <PacksList />;
    if (path.startsWith('/packs/')) {
      const packId = safeDecodeURIComponent(path.replace('/packs/', ''));
      if (packId) return <PackDetail packId={packId} />;
    }
    if (path === '/onboarding-preview') return <OnboardingPreview />;
    if (path === '/sources') return <Sources />;
    if (path === '/destinations') return <Destinations />;
    if (path === '/routes') return <RoutesPage />;
    if (path === '/exports') return <Exports />;
    return <Dashboard />;
  }, [path]);

  return <AppLayout path={path}>{route}</AppLayout>;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="auto" theme={theme}>
      <QueryClientProvider client={queryClient}>
        <AppRouter />
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>,
);
