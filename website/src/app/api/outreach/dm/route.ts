// Wave 2 — LinkedIn DM generator.
// POST /api/outreach/dm { resume_job_id, recipient_name? }
// Returns { content } — a 3-5 sentence DM tailored to the role, drafted from
// the user's strongest profile highlights + the JD. Banned-phrase list +
// first-person only + no "excited to apply" slop.

import { createClient } from "@/lib/supabase/server";
import { groqChat } from "@/lib/groq";

const SYSTEM_PROMPT = `You are drafting a LinkedIn direct message from a candidate to a recruiter or hiring manager for a specific role. The user will publish this DM under their own name.

Rules (non-negotiable):
- 3-5 sentences, ≤600 characters total. LinkedIn DMs cap at ~300 before "see more" — keep it tight.
- First person, direct tone. "Hi {name}, …" opener. Never "Hope you're doing well" or similar filler.
- Tie ONE specific thing from the candidate's profile to ONE specific requirement from the JD. Numbers when present.
- Banned phrases: "excited to apply", "honored", "please consider", "humbly submit", "I believe I would be", "unlocked", "passionate".
- End with a light ask: a link to the resume/call OR a single question about the role. No demands.
- NEVER invent facts. Only use claims present in the source highlights.

Return only the DM text. No preamble, no sign-off (the user adds their own signature).`;

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = (await request.json().catch(() => ({}))) as {
    resume_job_id?: string;
    recipient_name?: string;
  };
  const jobId = body.resume_job_id?.trim();
  if (!jobId) {
    return Response.json(
      { error: "resume_job_id required" },
      { status: 400 },
    );
  }

  const recipient = (body.recipient_name ?? "").trim() || "there";

  // Pull the resume_job target + JD for context.
  const { data: job } = await supabase
    .from("resume_jobs")
    .select("target_company, target_role, jd_text")
    .eq("id", jobId)
    .eq("user_id", user.id)
    .maybeSingle();
  if (!job) {
    return Response.json({ error: "Resume job not found" }, { status: 404 });
  }

  // Pull top 5 highest-relevance nuggets for this user — the strongest signals.
  const { data: nuggets } = await supabase
    .from("career_nuggets")
    .select("answer, nugget_text, company, role")
    .eq("user_id", user.id)
    .in("importance", ["P0", "P1"])
    .order("resume_relevance", { ascending: false })
    .limit(5);

  const nuggetLines = (nuggets ?? [])
    .map(
      (n) =>
        `- ${n.nugget_text || n.answer}${n.company ? ` (at ${n.company})` : ""}`,
    )
    .join("\n");

  const userPrompt = [
    `## Recipient`,
    `Name: ${recipient}`,
    `Company: ${job.target_company ?? ""}`,
    `Role: ${job.target_role ?? ""}`,
    `\n## Top candidate highlights (use ONE in the DM)`,
    nuggetLines || "- (profile empty)",
    `\n## Job description (for requirement match)`,
    (job.jd_text ?? "").slice(0, 1500),
    `\nReturn the DM text only.`,
  ].join("\n");

  try {
    const content = await groqChat(
      [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
      { maxTokens: 400, temperature: 0.5 },
    );
    return Response.json({ content: content.trim() });
  } catch (e) {
    console.error("[outreach/dm] error:", e);
    return Response.json(
      { error: "Couldn't draft the DM. Try again in a moment." },
      { status: 502 },
    );
  }
}
