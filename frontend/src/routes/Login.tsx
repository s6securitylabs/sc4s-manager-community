import {
  Alert,
  Box,
  Button,
  Center,
  Group,
  Paper,
  PasswordInput,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useState } from 'react';

import { login } from '../api/auth';

interface LoginProps {
  onLogin: () => void;
}

export function Login({ onLogin }: LoginProps) {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) return;
    setLoading(true);
    setError('');
    try {
      await login(token.trim());
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Center mih="100vh" bg="var(--mantine-color-body)">
      <Box w={400}>
        <Stack gap="lg">
          <Stack gap={4}>
            <Title order={2}>SC4S Manager</Title>
            <Text c="dimmed" size="sm">Enter your access token to continue</Text>
          </Stack>

          <Paper withBorder p="xl" radius="lg">
            <form onSubmit={handleSubmit}>
              <Stack gap="md">
                <PasswordInput
                  label="Access token"
                  placeholder="Paste your SC4S_MANAGER_MANUAL_LOGIN_TOKEN"
                  value={token}
                  onChange={(e) => setToken(e.currentTarget.value)}
                  autoFocus
                />

                {error && (
                  <Alert color="red" title="Sign in failed">
                    {error}
                  </Alert>
                )}

                <Group justify="flex-end">
                  <Button type="submit" loading={loading} disabled={!token.trim()}>
                    Sign in
                  </Button>
                </Group>
              </Stack>
            </form>
          </Paper>

          <Text c="dimmed" size="xs">
            Set <Text component="span" ff="monospace" size="xs">SC4S_MANAGER_MANUAL_LOGIN_TOKEN</Text> in{' '}
            <Text component="span" ff="monospace" size="xs">manager.env</Text> to enable standalone login.
            If you are accessing this through a reverse proxy, ensure your proxy is forwarding the correct trust header.
          </Text>
        </Stack>
      </Box>
    </Center>
  );
}
