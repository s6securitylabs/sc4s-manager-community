import { z } from 'zod';
import { apiFetch } from './client';

const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');

export const runtimeListenerSchema = z.object({
  protocol: z.enum(['tcp', 'udp', 'tls']),
  port: z.number().int(),
  desired: z.boolean(),
  live: z.boolean(),
  bind: z.string().optional(),
});

export const runtimeCounterSchema = z.object({
  name: z.string(),
  component: z.enum(['source', 'parser', 'destination', 'unknown']),
  metric: z.string(),
  value: z.number().int().nonnegative(),
});

export const runtimeDestinationSchema = z.object({
  id: z.string(),
  kind: z.string(),
  written: z.number().int().nonnegative(),
  dropped: z.number().int().nonnegative(),
  queued: z.number().int().nonnegative().nullable(),
});

export const runtimeWarningSchema = z.object({
  severity: z.enum(['warning', 'error']),
  code: z.string(),
  message: z.string(),
});

export const runtimeStateSchema = z.object({
  ok: z.boolean(),
  generated_at: z.string(),
  manager: z
    .object({
      version: z.string(),
      health: z.string(),
    })
    .passthrough(),
  control_daemon: z
    .object({
      ok: z.boolean(),
      provider: z.string(),
      error: z.string().optional(),
    })
    .passthrough(),
  sc4s: z
    .object({
      running: z.boolean(),
      status: z.string().nullable().optional(),
      health: z.string().nullable().optional(),
      image: z.string().nullable().optional(),
      image_version: z.string().nullable().optional(),
      supported_version: z.string(),
      version_drift: z.boolean(),
    })
    .passthrough(),
  listeners: z.array(runtimeListenerSchema),
  counters: z.array(runtimeCounterSchema),
  destinations: z.array(runtimeDestinationSchema),
  warnings: z.array(runtimeWarningSchema),
  redaction: z
    .object({
      secrets_present: z.boolean(),
    })
    .passthrough(),
});

export type RuntimeState = z.infer<typeof runtimeStateSchema>;
export type RuntimeListener = z.infer<typeof runtimeListenerSchema>;
export type RuntimeCounter = z.infer<typeof runtimeCounterSchema>;
export type RuntimeDestination = z.infer<typeof runtimeDestinationSchema>;
export type RuntimeWarning = z.infer<typeof runtimeWarningSchema>;

export async function getRuntimeState(signal?: AbortSignal): Promise<RuntimeState> {
  const res = await apiFetch(`${API_BASE}/runtime/state`, { signal });
  if (!res.ok) {
    throw new Error(`Runtime state fetch failed: ${res.status}`);
  }
  const data = await res.json();
  return runtimeStateSchema.parse(data);
}
