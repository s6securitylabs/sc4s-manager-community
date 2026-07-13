import { z } from 'zod';

const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');

export const apiErrorSchema = z.object({
  error: z.string(),
  code: z.string().optional(),
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

const transportSchema = z.enum(['udp', 'tcp', 'tls']);
const catalogueOriginSchema = z.enum(['sc4s-inbuilt', 'sc4s-inbuilt-lite', 'sechub-resource', 'community-extra']);
const relationshipSchema = z.enum([
  'upstream_only',
  'new_pack',
  'extends_upstream',
  'overrides_upstream',
  'adds_postfilters',
  'adds_reduction_rules',
  'adds_splunk_knowledge',
  'docs_only',
  'deprecated',
]);
const trustLevelSchema = z.enum(['unverified', 'community_submitted', 'trusted_contributor_verified', 's6_verified', 'field_verified']);
const qualityStatusSchema = z.enum(['catalogued', 'draft', 'curated', 'validated', 'field_validated', 'deprecated']);
const reviewStatusSchema = z.enum(['unreviewed', 'reviewed', 'deprecated']);
const sourceStatusSchema = z.string().min(1);

export const catalogueProvenanceSchema = z
  .object({
    origin: z.string().nullable().optional(),
    pack_class: z.string().nullable().optional(),
    source_kind: z.string().nullable().optional(),
    source_status: sourceStatusSchema.nullable().optional(),
    url: z.string().nullable().optional(),
  })
  .passthrough();

export const catalogueCapabilitiesSchema = z
  .object({
    parser: z.boolean(),
    filters: z.boolean(),
    postfilters: z.boolean(),
    log_reduction: z.boolean(),
    splunk_props_transforms: z.boolean(),
    cim_mapping: z.boolean(),
    ocsf_mapping: z.boolean(),
    fixtures: z.boolean(),
    syntax_validated: z.boolean(),
    splunk_ingestion_validated: z.boolean(),
  })
  .passthrough();

export const catalogueArtifactSchema = z
  .object({
    origin: z.string(),
    type: z.string(),
    path: z.string(),
    kind: z.string(),
    contains_secrets: z.boolean(),
  })
  .passthrough();

export const catalogueFeedbackSchema = z
  .object({
    likes: z.number().int().nonnegative(),
    rating_average: z.number().nullable(),
    comments_url: z.string().nullable(),
  })
  .passthrough();

export const listenerSchema = z
  .object({
    source_id: z.string(),
    transport: transportSchema,
    port: z.number().int().min(1).max(65535),
    env: z.record(z.string(), z.unknown()),
  })
  .passthrough();

export const eventFamilySchema = z
  .object({
    id: z.string(),
    label: z.string(),
    match_engine: z.enum(['pcre']),
    match: z.string(),
    expected_sourcetype: z.string(),
    primary_id_field: z.string(),
    required_fields: z.array(z.string()),
    timestamp_fields: z.array(z.string()),
  })
  .passthrough();

export const supportedTransportSchema = z
  .object({
    id: z.string(),
    label: z.string(),
    transport: transportSchema,
    syslog_protocol: z.enum(['rfc5425', 'rfc5424_over_tcp', 'udp_syslog', 'tcp_syslog']),
    framing: z.enum(['octet_counted', 'line_delimited', 'datagram']),
    envelope: z.enum(['ietf_rfc5424', 'bsd_rfc3164_or_headerless', 'none']),
    payload_format: z.enum(['custom_application', 'json', 'cef', 'csv', 'raw']),
    recommended: z.boolean(),
    default_port: z.number().int().min(1).max(65535),
    notes: z.string().optional(),
  })
  .passthrough();

export const sourceLogVersionSchema = z
  .object({
    name: z.unknown(),
    min: z.unknown(),
    max: z.unknown(),
    notes: z.unknown(),
  })
  .passthrough();

export const validationSchema = z
  .object({
    date_validated: z.unknown(),
    validated_by: z.unknown(),
    source_log_version: z.unknown(),
    sc4s_version: z.unknown(),
    splunk_version: z.unknown(),
    evidence: z.unknown(),
  })
  .passthrough();

export const timestampPolicySchema = z
  .object({
    source_time_mode: z.enum([
      'field_utc_epoch',
      'field_with_timezone',
      'field_without_timezone_source_local',
      'syslog_header_timezone',
      'receiver_time',
      'unknown_requires_validation',
    ]),
    primary_field: z.unknown(),
    primary_timezone: z.unknown(),
    fallback_time_mode: z.enum([
      'field_utc_epoch',
      'field_with_timezone',
      'field_without_timezone_source_local',
      'source_local_time_requires_timezone',
      'syslog_header_timezone',
      'receiver_time',
      'unknown_requires_validation',
    ]),
    fallback_timezone: z.unknown(),
    requires_source_timezone_when_fields_missing: z.unknown(),
  })
  .passthrough();

export const testEventSetSchema = z
  .object({
    id: z.string(),
    path: z.string(),
    format: z.enum(['bsd', 'ietf', 'cef', 'csv', 'hybrid', 'raw', 'custom_application']),
    wire_format: z.unknown(),
    event_count: z.number().int().min(1),
    events_per_file: z.enum(['single', 'multiple']),
    event_boundary: z.enum(['line', 'rfc5424_octet_counting', 'delimiter', 'multiline_pattern', 'payload_defined']),
    record_separator: z.unknown(),
    one_event_per_line: z.unknown(),
    multiline: z.unknown(),
    unique_events: z.unknown(),
    marker_tokens: z.unknown(),
    timestamp_policy: timestampPolicySchema,
    field_delimiting: z.unknown(),
    expected_families: z.unknown(),
  })
  .passthrough();

export const exportArtifactSchema = z
  .object({
    id: z.string(),
    group: z.enum(['sc4s', 'splunk', 'test_events', 'scripts', 'docs']),
    source_path: z.string(),
    target_path: z.string(),
    kind: z.unknown(),
    rendered: z.boolean(),
    contains_secrets: z.boolean(),
    required: z.boolean(),
  })
  .passthrough();

export const packSummarySchema = z
  .object({
    schema_version: z.literal('0.1'),
    id: z.string().regex(/^[a-z0-9_][a-z0-9_.-]*$/),
    version: z.string().min(1),
    url: z.string().url(),
    description: z.string().min(1),
    display_name: z.string().min(1),
    vendor: z.string().min(1),
    product: z.string().min(1),
    default_index: z.string().min(1),
    default_source: z.string().min(1),
    listener: listenerSchema,
    sourcetypes: z.record(z.string(), z.string().min(1)),
    event_families: z.array(eventFamilySchema).min(1),
    artifacts: z.record(z.string(), z.unknown()),
    supported_transports: z.array(supportedTransportSchema).min(1),
    recommended_transport: z.string(),
    source_log_version: sourceLogVersionSchema,
    validation: validationSchema,
    test_event_sets: z.array(testEventSetSchema).optional(),
    export_artifacts: z.array(exportArtifactSchema).optional(),
  })
  .passthrough();

export const packDetailSchema = packSummarySchema.extend({
  test_event_sets: z.array(testEventSetSchema),
  export_artifacts: z.array(exportArtifactSchema).min(1),
});

export const catalogueListEntrySchema = z
  .object({
    id: z.string(),
    display_name: z.string(),
    vendor: z.string(),
    product: z.string(),
    origins: z.array(catalogueOriginSchema),
    effective_origin: catalogueOriginSchema,
    relationship_to_upstream: relationshipSchema,
    review_status: reviewStatusSchema.optional(),
    trust_level: trustLevelSchema,
    quality_status: qualityStatusSchema,
    quality_score: z.number().int().min(1).max(5),
    is_verified: z.boolean(),
    capabilities: catalogueCapabilitiesSchema,
    summary: z.string(),
    source_status: sourceStatusSchema.nullable().optional(),
    provenance_url: z.string().nullable().optional(),
    candidate_warnings: z.array(z.string()),
  })
  .passthrough();

export const catalogueFacetItemSchema = z.object({
  value: z.string(),
  label: z.string(),
  count: z.number().int().nonnegative(),
});

export const catalogueFacetsSchema = z
  .object({
    origins: z.array(catalogueFacetItemSchema),
    vendors: z.array(catalogueFacetItemSchema),
    products: z.array(catalogueFacetItemSchema),
    relationships: z.array(catalogueFacetItemSchema),
    review_statuses: z.array(catalogueFacetItemSchema).optional(),
    trust_levels: z.array(catalogueFacetItemSchema),
    quality_statuses: z.array(catalogueFacetItemSchema),
    source_statuses: z.array(catalogueFacetItemSchema),
    artifact_types: z.array(catalogueFacetItemSchema),
    capabilities: z.array(catalogueFacetItemSchema),
    sc4s_versions: z.array(catalogueFacetItemSchema),
  })
  .passthrough();

export const catalogueListResponseSchema = z.object({
  entries: z.array(catalogueListEntrySchema),
  count: z.number().int().nonnegative(),
  limit: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  facets: catalogueFacetsSchema.optional(),
});

export const catalogueDetailSchema = catalogueListEntrySchema.extend({
  provenance: catalogueProvenanceSchema.nullable(),
  upstream: z.record(z.string(), z.unknown()),
  sc4s_manager: z.record(z.string(), z.unknown()).nullable(),
  artifacts: z.array(catalogueArtifactSchema),
  artifact_inventory: z.record(z.string(), z.array(z.string())),
  presets: z.array(z.record(z.string(), z.unknown())),
  field_contract: z.record(z.string(), z.unknown()),
  comparison_to_upstream: z.record(z.string(), z.unknown()),
  validation: z.record(z.string(), z.unknown()),
  known_limitations: z.array(z.string()),
  feedback: catalogueFeedbackSchema,
});

export const packsListResponseSchema = z.object({
  packs: z.array(packSummarySchema),
  count: z.number().int().nonnegative(),
});

export type PackSummary = z.infer<typeof packSummarySchema>;
export type PackDetail = z.infer<typeof packDetailSchema>;
export type PacksListResponse = z.infer<typeof packsListResponseSchema>;
export type CatalogueListEntry = z.infer<typeof catalogueListEntrySchema>;
export type CatalogueFacetItem = z.infer<typeof catalogueFacetItemSchema>;
export type CatalogueFacets = z.infer<typeof catalogueFacetsSchema>;
export type CatalogueDetail = z.infer<typeof catalogueDetailSchema>;
export type CatalogueListResponse = z.infer<typeof catalogueListResponseSchema>;
export type SupportedTransport = z.infer<typeof supportedTransportSchema>;
export type EventFamily = z.infer<typeof eventFamilySchema>;
export type TestEventSet = z.infer<typeof testEventSetSchema>;
export type ExportArtifact = z.infer<typeof exportArtifactSchema>;

export type ExportPackResult = {
  blob: Blob;
  filename: string;
};

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

function decodeHeaderValue(value: string): string | undefined {
  try {
    return decodeURIComponent(value);
  } catch {
    return undefined;
  }
}

export function filenameFromContentDisposition(header: string | null): string | undefined {
  if (!header) return undefined;

  const filenameStar = header.match(/(?:^|;)\s*filename\*=UTF-8''([^;]+)/i);
  if (filenameStar?.[1]) {
    const decoded = decodeHeaderValue(filenameStar[1].trim().replace(/^"|"$/g, ''));
    if (decoded) return decoded;
  }

  const filename = header.match(/(?:^|;)\s*filename=("(?:\\.|[^"])*"|[^;]+)/i);
  if (!filename?.[1]) return undefined;

  return filename[1].trim().replace(/^"|"$/g, '').replace(/\\"/g, '"');
}

async function parseResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const body = await readJsonOrText(response);

  if (!response.ok) {
    throw apiErrorFromResponse(response, body);
  }

  return schema.parse(body);
}

export async function listPacks(signal?: AbortSignal): Promise<PacksListResponse> {
  const response = await fetch(`${API_BASE}/packs`, { signal });
  return parseResponse(response, packsListResponseSchema);
}

export async function listCatalogue(params?: Record<string, string>, signal?: AbortSignal): Promise<CatalogueListResponse> {
  const query = new URLSearchParams(params || {});
  const suffix = query.size ? `?${query.toString()}` : '';
  const response = await fetch(`${API_BASE}/catalogue${suffix}`, { signal });
  return parseResponse(response, catalogueListResponseSchema);
}

export async function getCatalogueEntry(entryId: string, signal?: AbortSignal): Promise<CatalogueDetail> {
  const response = await fetch(`${API_BASE}/catalogue/${encodeURIComponent(entryId)}`, { signal });
  return parseResponse(response, catalogueDetailSchema);
}

export async function getPack(packId: string, signal?: AbortSignal): Promise<PackDetail> {
  const response = await fetch(`${API_BASE}/packs/${encodeURIComponent(packId)}`, { signal });
  return parseResponse(response, packDetailSchema);
}

export async function exportPack(packId: string): Promise<ExportPackResult> {
  const response = await fetch(`${API_BASE}/packs/${encodeURIComponent(packId)}/export`);
  if (!response.ok) {
    throw apiErrorFromResponse(response, await readJsonOrText(response));
  }
  const filename = filenameFromContentDisposition(response.headers.get('content-disposition')) || `${packId}-export.zip`;
  return { blob: await response.blob(), filename };
}
