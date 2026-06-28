import '@mantine/core/styles.css';
import './styles.css';

import { MantineProvider, createTheme } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { useEffect, useMemo, useState } from 'react';
import ReactDOM from 'react-dom/client';

import { AppLayout } from './components/AppLayout';
import { checkAuthStatus, logout } from './api/auth';
import { CatalogueDetail } from './routes/CatalogueDetail';
import { CatalogueList } from './routes/CatalogueList';
import { Dashboard } from './routes/Dashboard';
import { Exports } from './routes/Exports';
import { Library } from './routes/Library';
import { Destinations } from './routes/Destinations';
import { Login } from './routes/Login';
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
  fontSmoothing: true,
  headings: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
    fontWeight: '700',
  },
  colors: {
    dark: [
      '#f1f5f9',
      '#cbd5e1',
      '#94a3b8',
      '#64748b',
      '#475569',
      '#334155',
      '#1e293b',
      '#0f172a',
      '#0a1120',
      '#060c17',
    ],
    cyan: [
      '#ecfeff',
      '#cffafe',
      '#a5f3fc',
      '#67e8f9',
      '#22d3ee',
      '#06b6d4',
      '#0891b2',
      '#0e7490',
      '#155e75',
      '#164e63',
    ],
  },
  components: {
    Badge: {
      defaultProps: { radius: 'sm' },
    },
    Card: {
      defaultProps: { radius: 'lg' },
    },
    Paper: {
      defaultProps: { radius: 'lg' },
    },
    Button: {
      defaultProps: { radius: 'md' },
    },
  },
});

function currentPath() {
  return appPathFromLocation();
}

function AppRouter() {
  const [path, setPath] = useState(currentPath());
  const [authChecked, setAuthChecked] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    checkAuthStatus()
      .then((authenticated) => {
        setIsAuthenticated(authenticated);
        setAuthChecked(true);
      })
      .catch(() => {
        setAuthChecked(true);
      });
  }, []);

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

  const handleLogout = async () => {
    await logout();
    setIsAuthenticated(false);
    queryClient.clear();
  };

  if (!authChecked) return null;

  if (!isAuthenticated) {
    return <Login onLogin={() => setIsAuthenticated(true)} />;
  }

  return <AppLayout path={path} onLogout={handleLogout}>{route}</AppLayout>;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="light" theme={theme}>
      <QueryClientProvider client={queryClient}>
        <AppRouter />
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>,
);
