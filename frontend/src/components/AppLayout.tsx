import {
  ActionIcon,
  AppShell,
  Badge,
  Box,
  Burger,
  Divider,
  Group,
  NavLink,
  Paper,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Title,
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
  { label: 'Dashboard', to: '/', description: 'Overview of source catalogue, local packs, SC4S Library sync, and Manager connection', section: 'Operate' },
  { label: 'SC4S Library', to: '/library', description: 'Sync configured Library sources and review local import candidates', section: 'Operate' },
  { label: 'Source Catalogue', to: '/catalogue', description: 'Review curated and candidate source coverage', section: 'Operate' },
  { label: 'Local Packs', to: '/packs', description: 'Inspect local packs and export artifacts', section: 'Operate' },
  { label: 'Onboarding Preview', to: '/onboarding-preview', description: 'Paste a sample event to preview parser and pack candidates before configuring a source', section: 'Operate' },
  { label: 'Sources', to: '/sources', description: 'Onboard syslog sources and manage staged source changes', section: 'Operate' },
  { label: 'Destinations', to: '/destinations', description: 'Save staged Splunk HEC and syslog/BSD forwarding targets', section: 'Operate' },
  { label: 'Routes', to: '/routes', description: 'Route staged sources by SC4S vendor_product to destinations', section: 'Operate' },
  { label: 'Exports', to: '/exports', description: 'Download SC4S/Splunk config and evidence artifacts', section: 'Evidence' },
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

export function AppLayout({ children, path }: { children: ReactNode; path: string }) {
  const [opened, { toggle }] = useDisclosure();
  const route = currentRoute(path);
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
            <Paper className="shell-status-card" withBorder p="sm" radius="md">
              <Stack gap={2}>
                <Text size="xs" tt="uppercase" fw={700} c="dimmed">Current route</Text>
                <Text fw={600}>{route.label}</Text>
                <Text size="sm" c="dimmed">{route.description}</Text>
              </Stack>
            </Paper>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar className="shell-navbar" p="md">
        <AppShell.Section>
          <Paper className="cluster-card" withBorder p="md" radius="md">
            <Stack gap={4}>
              <Text size="xs" tt="uppercase" fw={700} c="cyan.6">Control plane</Text>
              <Text fw={700}>SC4S Manager operator workspace</Text>
              <Text size="sm" c="dimmed">
                Keep provenance, validation evidence, and candidate warnings visible.
              </Text>
            </Stack>
          </Paper>
        </AppShell.Section>

        <Divider my="md" />

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
