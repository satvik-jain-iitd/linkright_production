// ── Shared LLM call helpers ─────────────────────────────────────────────────
// All OpenAI-compatible providers use the same request shape.
// Only Gemini uses a different format.

export const PROVIDER_URLS: Record<string, string> = {
  groq:        "https://api.groq.com/openai/v1/chat/completions",
  openrouter:  "https://openrouter.ai/api/v1/chat/completions",
  cerebras:    "https://api.cerebras.ai/v1/chat/completions",
  sambanova:   "https://api.sambanova.ai/v1/chat/completions",
  siliconflow: "https://api.siliconflow.cn/v1/chat/completions",
  nvidia:      "https://integrate.api.nvidia.com/v1/chat/completions",
  github:      "https://models.inference.ai.azure.com/chat/completions",
  mistral:     "https://api.mistral.ai/v1/chat/completions",
};

export function buildLlmCall(
  provider: string,
  modelId: string,
  apiKey: string,
  systemPrompt: string,
  userMsg: string,
  maxTokens: number
) {
  if (provider === "gemini") {
    return {
      url: `https://generativelanguage.googleapis.com/v1beta/models/${modelId}:generateContent?key=${apiKey}`,
      headers: { "Content-Type": "application/json" } as Record<string, string>,
      body: JSON.stringify({
        contents: [{ parts: [{ text: `${systemPrompt}\n\n${userMsg}` }] }],
        generationConfig: { temperature: 0.2, maxOutputTokens: maxTokens },
      }),
    };
  }

  const url = PROVIDER_URLS[provider] ?? PROVIDER_URLS.groq;
  return {
    url,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      ...(provider === "openrouter"
        ? { "HTTP-Referer": "https://sync.linkright.in" }
        : {}),
    } as Record<string, string>,
    body: JSON.stringify({
      model: modelId,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userMsg },
      ],
      temperature: 0.2,
      max_tokens: maxTokens,
    }),
  };
}

export function extractLlmText(
  provider: string,
  result: Record<string, unknown>
): string {
  if (provider === "gemini") {
    const candidates = result.candidates as
      | Array<{ content: { parts: Array<{ text: string }> } }>
      | undefined;
    return candidates?.[0]?.content?.parts?.[0]?.text ?? "";
  }
  const choices = result.choices as
    | Array<{ message: { content: string } }>
    | undefined;
  return choices?.[0]?.message?.content ?? "";
}

export function parseJsonResponse<T>(text: string): T | null {
  try {
    // Strip markdown code blocks if present
    const cleaned = text
      .replace(/```(?:json)?\s*/g, "")
      .replace(/```\s*/g, "")
      .trim();
    return JSON.parse(cleaned) as T;
  } catch {
    // Try to find JSON in the text
    const match = text.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        return JSON.parse(match[0]) as T;
      } catch {
        return null;
      }
    }
    return null;
  }
}
