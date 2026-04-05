/**
 * In-memory sliding window rate limiter.
 *
 * On Vercel Hobby, serverless functions share a warm container for a short
 * period. This provides reasonable per-user protection during warm reuse.
 * Resets on cold start — the Supabase-based check on /api/resume/start
 * is the authoritative throttle for expensive operations.
 */

const windows = new Map<string, number[]>();

/**
 * Check if a request is within rate limits.
 * @returns true if allowed, false if rate limited
 */
export function rateLimit(
  key: string,
  limit: number,
  windowMs: number = 60_000
): boolean {
  const now = Date.now();
  const timestamps = windows.get(key) || [];

  // Remove expired timestamps
  const valid = timestamps.filter((t) => now - t < windowMs);

  if (valid.length >= limit) {
    windows.set(key, valid);
    return false;
  }

  valid.push(now);
  windows.set(key, valid);
  return true;
}

/** Rate limit response helper */
export function rateLimitResponse(action: string) {
  return Response.json(
    { error: `Rate limit exceeded for ${action}. Please wait and try again.` },
    { status: 429 }
  );
}

// Periodic cleanup to prevent memory leaks (every 60s)
if (typeof globalThis !== "undefined") {
  const cleanup = () => {
    const now = Date.now();
    for (const [key, timestamps] of windows) {
      const valid = timestamps.filter((t) => now - t < 300_000);
      if (valid.length === 0) {
        windows.delete(key);
      } else {
        windows.set(key, valid);
      }
    }
  };
  // Only set interval in Node.js runtime, not edge
  if (typeof setInterval !== "undefined") {
    setInterval(cleanup, 60_000).unref?.();
  }
}
