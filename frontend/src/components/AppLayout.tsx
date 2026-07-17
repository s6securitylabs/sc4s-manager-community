import {
  ActionIcon,
  AppShell,
  Badge,
  Box,
  Burger,
  Divider,
  Group,
  NavLink,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Title,
  Button,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useMemo, useState } from 'react';
import type { ChangeEvent, KeyboardEvent, MouseEvent, ReactNode } from 'react';

import { hrefForAppPath, navigateTo } from '../lib/navigation';

type NavItem = {
  label: string;
  to: string;
  description: string;
  section: 'Operate' | 'Evidence';
};

const navItems: NavItem[] = [
  { label: 'Dashboard', to: '/', description: 'SC4S runtime health, connection status, and a summary of sources, packs, and library sync', section: 'Operate' },
  { label: 'SC4S Library', to: '/library', description: 'Browse Library packs, install SC4S configuration, and view separate product TA links', section: 'Operate' },
  { label: 'Source Catalogue', to: '/catalogue', description: 'Browse SC4S source types. Find the parser for your device and download it.', section: 'Operate' },
  { label: 'Local Packs', to: '/packs', description: 'View installed packs and export config bundles', section: 'Operate' },
  { label: 'Parser Preview', to: '/onboarding-preview', description: 'Paste a sample log event to identify the right SC4S parser before configuring a source', section: 'Operate' },
  { label: 'Sources', to: '/sources', description: 'Map IP addresses and hostnames to SC4S source types', section: 'Operate' },
  { label: 'Destinations', to: '/destinations', description: 'Configure where SC4S sends events — Splunk HEC or syslog', section: 'Operate' },
  { label: 'Routes', to: '/routes', description: 'Send specific source types to specific destinations', section: 'Operate' },
  { label: 'Pending changes', to: '/operations', description: 'Validate staged changes, reload/restart SC4S, and review rollback/audit evidence', section: 'Operate' },
  { label: 'Exports', to: '/exports', description: 'Download config files from a local pack', section: 'Evidence' },
];

const routeSearch = navItems.map((item) => ({
  value: item.to,
  label: item.label.toLowerCase(),
  keywords: `${item.label.toLowerCase()} ${item.description.toLowerCase()} ${item.to.toLowerCase()}`,
}));

function currentRoute(path: string) {
  return navItems.find((item) => (item.to === '/' ? path === '/' : path.startsWith(item.to))) || navItems[0];
}

function RouteSearchInput() {
  const [value, setValue] = useState('');

  const matches = useMemo(() => {
    const query = value.trim().toLowerCase();
    if (!query) return [];
    return routeSearch.filter((item) => item.keywords.includes(query)).slice(0, 1);
  }, [value]);

  const submit = () => {
    const query = value.trim().toLowerCase();
    if (!query) return;
    const match = routeSearch.find((item) => item.keywords.includes(query));
    if (match) {
      navigateTo(match.value);
      setValue('');
    }
  };

  return (
    <TextInput
      aria-label="Quick jump"
      classNames={{ input: 'shell-search-input' }}
      placeholder="Quick jump: dashboard, SC4S Library, source catalogue, sources..."
      size="sm"
      value={value}
      onChange={(event: ChangeEvent<HTMLInputElement>) => setValue(event.currentTarget.value)}
      onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          submit();
        }
      }}
      description={matches[0] ? `Enter → ${matches[0].label}` : 'Searches page names only; no backend data is queried.'}
    />
  );
}

function ColorSchemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const computedColorScheme = useComputedColorScheme('dark', { getInitialValueInEffect: true });
  const next = computedColorScheme === 'dark' ? 'light' : 'dark';
  const label = `Switch to ${next} mode`;

  return (
    <ActionIcon
      aria-label={label}
      title={label}
      variant="light"
      color="cyan"
      size="lg"
      onClick={() => setColorScheme(next)}
    >
      {computedColorScheme === 'dark' ? '☀' : '☾'}
    </ActionIcon>
  );
}

export function AppLayout({ children, path, onLogout }: { children: ReactNode; path: string; onLogout?: () => void }) {
  const [opened, { toggle }] = useDisclosure();
  const sections: Array<'Operate' | 'Evidence'> = ['Operate', 'Evidence'];

  return (
    <AppShell
      className="manager-shell"
      header={{ height: 82 }}
      navbar={{ width: 320, breakpoint: 'md', collapsed: { mobile: !opened } }}
      padding="lg"
    >
      <AppShell.Header className="shell-header">
        <Group h="100%" justify="space-between" px="lg" wrap="nowrap">
          <Group gap="md" wrap="nowrap">
            <Burger opened={opened} onClick={toggle} hiddenFrom="md" size="sm" />
            <Stack gap={2}>
              <Group gap="sm" align="center">
                <Title order={2}>SC4S Manager</Title>
                <Badge variant="light" color="cyan">operator console</Badge>
              </Group>
              <Text size="sm" c="dimmed">
                Operator console for Library source status, local packs, staged source changes, and export evidence.
              </Text>
            </Stack>
          </Group>

          <Group gap="md" align="start" wrap="nowrap" visibleFrom="sm">
            <Box maw={380} miw={300}>
              <RouteSearchInput />
            </Box>
            <ColorSchemeToggle />
            {onLogout && (
              <ActionIcon
                aria-label="Sign out"
                title="Sign out"
                variant="light"
                color="gray"
                size="lg"
                onClick={onLogout}
              >
                ⏻
              </ActionIcon>
            )}
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar className="shell-navbar" p="md">
        <Divider mb="md" />

        <AppShell.Section grow component={ScrollArea} type="never">
          <Stack gap="lg">
            {sections.map((section) => (
              <Stack key={section} gap="xs">
                <Text className="shell-section-label">{section}</Text>
                {navItems
                  .filter((item) => item.section === section)
                  .map((item) => (
                    <NavLink
                      key={item.to}
                      className="shell-nav-link"
                      classNames={{ label: 'shell-nav-label', description: 'shell-nav-description' }}
                      component="a"
                      href={hrefForAppPath(item.to)}
                      label={item.label}
                      description={item.description}
                      active={item.to === '/' ? path === '/' : path.startsWith(item.to)}
                      onClick={(event: MouseEvent<HTMLAnchorElement>) => {
                        event.preventDefault();
                        navigateTo(item.to);
                      }}
                    />
                  ))}
              </Stack>
            ))}
          </Stack>
        </AppShell.Section>

        <AppShell.Section mt="md" hiddenFrom="sm">
          <Stack gap="sm">
            <RouteSearchInput />
            <ColorSchemeToggle />
            {onLogout ? <Button variant="light" color="gray" onClick={onLogout}>Sign out</Button> : null}
          </Stack>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main className="shell-main">
        <Box maw={1440} mx="auto">
          {children}
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}
