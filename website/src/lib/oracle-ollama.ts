// Client for the Oracle FastAPI backend's /lifeos/generate endpoint.
// That endpoint wraps a local Ollama (llama3.2:1b) running on Satvik's
// Oracle Cloud VPS — free, no rate limits, no per-token cost.
//
// Use as the cheapest first-try for tasks where a 1B model is good enough
// (resume parsing, bullet cleanup). Fall back to Groq / Gemini when the
// 1B model's output fails validation (e.g. invalid JSON).

const ORACLE_TIMEOUT_MS = 45_000;

function oracleUrl(path: string): string {
  const base = process.env.ORACLE_BACKEND_URL ?? "https://oracle.linkright.in";
  return `${base.replace(/\/$/, "")}${path}`;
}

function oracleSecret(): string {
  const key = process.env.ORACLE_BACKEND_SECRET ?? "";
  if (!key) throw new Error("ORACLE_BACKEND_SECRET not set");
  return key;
}

/**
 * Call Oracle's /lifeos/generate — wraps Ollama smollm2:135m by default.
 * For JSON-shaped tasks, prefer generateLong with llama3.2:1b (below).
 */
export async function oracleGenerate(
  prompt: string,
  options: { system?: string; temperature?: number } = {}
): Promise<string> {
  const resp = await fetch(oracleUrl("/lifeos/generate"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${oracleSecret()}`,
    },
    body: JSON.stringify({
      prompt,
      system: options.system ?? "",
      temperature: options.temperature ?? 0.3,
    }),
    signal: AbortSignal.timeout(ORACLE_TIMEOUT_MS),
  });

  if (!resp.ok) {
    const err = await resp.text().catch(() => resp.statusText);
    throw new Error(`Oracle /lifeos/generate ${resp.status}: ${err}`);
  }

  const data = (await resp.json()) as { text?: string; response?: string };
  const text = data.text ?? data.response ?? "";
  if (!text) throw new Error("Oracle /lifeos/generate returned empty text");
  return text;
}

/**
 * Call Oracle's /lifeos/rewrite — wraps Ollama llama3.2:1b.
 * Better than /generate for structured / longer outputs.
 */
export async function oracleRewrite(
  prompt: string,
  options: { system?: string; temperature?: number } = {}
): Promise<string> {
  const resp = await fetch(oracleUrl("/lifeos/rewrite"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${oracleSecret()}`,
    },
    body: JSON.stringify({
      prompt,
      system: options.system ?? "",
      temperature: options.temperature ?? 0.2,
    }),
    signal: AbortSignal.timeout(ORACLE_TIMEOUT_MS),
  });

  if (!resp.ok) {
    const err = await resp.text().catch(() => resp.statusText);
    throw new Error(`Oracle /lifeos/rewrite ${resp.status}: ${err}`);
  }

  const data = (await resp.json()) as { text?: string; response?: string };
  const text = data.text ?? data.response ?? "";
  if (!text) throw new Error("Oracle /lifeos/rewrite returned empty text");
  return text;
}

/**
 * Chat-style wrapper that accepts OpenAI-shaped messages and returns the
 * assistant text. Collapses system+user messages into Oracle's prompt shape.
 */
export async function oracleChat(
  messages: { role: string; content: string }[],
  options: { temperature?: number; useRewriteModel?: boolean } = {}
): Promise<string> {
  const system = messages.find((m) => m.role === "system")?.content ?? "";
  const user = messages
    .filter((m) => m.role !== "system")
    .map((m) => m.content)
    .join("\n\n");
  const fn = options.useRewriteModel === false ? oracleGenerate : oracleRewrite;
  return fn(user, { system, temperature: options.temperature });
}
