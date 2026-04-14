/**
 * /api/applications — CRUD for job applications
 *
 * GET    → list all applications for current user (ordered by updated_at desc)
 * POST   → create new application
 * PUT    → update application (status, notes, dates, etc.)
 * DELETE → delete application (soft: set status = 'withdrawn')
 */

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function GET() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { data, error } = await supabase
    .from("applications")
    .select("*, resume_jobs(id, status, version_number, is_active_version, created_at)")
    .eq("user_id", user.id)
    .order("updated_at", { ascending: false });

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ applications: data ?? [] });
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`app-create:${user.id}`, 10)) {
    return rateLimitResponse("application creation");
  }

  let body: Record<string, unknown>;
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { company, role, jd_text, jd_url, location, salary_range, excitement, notes, tags } = body;

  if (!company || typeof company !== "string" || !role || typeof role !== "string") {
    return Response.json({ error: "company and role are required" }, { status: 400 });
  }

  const row = {
    user_id: user.id,
    company: (company as string).trim(),
    role: (role as string).trim(),
    jd_text: typeof jd_text === "string" ? jd_text : null,
    jd_url: typeof jd_url === "string" ? jd_url : null,
    location: typeof location === "string" ? location : null,
    salary_range: typeof salary_range === "string" ? salary_range : null,
    excitement: typeof excitement === "number" && excitement >= 1 && excitement <= 5 ? excitement : null,
    notes: typeof notes === "string" ? notes : null,
    tags: Array.isArray(tags) ? tags.filter((t): t is string => typeof t === "string") : [],
    status: "not_started",
  };

  const { data, error } = await supabase
    .from("applications")
    .insert(row)
    .select("id, company, role, status, created_at")
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ application: data }, { status: 201 });
}

export async function PUT(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  let body: Record<string, unknown>;
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { id, ...updates } = body;
  if (!id || typeof id !== "string") {
    return Response.json({ error: "id is required" }, { status: 400 });
  }

  const VALID_STATUSES = [
    "not_started", "resume_draft", "applied", "screening",
    "interview", "offer", "accepted", "rejected", "withdrawn",
  ];

  // Only allow known fields
  const allowed: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (typeof updates.status === "string" && VALID_STATUSES.includes(updates.status)) allowed.status = updates.status;
  if (typeof updates.company === "string") allowed.company = updates.company;
  if (typeof updates.role === "string") allowed.role = updates.role;
  if (typeof updates.notes === "string") allowed.notes = updates.notes;
  if (typeof updates.jd_text === "string") allowed.jd_text = updates.jd_text;
  if (typeof updates.jd_url === "string") allowed.jd_url = updates.jd_url;
  if (typeof updates.location === "string") allowed.location = updates.location;
  if (typeof updates.salary_range === "string") allowed.salary_range = updates.salary_range;
  if (typeof updates.excitement === "number") allowed.excitement = updates.excitement;
  if (typeof updates.applied_at === "string") allowed.applied_at = updates.applied_at;
  if (typeof updates.interview_at === "string") allowed.interview_at = updates.interview_at;
  if (typeof updates.deadline === "string") allowed.deadline = updates.deadline;
  if (Array.isArray(updates.tags)) allowed.tags = updates.tags.filter((t): t is string => typeof t === "string");

  const { data, error } = await supabase
    .from("applications")
    .update(allowed)
    .eq("id", id)
    .eq("user_id", user.id)  // RLS + explicit check
    .select("id, company, role, status, updated_at")
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ error: "Application not found" }, { status: 404 });
  return Response.json({ application: data });
}
