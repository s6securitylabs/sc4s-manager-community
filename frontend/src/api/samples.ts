import { z } from 'zod';
import { apiFetch } from './client';

import { ApiError, apiErrorSchema } from './packs';

const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');

export const classifyRequestSchema = z.object({
  sample: z.string().min(1),
  source_hint: z.string().optional(),
  transport: z.enum(['udp', 'tcp', 'tls', 'unknown']).optional(),
});

export const classifyResponseSchema = z
  .object({
    ok: z.boolean(),
    format_hints: z.array(z.string()),
    timestamp_hint: z.string().nullable(),
    host_hint: z.string().nullable(),
    redacted_sample_preview: z.string(),
    stored: z.literal(false),
    limitations: z.array(z.string()),
  })
  .passthrough();

export const candidateMatchSchema = z
  .object({
    pack_id: z.string(),
    vendor_product: z.string(),
    reason: z.string(),
    confidence: z.enum(['high', 'medium', 'low']),
    requires_operator_review: z.boolean(),
  })
  .passthrough();

export const expectedMetadataSchema = z
  .object({
    index: z.string().nullable(),
    sourcetype: z.string().nullable(),
    source: z.string().nullable(),
    host: z.string().nullable(),
    timestamp_policy: z.string(),
  })
  .passthrough();

export const previewResponseSchema = z
  .object({
    classification: classifyResponseSchema,
    candidate_matches: z.array(candidateMatchSchema),
    expected_metadata: expectedMetadataSchema,
    next_actions: z.array(z.string()),
    validated: z.literal(false),
  })
  .passthrough();

export type ClassifyRequest = z.infer<typeof classifyRequestSchema>;
export type ClassifyResponse = z.infer<typeof classifyResponseSchema>;
export type CandidateMatch = z.infer<typeof candidateMatchSchema>;
export type ExpectedMetadata = z.infer<typeof expectedMetadataSchema>;
export type PreviewResponse = z.infer<typeof previewResponseSchema>;

async function readJsonOrText(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json().catch(() => undefined);
  }
  return response.text().catch(() => undefined);
}

function apiErrorFromResponse(response: Response, body: unknown): ApiError {
  const parsed = apiErrorSchema.safeParse(body);
  return new ApiError(
    parsed.success ? parsed.data.error : response.statusText || `Request failed with status ${response.status}`,
    response.status,
    parsed.success ? parsed.data : undefined,
  );
}

async function parseResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const body = await readJsonOrText(response);
  if (!response.ok) {
    throw apiErrorFromResponse(response, body);
  }
  return schema.parse(body);
}

export async function classifySample(request: ClassifyRequest, signal?: AbortSignal): Promise<ClassifyResponse> {
  const response = await apiFetch(`${API_BASE}/samples/classify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });
  return parseResponse(response, classifyResponseSchema);
}

export async function previewSample(request: ClassifyRequest, signal?: AbortSignal): Promise<PreviewResponse> {
  const response = await apiFetch(`${API_BASE}/samples/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });
  return parseResponse(response, previewResponseSchema);
}
