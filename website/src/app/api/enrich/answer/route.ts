import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

const REWRITE_PROMPT = `You are a career profile writer. Rewrite the following raw answer as a polished career profile paragraph.

Rules:
- First person, professional tone
- Lead with an action verb
- Include specific quantifiers if mentioned (numbers, %, team size, revenue)
- Follow storytelling structure: context → action → outcome
- Keep it 2-4 sentences
- Do not invent specifics not present in the answer
- Return ONLY the rewritten paragraph, no commentary`;

function buildSearchQueries(answer: string): string[] {
  // Extract meaningful noun phrases and technical terms for dedup search
  const words = answer
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length >= 5)
    .map((w) => w.toLowerCase());

  const unique = [...new Set(words)].slice(0, 6);
  if (unique.length === 0) return [answer.slice(0, 100)];

  // Create 2-3 overlapping query strings
  const queries: string[] = [];
  if (unique.length >= 3) queries.push(unique.slice(0, 3).join(" "));
  if (unique.length >= 4) queries.push(unique.slice(2, 5).join(" "));
  queries.push(unique.slice(0, 2).join(" "));

  return [...new Set(queries)].slice(0, 3);
}

async function searchChunks(
  supabase: Awaited<ReturnType<typeof createClient>>,
  userId: string,
  query: string
): Promise<string[]> {
  const STOPWORDS = new Set(["the", "and", "that", "with", "this", "from", "which", "when", "were", "have"]);

  const words = query
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w: string) => w.length >= 4 && !STOPWORDS.has(w.toLowerCase()))
    .map((w: string) => w.toLowerCase());
  const unique = [...new Set(words)].slice(0, 3);
  if (unique.length === 0) return [];

  const prefixQuery = unique.map((w) => `'${w}':*`).join(" & ");
  const { data } = await supabase
    .from("career_chunks")
    .select("chunk_text")
    .eq("user_id", userId)
    .textSearch("chunk_text", prefixQuery, { config: "english" })
    .limit(2);

  return (data || []).map((row: { chunk_text: string }) => row.chunk_text);
}

function buildLlmBody(
  provider: string,
  modelId: string,
  apiKey: string,
  answer: string
) {
  if (provider === "groq" || provider === "openrouter") {
    const baseUrl =
      provider === "openrouter"
        ? "https://openrouter.ai/api/v1"
        : "https://api.groq.com/openai/v1";
    return {
      url: `${baseUrl}/chat/completions`,
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        ...(provider === "openrouter" ? { "HTTP-Referer": "https://linkright.in" } : {}),
      },
      body: JSON.stringify({
        model: modelId,
        messages: [
          { role: "system", content: REWRITE_PROMPT },
          { role: "user", content: answer },
        ],
        temperature: 0.3,
        max_tokens: 300,
      }),
    };
  } else {
    return {
      url: `https://generativelanguage.googleapis.com/v1beta/models/${modelId}:generateContent?key=${apiKey}`,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: `${REWRITE_PROMPT}\n\n${answer}` }] }],
        generationConfig: { temperature: 0.3, maxOutputTokens: 300 },
      }),
    };
  }
}

function extractText(provider: string, result: Record<string, unknown>): string {
  if (provider === "gemini") {
    return (
      (
        result?.candidates as Array<{
          content: { parts: Array<{ text: string }> };
        }>
      )?.[0]?.content?.parts?.[0]?.text ?? ""
    );
  }
  return (
    (result?.choices as Array<{ message: { content: string } }>)?.[0]?.message
      ?.content ?? ""
  );
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`enrich-answer:${user.id}`, 10)) {
    return rateLimitResponse("enrich answer");
  }

  const { answer, model_provider, model_id, api_key } = await request.json();

  if (!answer || answer.trim().length < 20) {
    return Response.json({ error: "Answer too short" }, { status: 400 });
  }

  if (!model_provider || !model_id || !api_key) {
    return Response.json({ error: "Missing LLM config" }, { status: 400 });
  }

  // Step 1: Deduplication — search existing career chunks
  const searchQueries = buildSearchQueries(answer);
  let isDuplicate = false;

  for (const q of searchQueries) {
    const chunks = await searchChunks(supabase, user.id, q);
    if (chunks.length > 0) {
      // Check keyword overlap: if >60% of significant words from answer appear in a chunk
      const answerWords = new Set(
        answer.toLowerCase().split(/\s+/).filter((w: string) => w.length >= 5)
      );
      for (const chunk of chunks) {
        const chunkWords = chunk.toLowerCase().split(/\s+/);
        const overlap = chunkWords.filter((w: string) => answerWords.has(w)).length;
        const overlapRatio = answerWords.size > 0 ? overlap / answerWords.size : 0;
        if (overlapRatio >= 0.4) {
          isDuplicate = true;
          break;
        }
      }
    }
    if (isDuplicate) break;
  }

  if (isDuplicate) {
    return Response.json({
      status: "duplicate",
      message: "This information is already captured in your career profile.",
    });
  }

  // Step 2: Rewrite as career profile paragraph via LLM
  let rewritten = answer.trim();
  try {
    const { url, headers, body } = buildLlmBody(
      model_provider,
      model_id,
      api_key,
      answer
    );
    const resp = await fetch(url, { method: "POST", headers, body, signal: AbortSignal.timeout(10000) });
    if (resp.ok) {
      const result = await resp.json();
      const text = extractText(model_provider, result).trim();
      if (text.length > 20) rewritten = text;
    }
  } catch {
    // Fall back to raw answer
  }

  // Step 3: Append as new chunk to career_chunks
  const { data: existingChunks } = await supabase
    .from("career_chunks")
    .select("chunk_index")
    .eq("user_id", user.id)
    .order("chunk_index", { ascending: false })
    .limit(1);

  const nextIndex = existingChunks && existingChunks.length > 0
    ? (existingChunks[0] as { chunk_index: number }).chunk_index + 1
    : 0;

  const { error: insertError } = await supabase
    .from("career_chunks")
    .insert({
      user_id: user.id,
      chunk_index: nextIndex,
      chunk_text: rewritten,
      chunk_tokens: Math.ceil(rewritten.length / 4),
    });

  if (insertError) {
    return Response.json({ error: "Failed to save to profile" }, { status: 500 });
  }

  // Step 4: Fire-and-forget nugget re-embedding so new chunk gets indexed
  const workerUrl = process.env.WORKER_URL;
  const workerSecret = process.env.WORKER_SECRET;
  if (workerUrl && workerSecret) {
    fetch(`${workerUrl}/nuggets/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${workerSecret}`,
      },
      body: JSON.stringify({ user_id: user.id }),
    }).catch(() => {/* non-blocking — enrich answer already saved */});
  }

  return Response.json({
    status: "added",
    message: "Added to your career profile.",
    summary: rewritten.slice(0, 100) + (rewritten.length > 100 ? "..." : ""),
  });
}
