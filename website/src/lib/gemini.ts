// Platform LLM router — multi-provider fallback chain.
//
// Structured tasks (default): Groq 8b → Cerebras 8b → Gemini → OpenRouter → Oracle
// Reasoning tasks (taskType:"reasoning"): Gemini → Groq 70b → OpenRouter → Oracle
//
// Pass taskType:"reasoning" when the task needs deep analysis, high context,
// or complex multi-step output (e.g. nugget extraction, career narration).
// Default (structured) is optimised for fast, cheap JSON extraction.

import { groqChat } from "./groq";
import { cerebrasChat } from "./cerebras";
import { openrouterChat } from "./openrouter";
import { oracleChat } from "./oracle-ollama";

const GEMINI_MODEL = "gemini-2.5-flash-lite";
const GEMINI_MODEL_REASONING = "gemini-2.5-flash";
const GEMINI_TIMEOUT_MS = 45_000;

function platformGeminiKeys(): string[] {
  const keys = [
    process.env.GEMINI_API_KEY_1,
    process.env.GEMINI_API_KEY_2,
    process.env.GEMINI_API_KEY_3,
    process.env.GEMINI_API_KEY,
  ].filter(Boolean) as string[];
  return keys;
}

export async function geminiChat(
  messages: { role: string; content: string }[],
  options: { maxTokens?: number; temperature?: number; model?: string } = {}
): Promise<string> {
  const model = options.model ?? GEMINI_MODEL;
  const systemMsg = messages.find((m) => m.role === "system")?.content ?? "";
  const userMsg = messages
    .filter((m) => m.role !== "system")
    .map((m) => m.content)
    .join("\n\n");
  const prompt = systemMsg ? `${systemMsg}\n\n${userMsg}` : userMsg;

  const keys = platformGeminiKeys();
  if (keys.length === 0) throw new Error("GEMINI_API_KEY not set (tried GEMINI_API_KEY, _1, _2, _3)");
  const errors: string[] = [];

  for (const key of keys) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: options.temperature ?? 0.3,
          maxOutputTokens: options.maxTokens ?? 1000,
        },
      }),
      signal: AbortSignal.timeout(GEMINI_TIMEOUT_MS),
    });

    if (resp.status === 429 || resp.status === 503) {
      const err = await resp.text().catch(() => resp.statusText);
      errors.push(`key[...${key.slice(-6)}] ${resp.status}: ${err.slice(0, 80)}`);
      continue;
    }

    if (!resp.ok) {
      const err = await resp.text().catch(() => resp.statusText);
      throw new Error(`Gemini API error ${resp.status}: ${err}`);
    }

    const data = await resp.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    if (!text) throw new Error("Gemini returned empty response");
    return text;
  }

  throw new Error(`Gemini all keys exhausted (429/503). ${errors.join("; ")}`);
}

type Provider = "oracle" | "groq" | "cerebras" | "gemini" | "openrouter";

export async function platformChatWithFallback(
  messages: { role: string; content: string }[],
  options: {
    maxTokens?: number;
    temperature?: number;
    model?: string;
    /**
     * "structured" (default) — fast JSON extraction tasks (resume parsing, scoring).
     *   Chain: Groq 8b → Cerebras 8b → Gemini → OpenRouter → Oracle
     *
     * "reasoning" — complex analysis, narration, high context (nugget extraction etc).
     *   Chain: Gemini → Groq 70b → OpenRouter → Oracle
     */
    taskType?: "structured" | "reasoning";
    /** Set false to skip Oracle as last-resort attempt. */
    tryOracle?: boolean;
  } = {}
): Promise<{ text: string; provider: Provider }> {
  const taskType = options.taskType ?? "structured";
  const errors: string[] = [];

  if (taskType === "reasoning") {
    // ── Reasoning chain: Gemini first ──────────────────────────────────────

    // Tier 1 — Gemini (flash model, high context, strong reasoning)
    try {
      const text = await geminiChat(messages, {
        ...options,
        model: options.model ?? GEMINI_MODEL_REASONING,
      });
      return { text, provider: "gemini" };
    } catch (err) {
      const msg = sanitize(err);
      console.warn(`[platform-llm] Gemini (reasoning) failed: ${msg} — trying Groq 70b`);
      errors.push(`Gemini: ${msg}`);
    }

    // Tier 2 — Groq 70b (strong, but rate-limited)
    try {
      const text = await groqChat(messages, { ...options, model: "llama-3.3-70b-versatile" });
      return { text, provider: "groq" };
    } catch (err) {
      const msg = sanitize(err);
      console.warn(`[platform-llm] Groq 70b failed: ${msg} — trying OpenRouter`);
      errors.push(`Groq: ${msg}`);
    }

    // Tier 3 — OpenRouter (reasoning model)
    try {
      const text = await openrouterChat(messages, { ...options, taskType: "reasoning" });
      return { text, provider: "openrouter" };
    } catch (err) {
      const msg = sanitize(err);
      console.warn(`[platform-llm] OpenRouter failed: ${msg} — trying Oracle`);
      errors.push(`OpenRouter: ${msg}`);
    }

  } else {
    // ── Structured chain: fast small models first ───────────────────────────

    // Tier 1 — Groq 8b (fast, cheap, good for structured JSON)
    try {
      const text = await groqChat(messages, { ...options, model: "llama-3.1-8b-instant" });
      return { text, provider: "groq" };
    } catch (err) {
      const msg = sanitize(err);
      console.warn(`[platform-llm] Groq 8b failed: ${msg} — trying Cerebras`);
      errors.push(`Groq: ${msg}`);
    }

    // Tier 2 — Cerebras 8b (ultra-fast, separate rate limits)
    try {
      const text = await cerebrasChat(messages, options);
      return { text, provider: "cerebras" };
    } catch (err) {
      const msg = sanitize(err);
      console.warn(`[platform-llm] Cerebras failed: ${msg} — trying Gemini`);
      errors.push(`Cerebras: ${msg}`);
    }

    // Tier 3 — Gemini flash-lite (reliable, handles complex JSON)
    try {
      const text = await geminiChat(messages, options);
      return { text, provider: "gemini" };
    } catch (err) {
      const msg = sanitize(err);
      console.warn(`[platform-llm] Gemini failed: ${msg} — trying OpenRouter`);
      errors.push(`Gemini: ${msg}`);
    }

    // Tier 4 — OpenRouter (free-tier small model, multiple keys)
    try {
      const text = await openrouterChat(messages, { ...options, taskType: "structured" });
      return { text, provider: "openrouter" };
    } catch (err) {
      const msg = sanitize(err);
      console.warn(`[platform-llm] OpenRouter failed: ${msg} — trying Oracle`);
      errors.push(`OpenRouter: ${msg}`);
    }
  }

  // Final tier — Oracle local Ollama (free, no rate limits, weaker model)
  if (options.tryOracle !== false) {
    try {
      const text = await oracleChat(messages, { temperature: options.temperature });
      return { text, provider: "oracle" };
    } catch (err) {
      errors.push(`Oracle: ${sanitize(err)}`);
    }
  }

  throw new Error(`All providers failed. ${errors.join(". ")}.`);
}

