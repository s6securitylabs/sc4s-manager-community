const rawBaseUrl = import.meta.env.BASE_URL || '/';

export function normalizeBasePath(baseUrl: string): string {
  try {
    const parsed = new URL(baseUrl, 'http://example.test');
    const pathname = parsed.pathname.replace(/^\/+|\/+$/g, '');
    return pathname ? `/${pathname}` : '';
  } catch {
    const pathname = baseUrl.replace(/^\/+|\/+$/g, '');
    return pathname ? `/${pathname}` : '';
  }
}

export const APP_BASE_PATH = normalizeBasePath(rawBaseUrl);

export function normalizeAppPath(path: string): string {
  const withoutHash = path.split('#', 1)[0] || '/';
  const withoutQuery = withoutHash.split('?', 1)[0] || '/';
  const withLeadingSlash = withoutQuery.startsWith('/') ? withoutQuery : `/${withoutQuery}`;
  return `/${withLeadingSlash.replace(/^\/+/, '')}`;
}

export function appPathFromLocation(pathname = window.location.pathname): string {
  if (APP_BASE_PATH && (pathname === APP_BASE_PATH || pathname.startsWith(`${APP_BASE_PATH}/`))) {
    return normalizeAppPath(pathname.slice(APP_BASE_PATH.length) || '/');
  }
  return normalizeAppPath(pathname || '/');
}

export function hrefForAppPath(path: string): string {
  const normalizedPath = normalizeAppPath(path);
  return `${APP_BASE_PATH}${normalizedPath}` || '/';
}

export function safeDecodeURIComponent(value: string): string | null {
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

export function navigateTo(path: string): void {
  const normalizedPath = normalizeAppPath(path);
  window.history.pushState({}, '', hrefForAppPath(normalizedPath));
  window.dispatchEvent(new CustomEvent<string>('sc4s:navigate', { detail: normalizedPath }));
}
