// SMA_v2 — user picks a concept, backend generates the draft.
// POST /api/sma/suggestions/:id/pick { concept_index }
// → calls n8n PersonalizedGenerator (sync), inserts row in sma_post_drafts.

import { createClient } from "@/lib/supabase/server";

type PickBody = { concept_index?: number };
type RouteContext = { params: Promise<{ id: string }> };

const PERSONALIZE_URL = process.env.SMA_PERSONALIZE_URL ?? "";
const SMA_TOKEN = process.env.SMA_INTERNAL_TOKEN ?? "";
const PERSONALIZE_TIMEOUT_MS = 60_000; // gemma3:1b on Oracle ~30-45s

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

  // Call n8n PersonalizedGenerator. Returns { draft_content }.
  if (!PERSONALIZE_URL || !SMA_TOKEN) {
    return Response.json(
      { error: "SMA_PERSONALIZE_URL or SMA_INTERNAL_TOKEN not configured" },
      { status: 500 },
    );
  }

  let draftContent = "";
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), PERSONALIZE_TIMEOUT_MS);
    const r = await fetch(PERSONALIZE_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${SMA_TOKEN}`,
      },
      body: JSON.stringify({
        user_id: user.id,
        concept: picked,
        diary_context: diaryContext,
      }),
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      return Response.json(
        { error: `Generator failed: ${r.status} ${txt.slice(0, 200)}` },
        { status: 502 },
      );
    }
    const out = await r.json().catch(() => ({}));
    draftContent = (out.draft_content ?? "").toString().trim();
  } catch (e) {
    const msg = e instanceof Error ? e.message : "fetch error";
    return Response.json({ error: `Generator unreachable: ${msg}` }, { status: 502 });
  }

  if (!draftContent) {
    return Response.json({ error: "Generator returned empty draft" }, { status: 502 });
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
