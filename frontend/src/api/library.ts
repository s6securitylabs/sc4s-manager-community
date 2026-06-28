import { z } from 'zod';

const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');

export const apiErrorSchema = z.object({
  error: z.string(),
  code: z.string().optional(),
  next_action: z.string().optional(),
  details: z.unknown().optional(),
});

export type ApiErrorBody = z.infer<typeof apiErrorSchema>;

export class ApiError extends Error {
  status: number;
  body?: ApiErrorBody;

  constructor(message: string, status: number, body?: ApiErrorBody) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

const librarySourceSchema = z.object({
  source_id: z.string(),
  enabled: z.boolean().optional(),
  catalogue_url: z.string().url().optional(),
  manifest_url: z.string().url().optional(),
  last_sync: z.string().optional(),
  entry_count: z.number().int().nonnegative().optional(),
  manifest_download_count: z.number().int().nonnegative().optional(),
}).passthrough();

const libraryHealthCheckSchema = z.object({
  name: z.string(),
  url: z.string().optional(),
  ok: z.boolean(),
  error_code: z.string().optional(),
  message: z.string().optional(),
  next_action: z.string().optional(),
  elapsed_ms: z.number().int().nonnegative().optional(),
  content_type: z.string().optional(),
  size_bytes: z.number().int().nonnegative().optional(),
  sha256: z.string().optional(),
}).passthrough();

export const librarySourceHealthResponseSchema = z.object({
  source_id: z.string(),
  checked_at: z.string(),
  overall_ok: z.boolean(),
  checks: z.array(libraryHealthCheckSchema),
  catalogue: z.object({ entry_count: z.number().int().nonnegative() }).passthrough(),
  manifest: z.object({ download_count: z.number().int().nonnegative() }).passthrough(),
  sample_entry: z.object({ ok: z.boolean(), id: z.string().nullable().optional() }).passthrough(),
  sample_bundle: libraryHealthCheckSchema.or(z.object({ ok: z.boolean() }).passthrough()),
  trust_semantics: z.object({
    remote_labels_are_advisory: z.boolean(),
    local_verification_requires_local_validation_json: z.boolean(),
    remote_metadata_can_set_local_is_verified: z.boolean(),
  }).passthrough(),
}).passthrough();

const libraryCatalogueEntrySchema = z.object({
  id: z.string(),
  display_name: z.string().optional(),
  vendor: z.string().optional(),
  product: z.string().optional(),
  version: z.string().optional(),
  download_available: z.boolean().optional(),
  source_id: z.string().optional(),
  source_type: z.string().optional(),
  is_remote: z.boolean().optional(),
}).passthrough();

const libraryEligibilitySchema = z.object({
  download_available: z.boolean(),
  runtime_candidate_count: z.number().int().nonnegative(),
}).passthrough();

const libraryDownloadSchema = z.object({
  filename: z.string(),
  sha256: z.string().optional(),
  expected_sha256: z.string().optional(),
  path: z.string().optional(),
  url: z.string().optional(),
  size_bytes: z.number().int().nonnegative().optional(),
}).passthrough();

const libraryVerificationSchema = z.object({
  zip_sha256: z.string().optional(),
  manifest_verified: z.boolean().optional(),
  artifact_count: z.number().int().nonnegative().optional(),
}).passthrough();

const libraryArtifactSchema = z.object({
  source_path: z.string(),
  target_path: z.string(),
  sha256: z.string().optional(),
  kind: z.string().optional(),
  size: z.number().int().nonnegative().optional(),
  bundle_path: z.string().optional(),
}).passthrough();

const libraryImportRecordSchema = z.object({
  import_id: z.string(),
  source_id: z.string(),
  entry_id: z.string(),
  created_at: z.string().optional(),
  apply_allowed: z.boolean(),
  reference_only: z.boolean(),
  runtime_files: z.array(libraryArtifactSchema).optional(),
  reference_files: z.array(libraryArtifactSchema).optional(),
  download: libraryDownloadSchema.optional(),
  detail: z.record(z.unknown()).optional(),
  last_apply: z.record(z.unknown()).optional(),
}).passthrough();

export const librarySourcesResponseSchema = z.object({
  sources: z.array(librarySourceSchema),
});

export const libraryCatalogueResponseSchema = z.object({
  source_id: z.string(),
  source: z.record(z.unknown()).optional(),
  entries: z.array(libraryCatalogueEntrySchema),
  filters: z.record(z.string()),
});

export const libraryEntryResponseSchema = z.object({
  source_id: z.string(),
  entry: z.record(z.unknown()),
  refresh: z.boolean(),
  eligibility: libraryEligibilitySchema,
});

export const libraryDownloadResponseSchema = z.object({
  ok: z.boolean(),
  source_id: z.string(),
  entry_id: z.string(),
  detail: z.record(z.unknown()),
  download: libraryDownloadSchema,
  verification: libraryVerificationSchema,
});

export const libraryValidateResponseSchema = z.object({
  ok: z.boolean(),
  import_id: z.string(),
  source_id: z.string(),
  entry_id: z.string(),
  apply_allowed: z.boolean(),
  reference_only: z.boolean(),
  runtime_files: z.array(libraryArtifactSchema),
  reference_files: z.array(libraryArtifactSchema),
  verification: libraryVerificationSchema,
}).passthrough();

export const libraryImportsResponseSchema = z.object({
  imports: z.array(libraryImportRecordSchema),
});

export const libraryApplyResponseSchema = z.object({
  ok: z.boolean(),
  import_id: z.string(),
  apply: z.boolean(),
  apply_allowed: z.boolean(),
  changed_targets: z.array(z.string()),
  validation: z.record(z.unknown()),
  control: z.record(z.unknown()),
  post_check: z.record(z.unknown()),
  rolled_back: z.boolean(),
  reference_only: z.boolean().optional(),
}).passthrough();

export const librarySyncResponseSchema = z.object({
  ok: z.boolean().optional(),
  source_id: z.string(),
  entry_count: z.number().int().optional(),
  manifest_download_count: z.number().int().optional(),
  last_sync: z.string().optional(),
}).passthrough();

export type LibrarySourcesResponse = z.infer<typeof librarySourcesResponseSchema>;
export type LibraryCatalogueResponse = z.infer<typeof libraryCatalogueResponseSchema>;
export type LibraryEntryResponse = z.infer<typeof libraryEntryResponseSchema>;
export type LibraryDownloadResponse = z.infer<typeof libraryDownloadResponseSchema>;
export type LibraryValidateResponse = z.infer<typeof libraryValidateResponseSchema>;
export type LibraryImportsResponse = z.infer<typeof libraryImportsResponseSchema>;
export type LibraryApplyResponse = z.infer<typeof libraryApplyResponseSchema>;
export type LibrarySyncResponse = z.infer<typeof librarySyncResponseSchema>;
export type LibrarySourceHealthResponse = z.infer<typeof librarySourceHealthResponseSchema>;
export type LibraryCatalogueEntry = z.infer<typeof libraryCatalogueEntrySchema>;
export type LibraryImportRecord = z.infer<typeof libraryImportRecordSchema>;

function fallbackErrorMessage(response: Response): string {
  return response.statusText || `Request failed with status ${response.status}`;
}

async function readJsonOrText(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json().catch(() => undefined);
  }
  return response.text().catch(() => undefined);
}

