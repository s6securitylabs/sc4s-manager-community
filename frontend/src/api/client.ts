export const AUTH_EXPIRED_EVENT = 'sc4s:auth-expired';

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, init);
  if ((response.status === 401 || response.status === 403) && typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT, { detail: { status: response.status } }));
  }
  return response;
}
