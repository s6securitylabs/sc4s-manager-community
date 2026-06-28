import { Badge, Group, Paper, Stack, Text } from '@mantine/core';

type ValidationShape = { ok?: boolean } & Record<string, unknown>;
type ControlShape = { ok?: boolean; skipped?: boolean } & Record<string, unknown>;

export type MutationOutcomeData = {
  ok: boolean;
  apply_mode?: string;
  validation?: ValidationShape;
  control?: ControlShape;
};

function controlState(control?: ControlShape): { label: string; color: string } {
  if (!control || control.skipped) return { label: 'Staged only — SC4S not reloaded/restarted', color: 'yellow' };
  if (control.ok) return { label: 'Apply action completed through control daemon', color: 'green' };
  return { label: 'SC4S reload/restart failed', color: 'red' };
}

export function MutationOutcome({ title, outcome }: { title: string; outcome: MutationOutcomeData }) {
  const control = controlState(outcome.control);
  const validationOk = outcome.validation?.ok;
  return (
    <Paper withBorder p="md" radius="md">
      <Stack gap="xs">
        <Group justify="space-between">
          <Text fw={700}>{title}</Text>
          <Badge color={outcome.ok ? 'green' : 'red'} variant="light">{outcome.ok ? 'Change accepted' : 'Change rejected or rolled back'}</Badge>
        </Group>
        <Group gap="xs">
          <Badge color={validationOk ? 'green' : 'red'} variant="light">
            Validation {validationOk ? 'passed' : 'failed'}
          </Badge>
          <Badge color={control.color} variant="light">{control.label}</Badge>
          {outcome.apply_mode ? <Badge color="gray" variant="light">{outcome.apply_mode}</Badge> : null}
        </Group>
        <Text size="sm" c="dimmed">
          Staged changes are not live until validation, SC4S reload/restart through the control daemon, and Splunk readback evidence confirm the result.
        </Text>
      </Stack>
    </Paper>
  );
}