function apiErrorFromResponse(response: Response, body: unknown): ApiError {
  const parsedError = apiErrorSchema.safeParse(body);
  return new ApiError(parsedError.success ? parsedError.data.error : fallbackErrorMessage(response), response.status, parsedError.success ? parsedError.data : undefined);
}

async function parseResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const body = await readJsonOrText(response);
  if (!response.ok) {
    throw apiErrorFromResponse(response, body);
  }
  return schema.parse(body);
}

async function postJson<T>(path: string, payload: Record<string, unknown>, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, schema);
}

export async function listLibrarySources(signal?: AbortSignal): Promise<LibrarySourcesResponse> {
  const response = await fetch(`${API_BASE}/library/sources`, { signal });
  return parseResponse(response, librarySourcesResponseSchema);
}

export async function getLibrarySourceHealth(sourceId: string, signal?: AbortSignal): Promise<LibrarySourceHealthResponse> {
  const query = new URLSearchParams({ source_id: sourceId || 'official' });
  const response = await fetch(`${API_BASE}/library/source-health?${query.toString()}`, { signal });
  return parseResponse(response, librarySourceHealthResponseSchema);
}

export async function listLibraryCatalogue(params?: Record<string, string>, signal?: AbortSignal): Promise<LibraryCatalogueResponse> {
  const query = new URLSearchParams(params || {});
  const suffix = query.size ? `?${query.toString()}` : '';
  const response = await fetch(`${API_BASE}/library/catalogue${suffix}`, { signal });
  return parseResponse(response, libraryCatalogueResponseSchema);
}

export async function getLibraryEntry(sourceId: string, entryId: string, refresh = false, signal?: AbortSignal): Promise<LibraryEntryResponse> {
  const query = new URLSearchParams({ source_id: sourceId, entry_id: entryId });
  if (refresh) query.set('refresh', 'yes');
  const response = await fetch(`${API_BASE}/library/entry?${query.toString()}`, { signal });
  return parseResponse(response, libraryEntryResponseSchema);
}

export async function listLibraryImports(signal?: AbortSignal): Promise<LibraryImportsResponse> {
  const response = await fetch(`${API_BASE}/library/imports`, { signal });
  return parseResponse(response, libraryImportsResponseSchema);
}

export async function syncLibrarySource(sourceId: string): Promise<LibrarySyncResponse> {
  return postJson('/library/sync', { source_id: sourceId }, librarySyncResponseSchema);
}

export async function downloadLibraryBundle(sourceId: string, entryId: string): Promise<LibraryDownloadResponse> {
  return postJson('/library/download', { source_id: sourceId, entry_id: entryId }, libraryDownloadResponseSchema);
}

export async function validateLibraryImport(sourceId: string, entryId: string): Promise<LibraryValidateResponse> {
  return postJson('/library/import/validate', { source_id: sourceId, entry_id: entryId }, libraryValidateResponseSchema);
}

export async function applyLibraryImport(importId: string, apply = true): Promise<LibraryApplyResponse> {
  return postJson('/library/import/apply', { import_id: importId, apply }, libraryApplyResponseSchema);
}
