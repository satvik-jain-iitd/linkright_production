/**
 * POST /api/resume/gaps
 *
 * Gap analysis + targeted interview question generation.
 * Takes JD requirements + current bullet coverage, identifies uncovered
 * requirements, and generates focused questions via Oracle 1B to help
 * the user fill those gaps.
 *
 * Input:
 *   requirements[] — JD requirements (from /api/jd/analyze)
 *   covered_reqs[] — req_ids already covered by resume bullets
 *   user_roles[]   — candidate's company/role list (for context in questions)
 *
 * Output:
 *   coverage_pct, gaps[] (with interview_question + resume_tip per gap)
 */

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

const ORACLE_URL = process.env.ORACLE_BACKEND_URL ?? "";
const ORACLE_SECRET = process.env.ORACLE_BACKEND_SECRET ?? "";

// ── Types ────────────────────────────────────────────────────────────────────

interface JDRequirement {
  id: string;
  category: string;
  text: string;
  importance: "required" | "preferred";
}

interface GapResult {
  req_id: string;
  text: string;
  category: string;
  importance: string;
  interview_question: string;
  resume_tip: string;
}

// ── Oracle 1B call ───────────────────────────────────────────────────────────

async function oracleGenerate(system: string, prompt: string): Promise<string | null> {
  if (!ORACLE_URL) return null;
  try {
    const resp = await fetch(`${ORACLE_URL.replace(/\/$/, "")}/lifeos/rewrite`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ORACLE_SECRET}`,
      },
      body: JSON.stringify({ system, prompt, temperature: 0.3 }),
      signal: AbortSignal.timeout(15000),
    });
    if (!resp.ok) return null;
    const data = (await resp.json()) as { text?: string };
    return data.text?.trim() ?? null;
  } catch {
    return null;
  }
}

// ── Groq fallback ────────────────────────────────────────────────────────────

async function groqGenerate(system: string, prompt: string): Promise<string | null> {
  try {
    const { groqChat } = await import("@/lib/groq");
    const text = await groqChat(
      [
        { role: "system", content: system },
        { role: "user", content: prompt },
      ],
      { maxTokens: 600, temperature: 0.3 }
    );
    return text?.trim() ?? null;
  } catch {
    return null;
  }
}

// ── Generate questions + tips for gaps (batch) ───────────────────────────────

async function generateGapContent(
  gaps: { id: string; text: string; category: string }[],
  userRoles: string[]
): Promise<Record<string, { question: string; tip: string }>> {
  if (gaps.length === 0) return {};

  const rolesContext = userRoles.length > 0
    ? `The candidate has worked at: ${userRoles.join(", ")}.`
    : "No work history available.";

  const system = `You generate targeted interview questions and resume tips for job requirements that a candidate's resume does not currently cover.

Rules:
- Each question should be specific and probe for concrete experience (metrics, tools, team size, outcomes)
- Questions should reference the candidate's known companies when relevant
- Tips should be actionable: "Quantify your X at Y" not "Add more details"
- Return ONLY valid JSON, no markdown fences, no explanation`;

  const gapList = gaps.map((g, i) => `${i + 1}. [${g.category}] ${g.text}`).join("\n");

  const prompt = `${rolesContext}

These JD requirements are NOT covered by the candidate's resume:
${gapList}

For each gap, generate:
1. A focused interview question to ask the candidate (to uncover hidden relevant experience)
2. A resume tip (how to reframe existing experience to cover this gap)

Return JSON array:
[{"req_index": 0, "question": "...", "tip": "..."}, ...]`;

  const rawText = await oracleGenerate(system, prompt) ?? await groqGenerate(system, prompt);
  if (!rawText) return {};

  // Parse JSON from response (strip fences if present)
  const cleaned = rawText
    .replace(/^```(?:json)?\n?/m, "")
    .replace(/\n?```$/m, "")
    .trim();

  try {
    const parsed = JSON.parse(cleaned) as Array<{
      req_index: number;
      question: string;
      tip: string;
    }>;

    const result: Record<string, { question: string; tip: string }> = {};
    for (const item of parsed) {
      if (item.req_index >= 0 && item.req_index < gaps.length) {
        result[gaps[item.req_index].id] = {
          question: item.question ?? "",
          tip: item.tip ?? "",
        };
      }
    }
    return result;
  } catch {
    // If JSON parse fails, return empty — caller handles gracefully
    console.warn("[resume/gaps] Failed to parse LLM response as JSON");
    return {};
  }
}

// ── Route handler ────────────────────────────────────────────────────────────

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`resume-gaps:${user.id}`, 10)) {
    return rateLimitResponse("gap analysis");
  }

  let body: {
    requirements?: JDRequirement[];
    covered_reqs?: string[];
    user_roles?: string[];
  };

  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { requirements, covered_reqs = [], user_roles = [] } = body;

  if (!requirements || !Array.isArray(requirements) || requirements.length === 0) {
    return Response.json({ error: "requirements[] is required" }, { status: 400 });
  }

  // ── Identify gaps ──────────────────────────────────────────────────────

  const coveredSet = new Set(covered_reqs);
  const gapReqs = requirements.filter((r) => !coveredSet.has(r.id));
  const coveredCount = requirements.length - gapReqs.length;
  const coveragePct = Math.round((coveredCount / requirements.length) * 100);
  const requiredGapCount = gapReqs.filter((r) => r.importance === "required").length;

  // ── Generate content for gaps (Oracle 1B / Groq fallback) ──────────────

  const gapContent = await generateGapContent(
    gapReqs.map((r) => ({ id: r.id, text: r.text, category: r.category })),
    user_roles
  );

  // ── Build response ─────────────────────────────────────────────────────

  const gaps: GapResult[] = gapReqs.map((r) => ({
    req_id: r.id,
    text: r.text,
    category: r.category,
    importance: r.importance,
    interview_question: gapContent[r.id]?.question ?? `Tell me about your experience with ${r.text.toLowerCase()}.`,
    resume_tip: gapContent[r.id]?.tip ?? `Consider adding relevant experience from your past roles.`,
  }));

  return Response.json({
    coverage_pct: coveragePct,
    total_reqs: requirements.length,
    covered_count: coveredCount,
    gap_count: gapReqs.length,
    required_gap_count: requiredGapCount,
    gaps,
  });
}
