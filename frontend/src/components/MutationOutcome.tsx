import { Alert, Badge, Code, Group, List, Paper, SimpleGrid, Stack, Text, Title } from '@mantine/core';

type ValidationShape = {
  ok?: boolean;
  revision?: number;
  validation_token?: string;
  checked_at?: string;
  syntax?: { ok?: boolean; code?: number; stdout?: string; stderr?: string };
  tls?: { ready?: boolean; cert?: { fingerprint?: string; days_remaining?: number } };
} & Record<string, unknown>;
type ControlShape = { ok?: boolean; skipped?: boolean; provider?: string; stdout?: string; stderr?: string; error?: string } & Record<string, unknown>;

export type MutationOutcomeData = {
  ok: boolean;
  apply_mode?: string;
  validation?: ValidationShape;
  control?: ControlShape;
  post_check?: Record<string, unknown>;
  backup?: string | null;
  rolled_back?: boolean;
  removed_paths?: string[];
  removed_selectors?: string[];
  removed_env_keys?: string[];
  test_instructions?: Record<string, string>;
};

function controlState(control?: ControlShape): { label: string; color: string } {
  if (!control || control.skipped) return { label: 'Staged only — SC4S not reloaded/restarted', color: 'yellow' };
  if (control.ok) return { label: 'Control action completed', color: 'green' };
  return { label: 'SC4S control action failed', color: 'red' };
}

function EvidenceCode({ children }: { children?: string }) {
  return children ? <Code block className="muted-code">{children}</Code> : <Text size="sm" c="dimmed">No diagnostic output returned.</Text>;
}

export function MutationOutcome({ title, outcome }: { title: string; outcome: MutationOutcomeData }) {
  const control = controlState(outcome.control);
  const validationOk = outcome.validation?.ok;
  const syntax = outcome.validation?.syntax;
  const tls = outcome.validation?.tls;
  const removed = [...(outcome.removed_paths || []), ...(outcome.removed_selectors || []), ...(outcome.removed_env_keys || [])];
  const postCheck = outcome.post_check;
  const postCheckHealth = postCheck?.health as { ok?: boolean } | undefined;
  const postCheckDocker = postCheck?.docker as { running?: boolean; ok?: boolean } | undefined;
  const postCheckPassed = Boolean(postCheck) && postCheckHealth?.ok !== false && postCheckDocker?.running !== false && postCheckDocker?.ok !== false;
  return (
    <Paper withBorder p="md" radius="md" role={outcome.ok ? 'status' : 'alert'} aria-live="polite" aria-atomic="true">
      <Stack gap="md">
        <Group justify="space-between">
          <Text fw={700}>{title}</Text>
          <Badge color={outcome.ok ? 'green' : 'red'} variant="light">{outcome.ok ? 'Change accepted' : 'Change rejected or rollback required'}</Badge>
        </Group>
        <Alert color="blue" title="State boundary">
          Saved/staged is not live. Validation checks Manager/SC4S syntax and TLS prerequisites; it is not Splunk proof. Live proof requires the control action, runtime post-check, marker event, and Splunk readback.
        </Alert>
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          <Stack gap="xs">
            <Title order={4}>1. Saved / staged</Title>
            <Badge color={outcome.ok ? 'green' : 'red'} variant="light">{outcome.ok ? 'Configuration written' : 'Write not accepted'}</Badge>
            {outcome.apply_mode ? <Text size="sm">Required apply mode: <Code>{outcome.apply_mode}</Code></Text> : null}
            {removed.length ? <List size="sm">{removed.map((item) => <List.Item key={item}><Code>{item}</Code></List.Item>)}</List> : null}
          </Stack>
          <Stack gap="xs">
            <Title order={4}>2. Validation evidence</Title>
            <Badge color={validationOk ? 'green' : 'red'} variant="light">Validation {validationOk ? 'passed' : 'failed'}</Badge>
            {outcome.validation?.checked_at ? <Text size="sm">Checked: {outcome.validation.checked_at}</Text> : null}
            {syntax ? <Text size="sm">Syntax: {syntax.ok ? 'passed' : 'failed'}{syntax.code !== undefined ? ` (exit ${syntax.code})` : ''}</Text> : null}
            <EvidenceCode>{syntax?.stderr || syntax?.stdout}</EvidenceCode>
            {tls ? <Text size="sm">TLS readiness: {tls.ready ? 'ready' : 'not ready or not configured'}</Text> : null}
          </Stack>
          <Stack gap="xs">
            <Title order={4}>3. Control action and post-check</Title>
            <Badge color={control.color} variant="light">{control.label}</Badge>
            {outcome.control?.provider ? <Text size="sm">Provider: {outcome.control.provider}</Text> : null}
            <EvidenceCode>{outcome.control?.stderr || outcome.control?.error || outcome.control?.stdout}</EvidenceCode>
            <Badge color={postCheckPassed ? 'green' : 'yellow'} variant="light">{postCheckPassed ? 'Runtime post-check passed' : 'No successful runtime post-check returned'}</Badge>
            {postCheck ? <EvidenceCode>{JSON.stringify(postCheck, null, 2)}</EvidenceCode> : null}
            <Text size="sm" c="dimmed">A successful reload/restart is control evidence only. Confirm listeners/counters on Dashboard and perform Splunk readback.</Text>
          </Stack>
          <Stack gap="xs">
            <Title order={4}>4. Rollback readiness</Title>
            {outcome.backup ? <Text size="sm">Backup handle: <Code>{outcome.backup}</Code></Text> : <Text size="sm" c="dimmed">No backup handle was returned by this endpoint.</Text>}
            {outcome.rolled_back !== undefined ? <Badge color={outcome.rolled_back ? 'yellow' : 'gray'}>{outcome.rolled_back ? 'Prior state restored' : 'No rollback reported'}</Badge> : null}
          </Stack>
        </SimpleGrid>
        {outcome.test_instructions ? (
          <Stack gap="xs">
            <Title order={4}>5. First-ingestion source test</Title>
            <Text size="sm">Run one transport command, then use the Splunk query. Replace placeholders; commands do not prove delivery until readback succeeds.</Text>
            {Object.entries(outcome.test_instructions).map(([kind, command]) => (
              <div key={kind}><Text size="xs" fw={700}>{kind.toUpperCase()}</Text><EvidenceCode>{command}</EvidenceCode></div>
            ))}
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}
