import { Langfuse } from "langfuse";

let _client: Langfuse | null = null;

function getClient(): Langfuse | null {
  if (_client) return _client;
  const publicKey = process.env.LANGFUSE_PUBLIC_KEY;
  const secretKey = process.env.LANGFUSE_SECRET_KEY;
  const baseUrl = process.env.LANGFUSE_BASE_URL ?? "https://us.cloud.langfuse.com";
  if (!publicKey || !secretKey) return null;
  _client = new Langfuse({ publicKey, secretKey, baseUrl });
  return _client;
}

// Cache: promptName → { text, expiresAt }
const cache = new Map<string, { text: string; expiresAt: number }>();
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Fetch a prompt by name from Langfuse. Falls back to `fallback` on any error.
 * Prompts are cached for 5 minutes to avoid per-request latency.
 *
 * Register new prompts in Langfuse dashboard at us.cloud.langfuse.com → Prompts.
 */
export async function getPrompt(name: string, fallback: string): Promise<string> {
  const now = Date.now();
  const cached = cache.get(name);
  if (cached && cached.expiresAt > now) return cached.text;

  const client = getClient();
  if (!client) return fallback;

  try {
    const prompt = await client.getPrompt(name);
    const text = prompt.prompt as string;
    if (!text) return fallback;
    cache.set(name, { text, expiresAt: now + CACHE_TTL_MS });
    return text;
  } catch (err) {
    console.warn(`[langfuse-prompts] Failed to fetch "${name}":`, err instanceof Error ? err.message : err);
    return fallback;
  }
}
