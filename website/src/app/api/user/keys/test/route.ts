// [BYOK-REMOVED] Supabase + rate-limit imports no longer needed
// import { createClient } from "@/lib/supabase/server";
// import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

/* [BYOK-REMOVED]
// Base URLs for all supported providers (OpenAI-compatible)
const PROVIDER_URLS: Record<string, string> = {
  groq:        "https://api.groq.com/openai/v1/chat/completions",
  openrouter:  "https://openrouter.ai/api/v1/chat/completions",
  cerebras:    "https://api.cerebras.ai/v1/chat/completions",
  sambanova:   "https://api.sambanova.ai/v1/chat/completions",
  siliconflow: "https://api.siliconflow.cn/v1/chat/completions",
  nvidia:      "https://integrate.api.nvidia.com/v1/chat/completions",
  github:      "https://models.inference.ai.azure.com/chat/completions",
  mistral:     "https://api.mistral.ai/v1/chat/completions",
};

// Default tiny model per provider for validation
const PROVIDER_TEST_MODELS: Record<string, string> = {
  groq:        "llama-3.1-8b-instant",
  openrouter:  "meta-llama/llama-3.2-3b-instruct:free",
  cerebras:    "llama3.1-8b",
  sambanova:   "Meta-Llama-3.1-8B-Instruct",
  siliconflow: "Qwen/Qwen2.5-7B-Instruct",
  nvidia:      "meta/llama-3.2-1b-instruct",
  github:      "Phi-3.5-mini-instruct",
  mistral:     "ministral-3b-2512",
};
*/

export async function POST() {
  // [BYOK-REMOVED] API key testing disabled — server manages keys
  /* [BYOK-REMOVED]
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`keys-test:${user.id}`, 10)) {
    return rateLimitResponse("key test");
  }

  const { provider, api_key, model_id } = await request.json();

  if (!provider || !api_key) {
    return Response.json({ error: "provider and api_key required" }, { status: 400 });
  }

  const start = Date.now();

  // Gemini uses different API format
  if (provider === "gemini") {
    const model = model_id || "gemini-1.5-flash-8b";
    try {
      const resp = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${api_key}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [{ parts: [{ text: "hi" }] }],
            generationConfig: { maxOutputTokens: 1 },
          }),
          signal: AbortSignal.timeout(10_000),
        }
      );
      const latency_ms = Date.now() - start;
      if (resp.status === 200) return Response.json({ valid: true, status: "ok", latency_ms });
      if (resp.status === 429) return Response.json({ valid: true, status: "rate_limited", latency_ms });
      if (resp.status === 400) {
        // 400 from Gemini often means key is valid but model name wrong — treat as ok
        return Response.json({ valid: true, status: "ok", latency_ms });
      }
      return Response.json({ valid: false, status: "invalid_key", latency_ms });
    } catch {
      return Response.json({ valid: false, status: "network_error", latency_ms: Date.now() - start });
    }
  }

  // Jina (embedding, not chat)
  if (provider === "jina") {
    try {
      const resp = await fetch("https://api.jina.ai/v1/embeddings", {
        method: "POST",
        headers: { "Authorization": `Bearer ${api_key}`, "Content-Type": "application/json" },
        body: JSON.stringify({ model: "jina-embeddings-v3", input: ["test"], dimensions: 768 }),
        signal: AbortSignal.timeout(10_000),
      });
      const latency_ms = Date.now() - start;
      if (resp.status === 200) return Response.json({ valid: true, status: "ok", latency_ms });
      if (resp.status === 429) return Response.json({ valid: true, status: "rate_limited", latency_ms });
      return Response.json({ valid: false, status: "invalid_key", latency_ms });
    } catch {
      return Response.json({ valid: false, status: "network_error", latency_ms: Date.now() - start });
    }
  }

  // All OpenAI-compatible providers
  const url = PROVIDER_URLS[provider];
  if (!url) return Response.json({ error: `Unknown provider: ${provider}` }, { status: 400 });

  const model = model_id || PROVIDER_TEST_MODELS[provider] || "llama-3.1-8b-instant";

  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${api_key}`,
    };
    if (provider === "openrouter") {
      headers["HTTP-Referer"] = "https://linkright.in";
    }

    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: "hi" }],
        max_tokens: 1,
      }),
      signal: AbortSignal.timeout(15_000),
    });

    const latency_ms = Date.now() - start;

    if (resp.status === 200) return Response.json({ valid: true, status: "ok", latency_ms });
    if (resp.status === 429) return Response.json({ valid: true, status: "rate_limited", latency_ms });
    if (resp.status === 401 || resp.status === 403) return Response.json({ valid: false, status: "invalid_key", latency_ms });
    // Some providers return 400 for bad model but valid key
    if (resp.status === 400) return Response.json({ valid: true, status: "ok", latency_ms });

    return Response.json({ valid: false, status: "error", latency_ms });
  } catch {
    return Response.json({ valid: false, status: "network_error", latency_ms: Date.now() - start });
  }
  */
  return Response.json({ valid: false, message: "API key management is handled server-side" }, { status: 410 });
}
