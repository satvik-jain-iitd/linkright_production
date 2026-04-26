// Map raw technical error strings to user-readable messages.
//
// Extracted from DashboardContent.tsx where this pattern was originally written.
// Reuse anywhere a backend/API error string would otherwise be shown verbatim
// to the user (rate-limit codes, timeout strings, validation errors, etc.).
//
// Pass a `fallback` to preserve a context-specific generic message — otherwise
// callers get the universal "Something went wrong. Please try again."
//
// Note: DashboardContent.tsx still defines its own copy (it's mid-refactor with
// other in-flight changes); merge it to use this util when those land.

const ERROR_PATTERNS: Array<[RegExp, string]> = [
  [/timed?\s*out/i, "Resume generation timed out. Please try again."],
  [/worker\s*(un)?reachable/i, "Our servers are busy. Please try again in a moment."],
  [/pydantic|validation|parse|schema/i, "The job description couldn't be processed. Try simplifying it."],
  [/rate\s*limit/i, "Too many requests. Please wait a few minutes."],
  [/api[_\s]?key|auth|unauthorized/i, "Service configuration error. Please contact support."],
  [/token|context.*length|too\s*long/i, "The input was too long. Try shortening your job description."],
];

const DEFAULT_FALLBACK = "Something went wrong. Please try again.";

export function friendlyError(
  raw: string | null | undefined,
  fallback: string = DEFAULT_FALLBACK,
): string {
  if (!raw) return fallback;
  for (const [pattern, message] of ERROR_PATTERNS) {
    if (pattern.test(raw)) return message;
  }
  return fallback;
}
