import { z } from 'zod';

const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');

import { ApiError, apiErrorSchema } from './library';
import { apiFetch } from './client';

const validationSchema = z.object({
  ok: z.boolean().optional(),
  revision: z.number().int().nonnegative().optional(),
  validation_token: z.string().min(1).optional(),
  syntax: z.record(z.string(), z.unknown()).optional(),
  tls: z.record(z.string(), z.unknown()).optional(),
  checked_at: z.string().optional(),
}).passthrough();

const controlSchema = z.object({
  ok: z.boolean().optional(),
  skipped: z.boolean().optional(),
}).passthrough();

const postCheckSchema = z.object({
  docker: z.record(z.string(), z.unknown()).optional(),
  health: z.record(z.string(), z.unknown()).optional(),
  ports: z.record(z.string(), z.unknown()).optional(),
}).passthrough();

export const sourceEntrySchema = z.object({
  name: z.string(),
  filter: z.string(),
  source: z.string(),
  vendor_product: z.string(),
  index: z.string(),
  compliance: z.string(),
  path: z.string(),
  apply_mode: z.string(),
}).passthrough();

export const sourcesResponseSchema = z.object({
  sources: z.array(sourceEntrySchema),
});

export const sourceCatalogResponseSchema = z.object({
  supported_sc4s_version: z.string().optional(),
  sources: z.array(z.object({
    vendor_product: z.string(),
    label: z.string().optional(),
    default_index: z.string().optional(),
    docs_url: z.string().optional(),
    notes: z.string().optional(),
  }).passthrough()),
});

export const onboardSourceResponseSchema = z.object({
  ok: z.boolean(),
  apply_mode: z.string(),
  service: z.record(z.string(), z.unknown()),
  validation: validationSchema,
  control: controlSchema,
  post_check: postCheckSchema.optional(),
  test_instructions: z.record(z.string(), z.string()).optional(),
}).passthrough();

export const deleteSourceResponseSchema = z.object({
  ok: z.boolean(),
  filter: z.string(),
  removed_paths: z.array(z.string()),
  validation: validationSchema,
  apply_mode: z.string(),
}).passthrough();

export const destinationEntrySchema = z.object({
  kind: z.string(),
  id: z.string(),
  url: z.string().nullable().optional(),
  token: z.string().nullable().optional(),
  host: z.string().nullable().optional(),
  port: z.string().nullable().optional(),
  transport: z.string().nullable().optional(),
  mode: z.string().nullable().optional(),
  tls_verify: z.string().nullable().optional(),
  configured: z.boolean().optional(),
}).passthrough();

export const backupsResponseSchema = z.object({
  backups: z.array(z.object({ name: z.string(), path: z.string(), size: z.number(), mtime: z.string() }).passthrough()),
});
export const auditResponseSchema = z.object({ lines: z.array(z.string()) });
export const controlActionResponseSchema = z.object({
  ok: z.boolean(),
  revision: z.number().int().nonnegative(),
  apply_mode: z.string().optional(),
  validation: validationSchema.optional(),
  control: controlSchema.optional(),
  post_check: postCheckSchema.optional(),
  code: z.string().optional(),
  error: z.string().optional(),
}).passthrough();

export const destinationsResponseSchema = z.object({
  supported_sc4s_version: z.string().optional(),
  destinations: z.array(destinationEntrySchema),
});

export const configureDestinationResponseSchema = z.object({
  ok: z.boolean(),
  kind: z.string(),
  id: z.string(),
  apply_mode: z.string(),
  updates: z.record(z.string(), z.string()),
  selector: z.string().nullable().optional(),
  backup: z.string().nullable().optional(),
  validation: validationSchema,
  control: controlSchema,
  post_check: postCheckSchema.optional(),
}).passthrough();

export const deleteDestinationResponseSchema = z.object({
  ok: z.boolean(),
  kind: z.string(),
  id: z.string(),
  removed_env_keys: z.array(z.string()),
  removed_selectors: z.array(z.string()),
  validation: validationSchema,
  apply_mode: z.string(),
}).passthrough();

export const routeEntrySchema = z.object({
  id: z.string(),
  source: z.string(),
  pack: z.string(),
  destination_kind: z.string(),
  destination_id: z.string(),
  selector: z.string().optional(),
  apply_mode: z.string().optional(),
}).passthrough();

export const routesResponseSchema = z.object({
  routes: z.array(routeEntrySchema),
});

export const upsertRouteResponseSchema = z.object({
  ok: z.boolean(),
  route: routeEntrySchema,
  validation: validationSchema,
  control: controlSchema,
  post_check: postCheckSchema.optional(),
}).passthrough();

