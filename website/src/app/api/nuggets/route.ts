// GET  /api/nuggets?limit=50 — list user's nuggets (importance-sorted).
// POST /api/nuggets             — user-added highlight (free-form).

import { createClient } from "@/lib/supabase/server";

const IMPORTANCE_RANK: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 };
const WORKER_URL = process.env.WORKER_URL ?? "";
const WORKER_SECRET = process.env.WORKER_SECRET ?? "";

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const limit = Math.min(parseInt(searchParams.get("limit") ?? "50", 10) || 50, 200);

  const { data, error } = await supabase
    .from("career_nuggets")
    .select("id,answer,company,role,section_type,importance,tags,created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(limit);

  if (error) return Response.json({ error: error.message }, { status: 500 });

  // Client-side importance sort (P0 first)
  const sorted = (data ?? []).slice().sort((a, b) => {
    const ai = IMPORTANCE_RANK[a.importance as string] ?? 4;
    const bi = IMPORTANCE_RANK[b.importance as string] ?? 4;
    if (ai !== bi) return ai - bi;
    return (b.created_at as string).localeCompare(a.created_at as string);
  });

  return Response.json({ nuggets: sorted });
}

type CreateBody = {
  title?: string;
  body?: string;
  company?: string;
  role?: string;
  section_type?: string;
  tags?: string[];
};

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = (await request.json().catch(() => ({}))) as CreateBody;
  const title = (body.title ?? "").trim();
  const answerText = (body.body ?? "").trim();
  if (!title && !answerText) {
    return Response.json(
      { error: "Give the highlight a title or a short description." },
      { status: 400 },
    );
  }
  if (answerText.length < 10 && title.length < 5) {
    return Response.json(
      { error: "Needs at least a few words — we can't learn from one word." },
      { status: 400 },
    );
  }

  const section =
    typeof body.section_type === "string" && body.section_type
      ? body.section_type
      : "user_added";

  // nugget_index: next sequential for this user.
  const { data: maxRow } = await supabase
    .from("career_nuggets")
    .select("nugget_index")
    .eq("user_id", user.id)
    .order("nugget_index", { ascending: false })
    .limit(1)
    .maybeSingle();
  const nextIndex = ((maxRow?.nugget_index ?? 0) as number) + 1;

  const row = {
    user_id: user.id,
    nugget_index: nextIndex,
    nugget_text: title || answerText.slice(0, 80),
    // career_nuggets.question is NOT NULL. For user-added highlights we
    // don't have an explicit question, so use a stable placeholder tied to
    // the title so it still reads well in any Q/A export.
    question: `Tell me about: ${title || answerText.slice(0, 60)}`,
    alt_questions: [],
    answer: answerText || title,
    primary_layer: "A",
    section_type: section,
    company: body.company?.trim() || null,
    role: body.role?.trim() || null,
    resume_relevance: 0.85,
    importance: "P1",
    factuality: "fact",
    temporality: "past",
    duration: "sustained",
    leadership_signal: "none",
    tags: Array.isArray(body.tags)
      ? ["user_added", ...body.tags.filter((t) => typeof t === "string")]
      : ["user_added"],
  };

  const { data, error } = await supabase
    .from("career_nuggets")
    .insert(row)
    .select(
      "id, nugget_text, answer, company, role, section_type, importance, tags, created_at",
    )
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });

  // Fire worker embed (best-effort).
  if (WORKER_URL && WORKER_SECRET) {
    fetch(`${WORKER_URL}/nuggets/embed`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      body: JSON.stringify({ user_id: user.id }),
    }).catch(() => {});
  }

  return Response.json({ nugget: data });
}
