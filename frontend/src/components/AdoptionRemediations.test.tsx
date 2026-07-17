import { MantineProvider } from '@mantine/core';
import { createColumnHelper } from '@tanstack/react-table';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const original = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...original,
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
    useQuery: ({ queryKey }: { queryKey: unknown[] }) => queryKey.join(':') === 'operations:backups'
      ? { isLoading: false, isError: false, data: { backups: [{ name: 'env_file.20260710.bak', path: '/redacted', size: 10, mtime: '2026-07-10T00:00:00Z' }] } }
      : { isLoading: false, isError: false, data: { lines: ['{"action":"reload_sc4s","actor":"operator"}'] } },
  };
});

import { DataTable } from './DataTable';
import { DeleteConfirmation } from './DeleteConfirmation';
import { MutationOutcome } from './MutationOutcome';
import { Operations } from '../routes/Operations';
import { Login } from '../routes/Login';

function render(node: React.ReactNode) {
  return renderToStaticMarkup(<MantineProvider>{node}</MantineProvider>);
}

describe('adoption UX remediations', () => {
  it('renders a keyboard-sortable inventory with a visible search label and aria-sort', () => {
    const columns = [createColumnHelper<{ name: string }>().accessor('name', { header: 'Name' })];
    const markup = render(<DataTable data={[{ name: 'source-a' }]} columns={columns} />);
    expect(markup).toContain('Search inventory');
    expect(markup).toContain('aria-sort="none"');
    expect(markup).toContain('aria-label="Sort by Name"');
    expect(markup).toContain('type="button"');
  });

  it('announces rich staged, validation, control, rollback, and first-ingestion evidence', () => {
    const markup = render(<MutationOutcome title="Source source-a" outcome={{
      ok: true,
      apply_mode: 'reloadable',
      backup: '/backups/source-a.bak',
      validation: { ok: true, checked_at: '2026-07-10T00:00:00Z', syntax: { ok: true, code: 0, stdout: 'syntax ok' }, tls: { ready: true } },
      control: { ok: true, provider: 'narrow-control', stdout: 'reloaded' },
      post_check: { docker: { running: true }, health: { ok: true }, ports: { tcp: { listener_active: true } } },
      test_instructions: { udp: 'logger marker', splunk: 'index=main marker' },
    }} />);
    expect(markup).toContain('role="status"');
    expect(markup).toContain('aria-live="polite"');
    expect(markup).toContain('Saved / staged');
    expect(markup).toContain('Validation evidence');
    expect(markup).toContain('Control action and post-check');
    expect(markup).toContain('Runtime post-check passed');
    expect(markup).toContain('Rollback readiness');
    expect(markup).toContain('First-ingestion source test');
    expect(markup).toContain('Splunk readback');
  });

  it('blocks destructive confirmation when dependent routes exist', () => {
    const markup = render(<DeleteConfirmation objectLabel="destination SIEM" dependents={['route-a']} onCancel={() => {}} onConfirm={() => {}} />);
    expect(markup).toContain('role="alertdialog"');
    expect(markup).toContain('Deletion blocked by dependencies');
    expect(markup).toContain('route-a');
    expect(markup).toContain('disabled');
  });

  it('renders the complete validate/apply/evidence journey and truthful backend limitation', () => {
    const markup = render(<Operations />);
    expect(markup).toContain('Pending changes and operations');
    expect(markup).toContain('Validate staged configuration');
    expect(markup).toContain('Reload SC4S');
    expect(markup).toContain('Restart SC4S');
    expect(markup).toContain('Apply controls stay disabled until validation passes and returns the current server revision');
    expect(markup).toContain('exact server revision returned by validation');
    expect(markup).toContain('do not yet guarantee rollback');
    expect(markup).toContain('Splunk readback');
  });

  it('renders a responsive login outage/session message with retry', () => {
    const markup = render(<Login onLogin={() => {}} authError="Your session expired" onRetry={() => {}} />);
    expect(markup).toContain('width:100%');
    expect(markup).toContain('Your session expired');
    expect(markup).toContain('Retry Manager connection');
  });
});
