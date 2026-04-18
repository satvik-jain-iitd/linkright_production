// Wave 2 — Recruiter email generator.
// POST /api/outreach/email { resume_job_id, recipient_name?, recipient_email? }
// Returns { subject, content } — a full email with subject line.

import { createClient } from "@/lib/supabase/server";
import { groqChat } from "@/lib/groq";

const SYSTEM_PROMPT = `You are drafting a cold email from a candidate to a recruiter or hiring manager about a specific open role. The user will publish this email under their own name.

Rules (non-negotiable):
- Return valid JSON: {"subject": "string", "content": "string"}.
- Subject: 6-10 words, specific to the role. Not "Application for {role}". Something like "{Company} {Role} — 18% lift on returns flow at Amex".
- Body: 120-220 words. 3 short paragraphs max.
  Para 1 — who you are, what you built that matches ONE real JD requirement (with a number).
  Para 2 — a second concrete signal from your profile that shows pattern, not one-off.
  Para 3 — a single clear ask (resume link, 15-min call).
- First person. "Hi {name}," opener. Never "To whom it may concern".
- Banned phrases: "excited to apply", "thrilled to", "humbled", "please find attached", "synergy", "at your earliest convenience", "unlocked".
- NEVER invent facts. Every claim must be traceable to the candidate highlights.

Return ONLY the JSON object. No markdown fences.`;

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = (await request.json().catch(() => ({}))) as {
    resume_job_id?: string;
    recipient_name?: string;
    recipient_email?: string;
  };
  const jobId = body.resume_job_id?.trim();
  if (!jobId) {
    return Response.json(
      { error: "resume_job_id required" },
      { status: 400 },
    );
  }

  const recipient = (body.recipient_name ?? "").trim() || "there";

  const { data: job } = await supabase
    .from("resume_jobs")
    .select("target_company, target_role, jd_text")
    .eq("id", jobId)
    .eq("user_id", user.id)
    .maybeSingle();
  if (!job) {
    return Response.json({ error: "Resume job not found" }, { status: 404 });
  }

  const { data: nuggets } = await supabase
    .from("career_nuggets")
    .select("answer, nugget_text, company, role")
    .eq("user_id", user.id)
    .in("importance", ["P0", "P1"])
    .order("resume_relevance", { ascending: false })
    .limit(6);

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
    `\n## Top candidate highlights (use TWO in the body)`,
    nuggetLines || "- (profile empty)",
    `\n## Job description (for requirement match)`,
    (job.jd_text ?? "").slice(0, 2000),
    `\nReturn JSON only: {"subject": "...", "content": "..."}.`,
  ].join("\n");

  try {
    const raw = await groqChat(
      [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
      { maxTokens: 700, temperature: 0.5 },
    );
    const stripped = raw
      .replace(/^```(?:json)?\s*/i, "")
      .replace(/\s*```\s*$/i, "")
      .trim();
    let parsed: { subject?: string; content?: string };
    try {
      parsed = JSON.parse(stripped);
    } catch {
      // Fallback: treat full response as content + generate a subject.
      parsed = {
        subject: `${job.target_company ?? "Your"} ${job.target_role ?? "role"} — interested`,
        content: raw.trim(),
      };
    }
    return Response.json({
      subject: (parsed.subject ?? "").trim(),
      content: (parsed.content ?? "").trim(),
    });
  } catch (e) {
    console.error("[outreach/email] error:", e);
    return Response.json(
      { error: "Couldn't draft the email. Try again in a moment." },
      { status: 502 },
    );
  }
}