/**
 * Streaming variant of geminiChat — returns a ReadableStream of text chunks.
 * Consumes Gemini's SSE (Server-Sent Events) format and emits only the text.
 * Falls back gracefully: tries all available keys, throws if all exhausted.
 */
export async function geminiChatStream(
  messages: { role: string; content: string }[],
  options: { maxTokens?: number; temperature?: number; model?: string } = {}
): Promise<ReadableStream<Uint8Array>> {
  const model = options.model ?? GEMINI_MODEL_REASONING;
  const systemMsg = messages.find((m) => m.role === "system")?.content ?? "";
  const userMsg = messages
    .filter((m) => m.role !== "system")
    .map((m) => m.content)
    .join("\n\n");
  const prompt = systemMsg ? `${systemMsg}\n\n${userMsg}` : userMsg;

  const keys = platformGeminiKeys();
  let lastError: Error | null = null;

  for (const key of keys) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:streamGenerateContent?alt=sse&key=${key}`;
    let resp: Response;
    try {
      resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: {
            temperature: options.temperature ?? 0.7,
            maxOutputTokens: options.maxTokens ?? 8000,
          },
        }),
      });
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));
      continue;
    }

    if (resp.status === 429 || resp.status === 503) {
      lastError = new Error(`Gemini key[...${key.slice(-6)}] ${resp.status}`);
      continue;
    }
    if (!resp.ok) {
      const errText = await resp.text().catch(() => resp.statusText);
      throw new Error(`Gemini stream error ${resp.status}: ${errText}`);
    }
    if (!resp.body) {
      throw new Error("Gemini stream: no response body");
    }

    const bodyReader = resp.body.getReader();
    const enc = new TextEncoder();

    return new ReadableStream<Uint8Array>({
      async start(controller) {
        const dec = new TextDecoder();
        let buf = "";
        try {
          while (true) {
            const { done, value } = await bodyReader.read();
            if (done) break;
            buf += dec.decode(value, { stream: true });
            const lines = buf.split("\n");
            buf = lines.pop() ?? "";
            for (const line of lines) {
              if (!line.startsWith("data: ")) continue;
              const jsonStr = line.slice(6).trim();
              if (!jsonStr || jsonStr === "[DONE]") continue;
              try {
                const obj = JSON.parse(jsonStr) as Record<string, unknown>;
                const candidates = obj?.candidates as Array<Record<string, unknown>> | undefined;
                const text = (candidates?.[0]?.content as Record<string, unknown>)
                  ?.parts as Array<{ text?: string }> | undefined;
                const chunk = text?.[0]?.text ?? "";
                if (chunk) controller.enqueue(enc.encode(chunk));
              } catch {
                // malformed SSE chunk — skip
              }
            }
          }
        } finally {
          controller.close();
        }
      },
      cancel() {
        bodyReader.cancel().catch(() => {});
      },
    });
  }

  throw lastError ?? new Error("Gemini streaming: all keys exhausted");
}

function sanitize(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err);
  return msg
    .replace(/AIza[0-9A-Za-z_-]{20,}/g, "[REDACTED_KEY]")
    .replace(/gsk_[0-9A-Za-z]{20,}/g, "[REDACTED_KEY]")
    .replace(/csk-[0-9A-Za-z_-]{20,}/g, "[REDACTED_KEY]")
    .replace(/sk-or-v1-[0-9A-Za-z_-]{20,}/g, "[REDACTED_KEY]");
}
