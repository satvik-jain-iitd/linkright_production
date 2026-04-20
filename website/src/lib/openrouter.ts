const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";
// Free-tier small model — fast, no cost, good for structured JSON tasks.
const OPENROUTER_MODEL_STRUCTURED = "meta-llama/llama-3.1-8b-instruct:free";
// Reasoning model — higher context, better for complex tasks.
const OPENROUTER_MODEL_REASONING = "google/gemini-2.5-flash-preview:thinking";
const OPENROUTER_TIMEOUT_MS = 45_000;

function platformOpenRouterKeys(): string[] {
  const keys = [
    process.env.OPENROUTER_API_KEY_1,
    process.env.OPENROUTER_API_KEY_2,
    process.env.OPENROUTER_API_KEY_3,
    process.env.OPENROUTER_API_KEY_4,
    process.env.OPENROUTER_API_KEY,
  ].filter(Boolean) as string[];
  if (keys.length === 0) throw new Error("OPENROUTER_API_KEY not set (tried OPENROUTER_API_KEY, _1-_4)");
  return keys;
}

export async function openrouterChat(
  messages: { role: string; content: string }[],
  options: { maxTokens?: number; temperature?: number; model?: string; taskType?: "structured" | "reasoning" } = {}
): Promise<string> {
  const defaultModel =
    options.taskType === "reasoning" ? OPENROUTER_MODEL_REASONING : OPENROUTER_MODEL_STRUCTURED;
  const model = options.model ?? defaultModel;

  const keys = platformOpenRouterKeys();
  const errors: string[] = [];

  for (const key of keys) {
    const resp = await fetch(OPENROUTER_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://sync.linkright.in",
        "X-Title": "LinkRight",
      },
      body: JSON.stringify({
        model,
        messages,
        max_tokens: options.maxTokens ?? 1000,
        temperature: options.temperature ?? 0.3,
      }),
      signal: AbortSignal.timeout(OPENROUTER_TIMEOUT_MS),
    });

    if (resp.status === 429 || resp.status === 503) {
      const err = await resp.text().catch(() => resp.statusText);
      errors.push(`key[...${key.slice(-6)}] ${resp.status}: ${err.slice(0, 80)}`);
      continue;
    }

    if (!resp.ok) {
      const err = await resp.text().catch(() => resp.statusText);
      throw new Error(`OpenRouter API error ${resp.status}: ${err}`);
    }

    const data = await resp.json();
    const text = data.choices?.[0]?.message?.content ?? "";
    if (!text) throw new Error("OpenRouter returned empty response");
    return text;
  }

  throw new Error(`OpenRouter all keys exhausted (429/503). ${errors.join("; ")}`);
}
