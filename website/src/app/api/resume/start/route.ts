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
  // [BYOK-REMOVED] api_key destructured but no longer required from client
  const { jd_text, career_text, model_provider, model_id, /* api_key, */ template_id, qa_answers, override_theme_colors, target_role, target_company } = body; // [PSA5-ayd.1.1.3]

  // [BYOK-REMOVED] api_key removed from required fields — server provides the key
  // if (!jd_text || !career_text || !model_provider || !model_id || !api_key) {
  if (!jd_text || !career_text) {
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

  // [BYOK-REMOVED] UUID key resolution block — server now provides the key
  // let resolved_api_key = api_key;
  // const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  // if (UUID_RE.test(api_key)) {
  //   const { data: keyRow } = await supabase
  //     .from("user_api_keys")
  //     .select("api_key")
  //     .eq("id", api_key)
  //     .eq("user_id", user.id)
  //     .single();
  //   if (keyRow?.api_key) {
  //     resolved_api_key = keyRow.api_key;
  //   } else {
  //     // Fallback: try user_settings
  //     const { data: settings } = await supabase
  //       .from("user_settings")
  //       .select("api_key")
  //       .eq("user_id", user.id)
  //       .single();
  //     if (settings?.api_key) {
  //       resolved_api_key = settings.api_key;
  //     }
  //   }
  // }
  const resolved_api_key = process.env.GROQ_API_KEY || "";

  // Create job row in Supabase
  const { data: job, error: insertError } = await supabase
    .from("resume_jobs")
    .insert({
      user_id: user.id,
      status: "queued",
      jd_text,
      career_text,
      model_provider: body.model_provider || "groq",
      model_id: body.model_id || "llama-3.1-8b-instant",
      template_id: template_id || "cv-a4-standard",
      target_role: target_role || null, // [PSA5-ayd.1.1.3]
      target_company: target_company || null, // [PSA5-ayd.1.1.3]
    })
    .select("id")
    .single();

  if (insertError || !job) {
    return Response.json({ error: "Failed to create job" }, { status: 500 });
  }

  // Trigger worker (fire-and-forget, don't await the pipeline)
  try {
    const workerRes = await fetch(`${WORKER_URL}/jobs/start`, {
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
        model_provider: body.model_provider || "groq",
        model_id: body.model_id || "llama-3.1-8b-instant",
        api_key: resolved_api_key,
        template_id: template_id || "cv-a4-standard",
        qa_answers: qa_answers || [],
        // Sanitize: worker Pydantic model requires str for all 4 color fields — no nulls allowed
        override_theme_colors: override_theme_colors ? {
          brand_primary: override_theme_colors.brand_primary,
          brand_secondary: override_theme_colors.brand_secondary,
          brand_tertiary: override_theme_colors.brand_tertiary || override_theme_colors.brand_secondary,
          brand_quaternary: override_theme_colors.brand_quaternary || override_theme_colors.brand_primary,
        } : null,
      }),
    });
    if (!workerRes.ok) {
      throw new Error(`Worker responded with ${workerRes.status}`);
    }
  } catch (err) {
    // Worker trigger failed — mark job as failed so user can retry immediately
    await supabase
      .from("resume_jobs")
      .update({ status: "failed", error_message: `Worker unavailable: ${err instanceof Error ? err.message : "unknown"}` })
      .eq("id", job.id);
    return Response.json({ error: "Worker unavailable" }, { status: 502 });
  }

  return Response.json({ job_id: job.id, status: "queued" });
}
