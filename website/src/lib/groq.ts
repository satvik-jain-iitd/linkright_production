const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
// Default model upgraded to 70b: 8b was consistently emitting truncated /
// malformed JSON on complex structured-output tasks (parse-resume, draft
// generation). Callers who want cheaper/faster can override via options.model.
const GROQ_MODEL = "llama-3.3-70b-versatile";
const GROQ_TIMEOUT_MS = 45_000;

function platformKey(): string {
  const key = process.env.PLATFORM_GROQ_API_KEY;
  if (!key) throw new Error("PLATFORM_GROQ_API_KEY is not set");
  return key;
}

/**
 * Makes a Groq chat completion call using the platform key.
 */
export async function groqChat(
  messages: { role: string; content: string }[],
  options: { maxTokens?: number; temperature?: number; model?: string } = {}
): Promise<string> {
  const resp = await fetch(GROQ_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${platformKey()}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: options.model ?? GROQ_MODEL,
      messages,
      max_tokens: options.maxTokens ?? 1000,
      temperature: options.temperature ?? 0.3,
    }),
    signal: AbortSignal.timeout(GROQ_TIMEOUT_MS),
  });

  if (!resp.ok) {
    const err = await resp.text().catch(() => resp.statusText);
    throw new Error(`Groq API error ${resp.status}: ${err}`);
  }

  const data = await resp.json();
  return data.choices?.[0]?.message?.content ?? "";
}
