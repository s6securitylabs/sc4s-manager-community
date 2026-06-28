const META_ERROR_PATTERN = /\b(schema|contract|payload|query|json|parse|typescript|zod|stack|trace|implementation|requirement|prd|adr|mvp|roadmap|api\s*(endpoint|status|base)?|endpoint|http\s+client|curl|debug)\b|\/api\//i;

export function operatorSafeErrorMessage(error: unknown, fallback = 'Manager could not load this operator view. Check the service health and retry.'): string {
  const message = error instanceof Error ? error.message : typeof error === 'string' ? error : '';
  const trimmed = message.trim();
  if (!trimmed) return fallback;
  if (META_ERROR_PATTERN.test(trimmed)) return fallback;
  return trimmed;
}
