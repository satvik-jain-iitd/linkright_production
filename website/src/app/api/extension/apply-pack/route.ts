import { authorizeExtensionRequest } from "@/lib/extension-jwt";
import { createServiceClient } from "@/lib/supabase/service";

/** POST /api/extension/apply-pack?job_id=<uuid>
 *
 * Triggers the full resume pipeline against a job previously registered
 * via /api/extension/parse-job. Returns a resume_id the extension can use
 * to open the apply-pack in sync.linkright.in for review.
 *
 * This wraps /api/resume/start — duplicating the logic is cheaper and
 * keeps the extension auth boundary clean (the existing resume/start
 * relies on Supabase cookie session; the extension uses JWT).
 *
 * Auth: Authorization: Bearer <extension-jwt>
 */

export async function POST(request: Request) {
  const claims = await authorizeExtensionRequest(request);
  if (!claims) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(request.url);
  const jobId = url.searchParams.get("job_id");
  if (!jobId) {
    return Response.json({ error: "job_id query param required" }, { status: 400 });
  }

  const sb = createServiceClient();

  // Fetch the saved job_scans row (must belong to this user).
  const { data: job, error: jobErr } = await sb
    .from("job_scans")
    .select("id, jd_text, job_title")
    .eq("id", jobId)
    .eq("user_id", claims.sub)
    .maybeSingle();

  if (jobErr || !job) {
    return Response.json({ error: "Job not found" }, { status: 404 });
  }

  // Fetch user's career_text from career_chunks (resume pipeline needs it).
  const { data: chunks } = await sb
    .from("career_chunks")
    .select("chunk_text")
    .eq("user_id", claims.sub)
    .order("chunk_index", { ascending: true })
    .limit(100);

  const careerText = (chunks ?? [])
    .map((c: { chunk_text: string }) => c.chunk_text)
    .join("\n\n")
    .slice(0, 32_000);

  if (!careerText || careerText.length < 200) {
    return Response.json(
      { error: "Your memory layer is too thin to generate a tailored resume. Open /onboarding first." },
      { status: 422 },
    );
  }

  // Insert a new resume_jobs row with status='queued' — the worker's
  // queue_poller picks it up.
  const { data: resumeJob, error: rjErr } = await sb
    .from("resume_jobs")
    .insert({
      user_id: claims.sub,
      jd_text: job.jd_text,
      career_text: careerText,
      status: "queued",
      current_phase: "queued",
      phase_number: 0,
      progress_pct: 0,
      source: "extension",
      source_job_scan_id: job.id,
    })
    .select("id")
    .single();

  if (rjErr || !resumeJob) {
    console.error("[ext-apply-pack] insert failed:", rjErr);
    return Response.json({ error: "Could not queue apply-pack" }, { status: 500 });
  }

  return Response.json({
    resume_id: resumeJob.id,
    status: "queued",
    open_url: `https://sync.linkright.in/resume/customize/${resumeJob.id}`,
  });
}
