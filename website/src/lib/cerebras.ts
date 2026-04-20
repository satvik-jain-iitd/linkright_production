const CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions";
const CEREBRAS_MODEL = "llama3.1-8b";
const CEREBRAS_TIMEOUT_MS = 30_000;

function platformCerebrasKeys(): string[] {
  const keys = [
    process.env.CEREBRAS_API_KEY_1,
    process.env.CEREBRAS_API_KEY_2,
    process.env.CEREBRAS_API_KEY,
  ].filter(Boolean) as string[];
  if (keys.length === 0) throw new Error("CEREBRAS_API_KEY not set (tried CEREBRAS_API_KEY, _1, _2)");
  return keys;
}

export async function cerebrasChat(
  messages: { role: string; content: string }[],
  options: { maxTokens?: number; temperature?: number; model?: string } = {}
): Promise<string> {
  const keys = platformCerebrasKeys();
  const errors: string[] = [];

  for (const key of keys) {
    const resp = await fetch(CEREBRAS_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: options.model ?? CEREBRAS_MODEL,
        messages,
        max_tokens: options.maxTokens ?? 1000,
        temperature: options.temperature ?? 0.3,
      }),
      signal: AbortSignal.timeout(CEREBRAS_TIMEOUT_MS),
    });

    if (resp.status === 429 || resp.status === 503) {
      const err = await resp.text().catch(() => resp.statusText);
      errors.push(`key[...${key.slice(-6)}] ${resp.status}: ${err.slice(0, 80)}`);
      continue;
    }

    if (!resp.ok) {
      const err = await resp.text().catch(() => resp.statusText);
      throw new Error(`Cerebras API error ${resp.status}: ${err}`);
    }

    const data = await resp.json();
    const text = data.choices?.[0]?.message?.content ?? "";
    if (!text) throw new Error("Cerebras returned empty response");
    return text;
  }

  throw new Error(`Cerebras all keys exhausted (429/503). ${errors.join("; ")}`);
}
