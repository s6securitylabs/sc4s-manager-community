const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');

export async function checkAuthStatus(): Promise<boolean> {
  const res = await fetch(`${API_BASE}/auth/status`);
  if (!res.ok) throw new Error(`Authentication status failed: ${res.status}`);
  const data: { authenticated?: boolean } = await res.json();
  if (typeof data.authenticated !== 'boolean') throw new Error('Invalid authentication status response');
  return data.authenticated;
}

export async function login(token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  if (res.status === 401) throw new Error('Invalid token');
  if (res.status === 403) {
    const data: { hint?: string } = await res.json().catch(() => ({}));
    throw new Error(data.hint || 'Standalone login is not configured on this server');
  }
  if (!res.ok) throw new Error('Login failed');
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/logout`, { method: 'POST' }).catch(() => {});
}
