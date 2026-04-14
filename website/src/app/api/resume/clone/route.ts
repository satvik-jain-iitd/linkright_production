/**
 * POST /api/resume/clone
 *
 * Clone a resume job. Two modes:
 *   mode = "new_version"  → same application, new version number
 *   mode = "new_application" → creates a new application first, then clones resume into it
 *
 * Input: { source_job_id, mode, new_company?, new_role?, new_jd_text? }
 * Output: { job_id, application_id?, version_number }
 */

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`resume-clone:${user.id}`, 10)) {
    return rateLimitResponse("resume clone");
  }

  let body: {
    source_job_id?: string;
    mode?: "new_version" | "new_application";
    new_company?: string;
    new_role?: string;
    new_jd_text?: string;
  };

  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { source_job_id, mode = "new_version", new_company, new_role, new_jd_text } = body;

  if (!source_job_id) {
    return Response.json({ error: "source_job_id is required" }, { status: 400 });
  }

  // Fetch source job
  const { data: source, error: fetchErr } = await supabase
    .from("resume_jobs")
    .select("*")
    .eq("id", source_job_id)
    .eq("user_id", user.id)
    .single();

  if (fetchErr || !source) {
    return Response.json({ error: "Source resume not found" }, { status: 404 });
  }

  let applicationId = source.application_id;

  if (mode === "new_application") {
    // Create a new application
    if (!new_company || !new_role) {
      return Response.json({ error: "new_company and new_role required for new_application mode" }, { status: 400 });
    }
    const { data: app, error: appErr } = await supabase
      .from("applications")
      .insert({
        user_id: user.id,
        company: new_company.trim(),
        role: new_role.trim(),
        jd_text: new_jd_text ?? null,
        status: "resume_draft",
      })
      .select("id")
      .single();

    if (appErr) return Response.json({ error: appErr.message }, { status: 500 });
    applicationId = app?.id ?? null;
  }

  // Determine next version number
  let versionNumber = 1;
  if (applicationId) {
    const { count } = await supabase
      .from("resume_jobs")
      .select("id", { count: "exact", head: true })
      .eq("application_id", applicationId);
    versionNumber = (count ?? 0) + 1;
  }

  // Clone the resume job
  const cloneRow = {
    user_id: user.id,
    application_id: applicationId,
    cloned_from: source_job_id,
    version_number: versionNumber,
    is_active_version: true,
    status: "draft",
    // Copy content from source
    jd_text: mode === "new_application" ? (new_jd_text ?? source.jd_text) : source.jd_text,
    career_text: source.career_text,
    target_role: mode === "new_application" ? (new_role ?? source.target_role) : source.target_role,
    target_company: mode === "new_application" ? (new_company ?? source.target_company) : source.target_company,
    model_provider: source.model_provider,
    model_id: source.model_id,
    output_html: source.output_html,
    brand_primary: source.brand_primary,
    brand_secondary: source.brand_secondary,
  };

  const { data: cloned, error: cloneErr } = await supabase
    .from("resume_jobs")
    .insert(cloneRow)
    .select("id, version_number, application_id")
    .single();

  if (cloneErr) return Response.json({ error: cloneErr.message }, { status: 500 });

  // Mark old versions as not active (for same application)
  if (applicationId) {
    await supabase
      .from("resume_jobs")
      .update({ is_active_version: false })
      .eq("application_id", applicationId)
      .neq("id", cloned!.id);
  }

  return Response.json({
    job_id: cloned!.id,
    application_id: applicationId,
    version_number: versionNumber,
    cloned_from: source_job_id,
  }, { status: 201 });
}