export const deleteRouteResponseSchema = z.object({
  ok: z.boolean(),
  id: z.string(),
  removed_selectors: z.array(z.string()),
  validation: validationSchema,
  apply_mode: z.string(),
}).passthrough();

export type SourceEntry = z.infer<typeof sourceEntrySchema>;
export type SourcesResponse = z.infer<typeof sourcesResponseSchema>;
export type SourceCatalogResponse = z.infer<typeof sourceCatalogResponseSchema>;
export type OnboardSourceResponse = z.infer<typeof onboardSourceResponseSchema>;
export type DestinationEntry = z.infer<typeof destinationEntrySchema>;
export type DestinationsResponse = z.infer<typeof destinationsResponseSchema>;
export type ConfigureDestinationResponse = z.infer<typeof configureDestinationResponseSchema>;
export type RouteEntry = z.infer<typeof routeEntrySchema>;
export type RoutesResponse = z.infer<typeof routesResponseSchema>;
export type UpsertRouteResponse = z.infer<typeof upsertRouteResponseSchema>;

async function readJsonOrText(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json().catch(() => undefined);
  }
  return response.text().catch(() => undefined);
}

async function parseResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const body = await readJsonOrText(response);
  if (!response.ok) {
    const parsedError = apiErrorSchema.safeParse(body);
    throw new ApiError(
      parsedError.success ? parsedError.data.error : response.statusText || `Request failed with status ${response.status}`,
      response.status,
      parsedError.success ? parsedError.data : undefined,
    );
  }
  return schema.parse(body);
}

async function getJson<T>(path: string, schema: z.ZodType<T>, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(`${API_BASE}${path}`, { signal });
  return parseResponse(response, schema);
}

async function postJson<T>(path: string, payload: Record<string, unknown>, schema: z.ZodType<T>): Promise<T> {
  const response = await apiFetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, schema);
}

export async function listSources(signal?: AbortSignal): Promise<SourcesResponse> {
  return getJson('/sources', sourcesResponseSchema, signal);
}

export async function getSourceCatalog(signal?: AbortSignal): Promise<SourceCatalogResponse> {
  return getJson('/source-catalog', sourceCatalogResponseSchema, signal);
}

export async function onboardSource(payload: {
  name: string;
  source: string;
  vendor_product?: string;
  index?: string;
  compliance?: string;
  apply?: boolean;
}): Promise<OnboardSourceResponse> {
  return postJson('/sources/onboard', payload, onboardSourceResponseSchema);
}

export async function deleteSource(name: string) {
  return postJson('/sources/delete', { name }, deleteSourceResponseSchema);
}

export async function listDestinations(signal?: AbortSignal): Promise<DestinationsResponse> {
  return getJson('/destinations', destinationsResponseSchema, signal);
}

export async function configureDestination(payload: Record<string, unknown>): Promise<ConfigureDestinationResponse> {
  return postJson('/destinations', payload, configureDestinationResponseSchema);
}

export async function deleteDestination(kind: string, id: string) {
  return postJson('/destinations/delete', { kind, id }, deleteDestinationResponseSchema);
}

export async function listRoutes(signal?: AbortSignal): Promise<RoutesResponse> {
  return getJson('/routes', routesResponseSchema, signal);
}

export async function upsertRoute(payload: {
  id: string;
  source: string;
  pack: string;
  destination_kind: string;
  destination_id: string;
  apply?: boolean;
}): Promise<UpsertRouteResponse> {
  return postJson('/routes', payload, upsertRouteResponseSchema);
}

export async function deleteRoute(id: string) {
  return postJson('/routes/delete', { id }, deleteRouteResponseSchema);
}

export async function validateConfiguration(signal?: AbortSignal) {
  return getJson('/validate', validationSchema, signal);
}

export async function runControlAction(action: 'reload' | 'restart', expectedRevision: number, validationToken: string) {
  return postJson(`/${action}`, { expected_revision: expectedRevision, validation_token: validationToken }, controlActionResponseSchema);
}

export async function listBackups(signal?: AbortSignal) {
  return getJson('/backups', backupsResponseSchema, signal);
}

export async function listAudit(signal?: AbortSignal) {
  return getJson('/audit', auditResponseSchema, signal);
}

export function isConfiguredDestination(destination: DestinationEntry): boolean {
  if (destination.configured !== undefined) return destination.configured;
  if (destination.kind === 'hec') return Boolean(destination.url && destination.token);
  return Boolean(destination.host && destination.port);
}
