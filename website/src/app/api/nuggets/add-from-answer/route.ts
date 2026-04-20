// POST /api/nuggets/add-from-answer
// Body: { parent_nugget_id, question, answer, job_discovery_id? }
// Persists the user's follow-up answer as a NEW career_nuggets row (P1),
// inheriting company/role from the parent. Also triggers embedding via
// worker endpoint so the new nugget is searchable within a minute.

import { createClient } from "@/lib/supabase/server";

const WORKER_URL = process.env.WORKER_URL ?? "";
const WORKER_SECRET = process.env.WORKER_SECRET ?? "";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json().catch(() => ({}));
  const parentId: string | undefined = body.parent_nugget_id;
  const question: string = (body.question ?? "").toString().trim();
  const answer: string = (body.answer ?? "").toString().trim();
  if (!question || !answer) {
    return Response.json({ error: "question and answer required" }, { status: 400 });
  }
  if (answer.length < 10) {
    return Response.json({ error: "answer too short" }, { status: 400 });
  }

  // Fetch parent for context inheritance (RLS restricts to user's own)
  let parentContext: {
    company: string | null;
    role: string | null;
    section_type: string | null;
  } = { company: null, role: null, section_type: null };
  if (parentId) {
    const { data: parent } = await supabase
      .from("career_nuggets")
      .select("company,role,section_type")
      .eq("id", parentId)
      .eq("user_id", user.id)
      .maybeSingle();
    if (parent) parentContext = parent;
  }

  // Compute next nugget_index for this user
  const { data: maxRow } = await supabase
    .from("career_nuggets")
    .select("nugget_index")
    .eq("user_id", user.id)
    .order("nugget_index", { ascending: false })
    .limit(1)
    .maybeSingle();
  const nextIndex = ((maxRow?.nugget_index ?? 0) as number) + 1;

  const { data: inserted, error } = await supabase
    .from("career_nuggets")
    .insert({
      user_id: user.id,
      nugget_index: nextIndex,
      nugget_text: `Q: ${question}\nA: ${answer}`,
      question,
      alt_questions: [],
      answer,
      primary_layer: "A",
      section_type: parentContext.section_type ?? "work_experience",
      company: parentContext.company,
      role: parentContext.role,
      resume_relevance: 0.85,     // user-curated → high
      importance: "P1",
      factuality: "fact",
      temporality: "past",
      duration: "point_in_time",
      leadership_signal: "none",
      tags: ["user_interview"],
      // parent_nugget_id links this Q&A back to the source highlight.
      // Requires DB migration: ALTER TABLE career_nuggets ADD COLUMN IF NOT EXISTS
      //   parent_nugget_id uuid REFERENCES career_nuggets(id) ON DELETE SET NULL;
      ...(parentId ? { parent_nugget_id: parentId } : {}),
    })
    .select("id")
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  // Fire-and-forget: ask the worker to embed newly-inserted nuggets for this user.
  // The worker already has /nuggets/embed which picks up unembedded rows.
  if (WORKER_URL && WORKER_SECRET) {
    fetch(`${WORKER_URL}/nuggets/embed`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      body: JSON.stringify({ user_id: user.id }),
    }).catch(() => {
      // non-blocking — the scheduled embedder will pick this up too
    });
  }

  return Response.json({ nugget_id: inserted.id });
}
