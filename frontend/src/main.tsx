import '@mantine/core/styles.css';
import './styles.css';

import { Alert, Center, Loader, MantineProvider, Stack, Text, createTheme } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import ReactDOM from 'react-dom/client';

import { AppLayout } from './components/AppLayout';
import { checkAuthStatus, logout } from './api/auth';
import { Login } from './routes/Login';
import { appPathFromLocation, safeDecodeURIComponent } from './lib/navigation';
import { AUTH_EXPIRED_EVENT } from './api/client';

const Dashboard = lazy(() => import('./routes/Dashboard').then((module) => ({ default: module.Dashboard })));
const Library = lazy(() => import('./routes/Library').then((module) => ({ default: module.Library })));
const CatalogueList = lazy(() => import('./routes/CatalogueList').then((module) => ({ default: module.CatalogueList })));
const CatalogueDetail = lazy(() => import('./routes/CatalogueDetail').then((module) => ({ default: module.CatalogueDetail })));
const PacksList = lazy(() => import('./routes/PacksList').then((module) => ({ default: module.PacksList })));
const PackDetail = lazy(() => import('./routes/PackDetail').then((module) => ({ default: module.PackDetail })));
const OnboardingPreview = lazy(() => import('./routes/OnboardingPreview').then((module) => ({ default: module.OnboardingPreview })));
const Sources = lazy(() => import('./routes/Sources').then((module) => ({ default: module.Sources })));
const Destinations = lazy(() => import('./routes/Destinations').then((module) => ({ default: module.Destinations })));
const RoutesPage = lazy(() => import('./routes/RoutesPage').then((module) => ({ default: module.RoutesPage })));
const Operations = lazy(() => import('./routes/Operations').then((module) => ({ default: module.Operations })));
const Exports = lazy(() => import('./routes/Exports').then((module) => ({ default: module.Exports })));

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
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    checkAuthStatus()
      .then((authenticated) => {
        setIsAuthenticated(authenticated);
        setAuthChecked(true);
      })
      .catch(() => {
        setAuthError('Manager is unreachable or returned an invalid authentication response. Check the service/network and retry.');
        setAuthChecked(true);
      });
  }, []);

  useEffect(() => {
    const expired = () => {
      setIsAuthenticated(false);
      setAuthError('Your session expired or is no longer authorized. Sign in again to return to this page.');
      queryClient.clear();
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, expired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, expired);
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
    if (path === '/operations') return <Operations />;
    if (path === '/exports') return <Exports />;
    return <Dashboard />;
  }, [path]);

  const handleLogout = async () => {
    await logout();
    setIsAuthenticated(false);
    queryClient.clear();
  };

  if (!authChecked) return <Center mih="100vh"><Stack align="center"><Loader /><Text>Checking Manager authentication…</Text></Stack></Center>;

  if (!isAuthenticated) {
    return <Login authError={authError} onRetry={() => window.location.reload()} onLogin={() => { setAuthError(null); setIsAuthenticated(true); }} />;
  }

  return <AppLayout path={path} onLogout={handleLogout}><Suspense fallback={<Alert color="blue" title="Loading page"><Loader size="sm" /></Alert>}>{route}</Suspense></AppLayout>;
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
