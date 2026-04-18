// Shared parse-resume retry helper.
//
// /api/onboarding/parse-resume runs a Groq LLM call. With 4 parallel
// Playwright workers hitting parse-resume simultaneously (parse-guards +
// pdf-upload + onboarding suites overlap), the free-tier rate limit is
// easy to trip, and the model occasionally returns non-JSON for thin
// inputs. Both surface as 422/429/5xx. We retry with exponential backoff
// so the suite doesn't flake on free-tier throttling.

import type { APIRequestContext, APIResponse } from '@playwright/test';

// Wider backoff — Groq's free tier occasionally takes 15-30s to reset under
// burst load. Last attempt gives ~50s cumulative which matches real recovery
// windows observed in the concurrency smoke test.
const DELAYS_MS = [1500, 3000, 6000, 12000, 20000];

export async function parseResumeWithRetry(
  request: APIRequestContext,
  payload: { text?: string; multipart?: Record<string, unknown> },
): Promise<APIResponse> {
  let res!: APIResponse;
  for (let attempt = 0; attempt <= DELAYS_MS.length; attempt++) {
    if (payload.text !== undefined) {
      res = await request.post('/api/onboarding/parse-resume', {
        headers: { 'Content-Type': 'application/json' },
        data: { text: payload.text },
      });
    } else if (payload.multipart !== undefined) {
      res = await request.post('/api/onboarding/parse-resume', {
        multipart: payload.multipart as Parameters<APIRequestContext['post']>[1] extends infer O
          ? O extends { multipart?: infer M } ? M : never
          : never,
      });
    }

    if (res.ok()) return res;

    // Only worth retrying on 429 (rate limit) or 5xx (transient) or 422 (LLM bad JSON).
    const s = res.status();
    if (s !== 429 && s < 500 && s !== 422) return res;

    if (attempt < DELAYS_MS.length) {
      await new Promise((r) => setTimeout(r, DELAYS_MS[attempt]));
    }
  }
  return res;
}
