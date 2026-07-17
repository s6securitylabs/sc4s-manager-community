import { Alert, Button, Group, Paper, Stack, Text, Title } from '@mantine/core';

export function DeleteConfirmation({
  objectLabel,
  dependents = [],
  busy,
  onCancel,
  onConfirm,
}: {
  objectLabel: string;
  dependents?: string[];
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const blocked = dependents.length > 0;
  return (
    <Paper role="alertdialog" aria-modal="true" aria-labelledby="delete-confirm-title" withBorder p="md">
      <Stack gap="sm">
        <Title id="delete-confirm-title" order={4}>Confirm deletion of {objectLabel}</Title>
        <Text size="sm">This removes saved/staged configuration only. It is not live until the required validate and apply action completes.</Text>
        {blocked ? (
          <Alert color="red" title="Deletion blocked by dependencies">
            Remove these routes first: {dependents.join(', ')}. SC4S Manager will not silently cascade this deletion.
          </Alert>
        ) : (
          <Alert color="yellow" title="Rollback evidence required">
            Review the returned backup, removed paths, and validation evidence after deletion, then apply and complete a runtime/Splunk post-check.
          </Alert>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onCancel}>Cancel</Button>
          <Button color="red" loading={busy} disabled={blocked} onClick={onConfirm}>Delete staged configuration</Button>
        </Group>
      </Stack>
    </Paper>
  );
}
