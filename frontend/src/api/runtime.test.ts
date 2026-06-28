import { describe, expect, it } from 'vitest';
import { runtimeStateSchema } from './runtime';

const validRuntimeState = {
  ok: true,
  generated_at: '2026-06-14T00:00:00Z',
  manager: { version: '0.1.0', health: 'ok' },
  control_daemon: { ok: true, provider: 'unix_socket' },
  sc4s: {
    running: true,
    status: 'running',
    health: 'healthy',
    image: 'ghcr.io/splunk/sc4s:3.43.0',
    image_version: '3.43.0',
    supported_version: '3.43.0',
    version_drift: false,
  },
  listeners: [
    { protocol: 'tcp', port: 514, desired: true, live: true, bind: '0.0.0.0' },
    { protocol: 'udp', port: 514, desired: true, live: true, bind: '0.0.0.0' },
  ],
  counters: [
    { name: 'source.s_DEFAULT', component: 'source', metric: 'processed', value: 1234 },
    { name: 'dst.d_hec_DEFAULT', component: 'destination', metric: 'written', value: 1000 },
  ],
  destinations: [{ id: 'DEFAULT', kind: 'splunk_hec', written: 1000, dropped: 2, queued: null }],
  warnings: [],
  redaction: { secrets_present: false },
};

describe('runtimeStateSchema', () => {
  it('parses a minimal valid runtime state', () => {
    const result = runtimeStateSchema.parse(validRuntimeState);
    expect(result.ok).toBe(true);
    expect(result.sc4s.version_drift).toBe(false);
    expect(result.listeners).toHaveLength(2);
    expect(result.listeners[0].protocol).toBe('tcp');
    expect(result.counters[0].component).toBe('source');
    expect(result.destinations[0].written).toBe(1000);
    expect(result.destinations[0].queued).toBeNull();
  });

  it('parses control daemon failure state with ok=false', () => {
    const data = {
      ...validRuntimeState,
      ok: false,
      control_daemon: { ok: false, provider: 'unix_socket', error: 'socket not found' },
      sc4s: {
        ...validRuntimeState.sc4s,
        running: false,
        status: 'unknown',
        health: null,
        image: null,
        image_version: null,
      },
      warnings: [{ severity: 'error', code: 'control_daemon_failure', message: 'socket not found' }],
    };
    const result = runtimeStateSchema.parse(data);
    expect(result.ok).toBe(false);
    expect(result.control_daemon.ok).toBe(false);
    expect(result.control_daemon.error).toBe('socket not found');
    expect(result.warnings[0].severity).toBe('error');
    expect(result.sc4s.running).toBe(false);
  });

  it('parses version drift warning and flag', () => {
    const data = {
      ...validRuntimeState,
      sc4s: {
        ...validRuntimeState.sc4s,
        image_version: '3.40.0',
        version_drift: true,
      },
      warnings: [
        {
          severity: 'warning',
          code: 'version_drift',
          message: 'Running SC4S 3.40.0 differs from Manager-supported SC4S 3.43.0',
        },
      ],
    };
    const result = runtimeStateSchema.parse(data);
    expect(result.sc4s.version_drift).toBe(true);
    expect(result.warnings[0].code).toBe('version_drift');
    expect(result.warnings[0].severity).toBe('warning');
  });

  it('parses listener_not_live warning', () => {
    const data = {
      ...validRuntimeState,
      listeners: [{ protocol: 'tcp', port: 514, desired: true, live: false, bind: '' }],
      warnings: [
        { severity: 'warning', code: 'listener_not_live', message: 'Desired TCP port 514 has no live listener' },
      ],
    };
    const result = runtimeStateSchema.parse(data);
    expect(result.listeners[0].live).toBe(false);
    expect(result.warnings[0].code).toBe('listener_not_live');
  });

  it('rejects invalid protocol in listeners', () => {
    const data = {
      ...validRuntimeState,
      listeners: [{ protocol: 'sctp', port: 514, desired: true, live: true }],
    };
    expect(() => runtimeStateSchema.parse(data)).toThrow();
  });

  it('rejects invalid severity in warnings', () => {
    const data = {
      ...validRuntimeState,
      warnings: [{ severity: 'info', code: 'something', message: 'fine' }],
    };
    expect(() => runtimeStateSchema.parse(data)).toThrow();
  });

  it('parses redaction secrets_present true', () => {
    const data = { ...validRuntimeState, redaction: { secrets_present: true } };
    const result = runtimeStateSchema.parse(data);
    expect(result.redaction.secrets_present).toBe(true);
  });

  it('accepts extra passthrough fields in sc4s and manager without throwing', () => {
    const data = {
      ...validRuntimeState,
      manager: { version: '0.1.0', health: 'ok', extra_field: 'ignored' },
      sc4s: { ...validRuntimeState.sc4s, restart_count: 2 },
    };
    const result = runtimeStateSchema.parse(data);
    expect(result.manager.version).toBe('0.1.0');
    expect(result.sc4s.running).toBe(true);
  });

  it('accepts null values for nullable sc4s fields', () => {
    const data = {
      ...validRuntimeState,
      sc4s: {
        ...validRuntimeState.sc4s,
        status: null,
        health: null,
        image: null,
        image_version: null,
      },
    };
    const result = runtimeStateSchema.parse(data);
    expect(result.sc4s.status).toBeNull();
    expect(result.sc4s.health).toBeNull();
  });
});
