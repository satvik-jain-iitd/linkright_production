import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export interface JDRequirement {
  id: string;
  category: "skill" | "experience" | "education" | "certification" | "other";
  text: string;
  importance: "required" | "preferred";
}

export interface JDMatch {
  req_id: string;
  chunk: string;
  status: "met" | "partial";
}

export interface JDGap {
  req_id: string;
  text: string;
  category: string;
  importance: string;
}

export interface JDAnalysisResult {
  requirements: JDRequirement[];
  matches: JDMatch[];
  gaps: JDGap[];
}

const EXTRACTION_PROMPT = `You are a job description analyst. Extract a structured list of requirements from this job description.

Return ONLY valid JSON — no markdown, no explanation:
[
  {
    "id": "r1",
    "category": "skill|experience|education|certification|other",
    "text": "original requirement phrase",
    "importance": "required|preferred"
  }
]

Rules:
- Extract 8-20 distinct requirements
- category: "skill" for technical/soft skills, "experience" for years/domain experience, "education" for degrees, "certification" for certs/licenses, "other" for everything else
- importance: "required" if mandatory, "preferred" if nice-to-have
- Keep "text" concise (under 80 chars) but specific`;

function buildLlmBody(
  provider: string,
  modelId: string,
  apiKey: string,
  jdText: string
) {
  const userMsg = `Job Description:\n${jdText.slice(0, 4000)}`;

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
          { role: "system", content: EXTRACTION_PROMPT },
          { role: "user", content: userMsg },
        ],
        temperature: 0.1,
        max_tokens: 1500,
      }),
    };
  } else {
    return {
      url: `https://generativelanguage.googleapis.com/v1beta/models/${modelId}:generateContent?key=${apiKey}`,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: `${EXTRACTION_PROMPT}\n\n${userMsg}` }] }],
        generationConfig: { temperature: 0.1, maxOutputTokens: 1500 },
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

function parseRequirements(text: string): JDRequirement[] {
  let clean = text.trim().replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
  try {
    const parsed = JSON.parse(clean);
    if (Array.isArray(parsed)) {
      return parsed
        .filter((r) => r.id && r.text)
        .map((r, i) => ({
          id: r.id || `r${i + 1}`,
          category: ["skill", "experience", "education", "certification", "other"].includes(r.category)
            ? r.category
            : "other",
          text: String(r.text).slice(0, 120),
          importance: r.importance === "preferred" ? "preferred" : "required",
        }));
    }
    return [];
  } catch {
    return [];
  }
}

// Text search to match requirement against career chunks
async function searchChunks(
  supabase: Awaited<ReturnType<typeof createClient>>,
  userId: string,
  query: string
): Promise<string[]> {
  const STOPWORDS = new Set([
    "experience", "years", "strong", "knowledge", "ability", "understanding",
    "what", "with", "this", "from", "which", "when", "were", "have",
  ]);

  const words = query
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w: string) => w.length >= 4 && !STOPWORDS.has(w.toLowerCase()))
    .map((w: string) => w.toLowerCase());
  const unique = [...new Set(words)].slice(0, 4);

  if (unique.length === 0) return [];

  const prefixQuery = unique.map((w) => `'${w}':*`).join(" | ");
  const { data } = await supabase
    .from("career_chunks")
    .select("chunk_text")
    .eq("user_id", userId)
    .textSearch("chunk_text", prefixQuery, { config: "english" })
    .limit(2);

  return (data || []).map((row: { chunk_text: string }) => row.chunk_text);
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`jd-analyze:${user.id}`, 5)) {
    return rateLimitResponse("JD analysis");
  }

  const { jd_text, model_provider, model_id, api_key } = await request.json();

  if (!jd_text || !model_provider || !model_id || !api_key) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  // Step 1: Extract requirements via LLM
  let requirements: JDRequirement[] = [];
  try {
    const { url, headers, body } = buildLlmBody(
      model_provider,
      model_id,
      api_key,
      jd_text
    );
    const resp = await fetch(url, {
      method: "POST",
      headers,
      body,
      signal: AbortSignal.timeout(15000),
    });
    if (!resp.ok) {
      return Response.json({ error: "LLM request failed" }, { status: 502 });
    }
    const result = await resp.json();
    const text = extractText(model_provider, result);
    requirements = parseRequirements(text);
  } catch {
    return Response.json({ error: "Failed to analyze JD" }, { status: 500 });
  }

  if (requirements.length === 0) {
    return Response.json({ error: "Could not extract requirements" }, { status: 500 });
  }

  // Step 2: For each requirement, search career chunks
  const matches: JDMatch[] = [];
  const gaps: JDGap[] = [];

  await Promise.allSettled(
    requirements.map(async (req) => {
      const chunks = await searchChunks(supabase, user.id, req.text);
      if (chunks.length > 0) {
        matches.push({
          req_id: req.id,
          chunk: chunks[0],
          status: chunks.length >= 2 ? "met" : "partial",
        });
      } else {
        gaps.push({
          req_id: req.id,
          text: req.text,
          category: req.category,
          importance: req.importance,
        });
      }
    })
  );

  const result: JDAnalysisResult = { requirements, matches, gaps };
  return Response.json(result);
}
