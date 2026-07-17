export type PendingChange = {
  id: string;
  summary: string;
  applyMode: 'reloadable' | 'restart_required';
  stagedAt: string;
};

const KEY = 'sc4s-manager-pending-changes';
export const PENDING_CHANGED_EVENT = 'sc4s:pending-changed';

export function listPendingChanges(): PendingChange[] {
  if (typeof window === 'undefined') return [];
  try {
    const parsed = JSON.parse(window.localStorage.getItem(KEY) || '[]');
    return Array.isArray(parsed) ? parsed.filter((item) => item?.id && item?.summary) : [];
  } catch {
    return [];
  }
}

export function recordPendingChange(change: Omit<PendingChange, 'stagedAt'>): void {
  if (typeof window === 'undefined') return;
  const next = listPendingChanges().filter((item) => item.id !== change.id);
  next.push({ ...change, stagedAt: new Date().toISOString() });
  window.localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event(PENDING_CHANGED_EVENT));
}

export function clearPendingChanges(mode?: PendingChange['applyMode']): void {
  if (typeof window === 'undefined') return;
  const next = mode ? listPendingChanges().filter((item) => item.applyMode !== mode) : [];
  window.localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event(PENDING_CHANGED_EVENT));
}

export function clearPendingChange(id: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(KEY, JSON.stringify(listPendingChanges().filter((item) => item.id !== id)));
  window.dispatchEvent(new Event(PENDING_CHANGED_EVENT));
}
