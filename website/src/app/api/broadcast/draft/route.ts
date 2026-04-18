// Wave 2 / S17 — Compose draft.
// POST /api/broadcast/draft { insight_id, insight_kind, tone? }
// → returns { content, regens_remaining }
//
// Uses groqChat to draft a LinkedIn-shaped post from the source insight.
// Banned phrases + first-person only; the source text is the ground truth
// (no invention). Respects a per-insight regen budget (3 per insight).

import { createClient } from "@/lib/supabase/server";
import { groqChat } from "@/lib/groq";

const SYSTEM_PROMPT = `You are ghost-writing for a smart, busy operator. They will publish this post on LinkedIn under their own name. Your job is to turn a specific real moment (from their diary, resume, or project history) into a post that sounds like a builder, not a guru.

Rules (non-negotiable):
- First person only. "I ...". Never "we did ...".
- 120-350 words, 3-7 short paragraphs. No emoji. No hashtags.
- Open with the concrete moment, not a thesis. Numbers where they help.
- Don't invent. Don't embellish metrics. Don't add meetings, titles, or companies that weren't in the source.
- Banned phrases: "unlocked potential", "step into your power", "game-changer", "synergy", "excited to share", "humbled to announce", "unleash", "paradigm".
- End with one sharp takeaway OR one honest open question — not both.

Return only the post text. No preamble. No sign-off.`;

type DraftBody = {
  insight_id?: string;
  insight_kind?: "nugget" | "diary";
  tone?: "shorter" | "punchier" | "more_personal" | "add_question" | "sharper";
  previous_draft?: string;
};

const TONE_INSTRUCTIONS: Record<string, string> = {
  shorter: "Cut at least 40% of the length. Keep only the sharpest lines.",
  punchier: "Shorter sentences. Stronger verbs. No adverbs.",
  more_personal: "Add one specific sensory or emotional detail from the moment. No cliches.",
  add_question: "End with a single honest, open question the reader can answer.",
  sharper: "Rewrite the final line as a crisp, memorable takeaway.",
};

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = (await request.json().catch(() => ({}))) as DraftBody;
  const insightId = body.insight_id?.trim();
  const kind = body.insight_kind ?? "nugget";
  if (!insightId) {
    return Response.json({ error: "insight_id required" }, { status: 400 });
  }

  // Fetch insight body (RLS restricts to user's own).
  let sourceText = "";
  let sourceLabel = "";
  if (kind === "nugget") {
    const { data } = await supabase
      .from("career_nuggets")
      .select("answer, nugget_text, company, role, section_type")
      .eq("id", insightId)
      .eq("user_id", user.id)
      .maybeSingle();
    if (!data)
      return Response.json({ error: "Insight not found" }, { status: 404 });
    sourceText = `${data.nugget_text ?? ""}\n${data.answer ?? ""}`.trim();
    sourceLabel = data.company ? `at ${data.company} as ${data.role}` : "from profile";
  } else {
    const { data } = await supabase
      .from("user_diary_entries")
      .select("content, created_at")
      .eq("id", insightId)
      .eq("user_id", user.id)
      .maybeSingle();
    if (!data)
      return Response.json({ error: "Insight not found" }, { status: 404 });
    sourceText = data.content;
    sourceLabel = "from diary";
  }

  if (!sourceText) {
    return Response.json(
      { error: "Insight has no content to draft from." },
      { status: 422 },
    );
  }

  // Regen budget — 3 regens per insight per user.
  const { count } = await supabase
    .from("broadcast_posts")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .eq("source_insight_id", insightId);
  const regens_used = count ?? 0;
  const regens_remaining = Math.max(0, 3 - regens_used);
  if (regens_used >= 3 && !body.previous_draft) {
    return Response.json(
      {
        error: "Regen budget used (3/3). Edit manually or pick a different insight.",
      },
      { status: 429 },
    );
  }

  const toneHint = body.tone ? TONE_INSTRUCTIONS[body.tone] ?? "" : "";

  const userPrompt = [
    "## Source moment",
    `Context: ${sourceLabel}`,
    sourceText,
    body.previous_draft ? `\n## Previous draft (rewrite, don't re-use)\n${body.previous_draft}` : "",
    toneHint ? `\n## Tone adjustment\n${toneHint}` : "",
  ]
    .filter(Boolean)
    .join("\n");

  const content = await groqChat(
    [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: userPrompt },
    ],
    { maxTokens: 700, temperature: 0.6 },
  );

  return Response.json({
    content: content.trim(),
    regens_remaining,
  });
}
