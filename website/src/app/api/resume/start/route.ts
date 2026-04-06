import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

const WORKER_URL = process.env.WORKER_URL!;
const WORKER_SECRET = process.env.WORKER_SECRET!;

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  // In-memory rate limit: 3 requests/minute per user
  if (!rateLimit(`start:${user.id}`, 3)) {
    return rateLimitResponse("job creation");
  }

  const body = await request.json();
  const { jd_text, career_text, model_provider, model_id, api_key, template_id, qa_answers, override_theme_colors } = body;

  if (!jd_text || !career_text || !model_provider || !model_id || !api_key) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  // Auto-cleanup stale jobs: mark any queued/processing jobs older than 10 min as failed
  const tenMinAgo = new Date(Date.now() - 10 * 60 * 1000).toISOString();
  await supabase
    .from("resume_jobs")
    .update({ status: "failed", error_message: "Timed out after 10 minutes" })
    .eq("user_id", user.id)
    .in("status", ["queued", "processing"])
    .lt("created_at", tenMinAgo);

  // Per-user throttle: max 1 concurrent job (checked AFTER stale cleanup)
  const { count: activeCount } = await supabase
    .from("resume_jobs")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .in("status", ["queued", "processing"]);

  if (activeCount && activeCount >= 1) {
    return Response.json(
      { error: "You already have a resume being generated. Please wait for it to finish." },
      { status: 429 }
    );
  }

  // Per-user throttle: max 5 jobs per hour
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
  const { count: hourlyCount } = await supabase
    .from("resume_jobs")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .gte("created_at", oneHourAgo);

  if (hourlyCount && hourlyCount >= 5) {
    return Response.json(
      { error: "Rate limit: max 5 resumes per hour. Please try again later." },
      { status: 429 }
    );
  }

  // Create job row in Supabase
  const { data: job, error: insertError } = await supabase
    .from("resume_jobs")
    .insert({
      user_id: user.id,
      status: "queued",
      jd_text,
      career_text,
      model_provider,
      model_id,
      template_id: template_id || "cv-a4-standard",
    })
    .select("id")
    .single();

  if (insertError || !job) {
    return Response.json({ error: "Failed to create job" }, { status: 500 });
  }

  // Trigger worker (fire-and-forget, don't await the pipeline)
  try {
    await fetch(`${WORKER_URL}/jobs/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      body: JSON.stringify({
        job_id: job.id,
        user_id: user.id,
        jd_text,
        career_text,
        model_provider,
        model_id,
        api_key,
        template_id: template_id || "cv-a4-standard",
        qa_answers: qa_answers || [],
        override_theme_colors: override_theme_colors || null,
      }),
    });
  } catch {
    // Worker trigger failed — job stays queued, user can retry
    await supabase
      .from("resume_jobs")
      .update({ status: "failed", error_message: "Worker unreachable" })
      .eq("id", job.id);
    return Response.json({ error: "Worker unavailable" }, { status: 502 });
  }

  return Response.json({ job_id: job.id, status: "queued" });
}
