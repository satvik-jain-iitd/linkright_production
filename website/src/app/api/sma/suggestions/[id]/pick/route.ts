// SMA_v2 — user picks a concept, backend generates the draft.
// POST /api/sma/suggestions/:id/pick { concept_index }
// → calls Groq (3-5s), inserts row in sma_post_drafts, returns draft.

import { createClient } from "@/lib/supabase/server";
import { groqChat } from "@/lib/groq";

type PickBody = { concept_index?: number };
type RouteContext = { params: Promise<{ id: string }> };

const SYSTEM_PROMPT = `You are ghost-writing for a smart, busy operator who will publish this on LinkedIn under their own name. Sound like a builder, not a guru.

Hard rules:
- First person only. "I ...". Never "we did ...".
- 120-280 words, 3-6 short paragraphs.
- No emoji. No hashtags. No sign-off.
- Open with the concrete moment, not a thesis. Numbers where they help.
- Don't invent details, metrics, companies, or people not in the source.
- Banned phrases: "unlocked potential", "step into your power", "game-changer", "synergy", "excited to share", "humbled to announce", "unleash", "paradigm".
- End with one sharp takeaway OR one honest open question — not both.

Return only the post text. No preamble. No sign-off.`;

export async function POST(request: Request, ctx: RouteContext) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id: suggestionId } = await ctx.params;
  const body = (await request.json().catch(() => ({}))) as PickBody;
  const idx = Number.isInteger(body.concept_index) ? (body.concept_index as number) : -1;
  if (idx < 0) {
    return Response.json({ error: "concept_index required" }, { status: 400 });
  }

  // Fetch the suggestion (RLS = user owns it).
  const { data: suggestion, error: sErr } = await supabase
    .from("sma_suggestions")
    .select("id, user_id, diary_entry_id, concepts, status")
    .eq("id", suggestionId)
    .eq("user_id", user.id)
    .maybeSingle();

  if (sErr) return Response.json({ error: sErr.message }, { status: 500 });
  if (!suggestion) return Response.json({ error: "Suggestion not found" }, { status: 404 });
  if (suggestion.status === "picked") {
    // Idempotent: return existing draft if already picked
    const { data: existing } = await supabase
      .from("sma_post_drafts")
      .select("id, draft_content, status, concept_index")
      .eq("suggestion_id", suggestionId)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();
    if (existing) return Response.json({ draft: existing, reused: true });
  }

  const concepts = (suggestion.concepts as Array<Record<string, unknown>>) ?? [];
  const picked = concepts[idx];
  if (!picked) {
    return Response.json({ error: "Invalid concept_index" }, { status: 400 });
  }

  // Pull diary content for context (if linked).
  let diaryContext = "";
  if (suggestion.diary_entry_id) {
    const { data: diary } = await supabase
      .from("user_diary_entries")
      .select("content")
      .eq("id", suggestion.diary_entry_id)
      .maybeSingle();
    diaryContext = diary?.content ?? "";
  }

  const postAngle = String(picked.post_angle ?? "");
  const hookLine = String(picked.hook_line ?? "");
  const topicTag = String(picked.topic_tag ?? "");

  const userPrompt = [
    "## Source moment (today's diary)",
    diaryContext || "(no diary context provided)",
    "",
    "## Angle to take",
    postAngle,
    hookLine ? `\nOpening hook: ${hookLine}` : "",
    topicTag ? `Topic: ${topicTag}` : "",
  ]
    .filter(Boolean)
    .join("\n");

  // Try 8b first (cheap, fast, plenty for prose). Fall back to 70b only if
  // 8b errors structurally — saves the 70b daily token budget for tasks that
  // actually need it (resume parse JSON).
  let draftContent = "";
  let lastErr = "";
  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: userPrompt },
  ];
  for (const model of ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]) {
    try {
      draftContent = (
        await groqChat(messages, { maxTokens: 700, temperature: 0.6, model })
      ).trim();
      if (draftContent) break;
      lastErr = `empty draft from ${model}`;
    } catch (e) {
      lastErr = e instanceof Error ? e.message : "Groq error";
      // Only retry on rate-limit / quota / network class errors.
      if (!/429|rate.?limit|quota|TPD|TPM|timeout|ECONN|fetch failed/i.test(lastErr)) break;
    }
  }
  if (!draftContent) {
    return Response.json({ error: `Draft generation failed: ${lastErr}` }, { status: 502 });
  }

  // Insert draft + mark suggestion picked.
  const { data: draft, error: dErr } = await supabase
    .from("sma_post_drafts")
    .insert({
      user_id: user.id,
      suggestion_id: suggestionId,
      concept_index: idx,
      draft_content: draftContent,
      status: "draft",
    })
    .select("id, draft_content, status, concept_index, created_at")
    .single();

  if (dErr) return Response.json({ error: dErr.message }, { status: 500 });

  await supabase
    .from("sma_suggestions")
    .update({
      status: "picked",
      picked_concept_index: idx,
      picked_at: new Date().toISOString(),
    })
    .eq("id", suggestionId)
    .eq("user_id", user.id);

  return Response.json({ draft });
}
