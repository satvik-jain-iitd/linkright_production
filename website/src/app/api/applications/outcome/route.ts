// Wave 2 / applications outcome capture.
// POST /api/applications/outcome
//   { application_id, outcome: "rejected" | "offer" | "interview" | "ghosted", note: string }
//
// Saves the user's 1-line "what happened" as a career_nugget tagged
// "outcome" — these are rare + high-signal training data for the memory
// layer. Later flows (recommender, interview prep, broadcast) retrieve
// these to learn from what worked + what didn't.

import { createClient } from "@/lib/supabase/server";

const VALID_OUTCOMES = ["rejected", "offer", "interview", "ghosted"] as const;
type Outcome = (typeof VALID_OUTCOMES)[number];

const WORKER_URL = process.env.WORKER_URL ?? "";
const WORKER_SECRET = process.env.WORKER_SECRET ?? "";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = (await request.json().catch(() => ({}))) as {
    application_id?: string;
    outcome?: string;
    note?: string;
  };
  const appId = body.application_id?.trim();
  const note = (body.note ?? "").trim();
  const outcome = (body.outcome ?? "").trim().toLowerCase();

  if (!appId) {
    return Response.json({ error: "application_id required" }, { status: 400 });
  }
  if (!VALID_OUTCOMES.includes(outcome as Outcome)) {
    return Response.json(
      { error: `outcome must be one of: ${VALID_OUTCOMES.join(", ")}` },
      { status: 400 },
    );
  }
  if (note.length < 10) {
    return Response.json(
      { error: "Share at least one sentence — this is what the memory learns from." },
      { status: 400 },
    );
  }

  const { data: app } = await supabase
    .from("applications")
    .select("id, company, role, jd_text")
    .eq("id", appId)
    .eq("user_id", user.id)
    .maybeSingle();
  if (!app) {
    return Response.json({ error: "Application not found" }, { status: 404 });
  }

  // Next nugget_index for this user.
  const { data: maxRow } = await supabase
    .from("career_nuggets")
    .select("nugget_index")
    .eq("user_id", user.id)
    .order("nugget_index", { ascending: false })
    .limit(1)
    .maybeSingle();
  const nextIndex = ((maxRow?.nugget_index ?? 0) as number) + 1;

  const prettyOutcome =
    outcome === "rejected"
      ? "Rejected"
      : outcome === "offer"
        ? "Offer"
        : outcome === "interview"
          ? "Interview"
          : "Ghosted";

  const nuggetRow = {
    user_id: user.id,
    nugget_index: nextIndex,
    nugget_text: `${prettyOutcome} · ${app.company ?? ""} ${app.role ?? ""}`.trim(),
    question: `What happened with the ${app.company ?? ""} ${app.role ?? ""} application?`,
    alt_questions: [],
    answer: note,
    primary_layer: "C",
    section_type: "application_outcome",
    company: app.company ?? null,
    role: app.role ?? null,
    resume_relevance: 0.9, // outcomes are gold — high signal for future ranking
    importance: "P1",
    factuality: "fact",
    temporality: "past",
    duration: "point_in_time",
    leadership_signal: "none",
    tags: ["outcome", outcome],
  };

  const { data: inserted, error: insErr } = await supabase
    .from("career_nuggets")
    .insert(nuggetRow)
    .select("id")
    .single();

  if (insErr || !inserted) {
    return Response.json(
      { error: insErr?.message ?? "Couldn't save outcome." },
      { status: 500 },
    );
  }

  // Fire embed (best-effort).
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

  return Response.json({ ok: true, nugget_id: inserted.id });
}
