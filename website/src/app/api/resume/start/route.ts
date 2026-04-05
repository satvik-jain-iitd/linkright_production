import { createClient } from "@/lib/supabase/server";

const WORKER_URL = process.env.WORKER_URL!; // https://sync-resume-engine.onrender.com
const WORKER_SECRET = process.env.WORKER_SECRET!;

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { jd_text, career_text, model_provider, model_id, api_key, template_id } = body;

  if (!jd_text || !career_text || !model_provider || !model_id || !api_key) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
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
