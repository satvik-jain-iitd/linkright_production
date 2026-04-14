/**
 * /api/discoveries/[id]/apply — Move discovery to applications pipeline
 *
 * POST → create application from discovery, mark discovery as 'applied'
 */

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`discovery-apply:${user.id}`, 10)) {
    return rateLimitResponse("application creation");
  }

  const { id } = await params;

  // Fetch the discovery
  const { data: discovery, error: fetchErr } = await supabase
    .from("job_discoveries")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (fetchErr || !discovery) {
    return Response.json({ error: "Discovery not found" }, { status: 404 });
  }

  if (discovery.status === "applied") {
    return Response.json({ error: "Already applied to this discovery" }, { status: 409 });
  }

  // Dedup: check if application with same company+role already exists
  const normCompany = discovery.company_name.trim().toLowerCase();
  const normRole = discovery.title.trim().toLowerCase();

  const { data: existingApp } = await supabase
    .from("applications")
    .select("id, company, role")
    .eq("user_id", user.id)
    .ilike("company", normCompany)
    .ilike("role", normRole)
    .limit(1)
    .maybeSingle();

  if (existingApp) {
    // Mark discovery as applied even if app already exists
    await supabase
      .from("job_discoveries")
      .update({ status: "applied" })
      .eq("id", id)
      .eq("user_id", user.id);

    return Response.json({
      error: `Application for "${existingApp.company} — ${existingApp.role}" already exists`,
      existing_id: existingApp.id,
    }, { status: 409 });
  }

  // Create application pre-filled from discovery
  const { data: application, error: insertErr } = await supabase
    .from("applications")
    .insert({
      user_id: user.id,
      company: discovery.company_name,
      role: discovery.title,
      jd_url: discovery.job_url,
      location: discovery.location,
      notes: discovery.description_snippet
        ? `[Scout] ${discovery.description_snippet}`
        : "[Scout] Discovered via job scanner",
      tags: ["scout"],
      status: "not_started",
    })
    .select("id, company, role, status, created_at")
    .single();

  if (insertErr) return Response.json({ error: insertErr.message }, { status: 500 });

  // Mark discovery as applied
  await supabase
    .from("job_discoveries")
    .update({ status: "applied" })
    .eq("id", id)
    .eq("user_id", user.id);

  return Response.json({
    application,
    discovery_id: id,
  }, { status: 201 });
}
