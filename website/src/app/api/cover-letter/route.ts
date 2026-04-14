/**
 * /api/cover-letter — CRUD + trigger for cover letter generation
 *
 * POST → trigger cover letter generation (calls worker /jobs/cover-letter)
 * GET  → list cover letters or fetch specific one (query: application_id)
 */

import { createClient } from "@/lib/supabase/server";

const WORKER_URL = process.env.WORKER_URL;
const WORKER_SECRET = process.env.WORKER_SECRET;

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  let body: { application_id?: string; resume_job_id?: string; recipient_name?: string };
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { application_id, resume_job_id, recipient_name } = body;
  if (!application_id || typeof application_id !== "string") {
    return Response.json({ error: "application_id is required" }, { status: 400 });
  }

  // Verify application belongs to user and has JD
  const { data: app, error: appErr } = await supabase
    .from("applications")
    .select("id, jd_text, company, role")
    .eq("id", application_id)
    .eq("user_id", user.id)
    .single();

  if (appErr || !app) {
    return Response.json({ error: "Application not found" }, { status: 404 });
  }
  if (!app.jd_text) {
    return Response.json({ error: "Application has no JD text" }, { status: 400 });
  }

  // Check if cover letter already exists
  const { data: existing } = await supabase
    .from("cover_letters")
    .select("id, status")
    .eq("application_id", application_id)
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (existing && existing.status === "generating") {
    return Response.json({ status: "already_generating", cover_letter_id: existing.id });
  }

  // Trigger worker
  if (!WORKER_URL) {
    return Response.json({ error: "Worker not configured" }, { status: 503 });
  }

  try {
    const workerRes = await fetch(`${WORKER_URL}/jobs/cover-letter`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(WORKER_SECRET ? { Authorization: `Bearer ${WORKER_SECRET}` } : {}),
      },
      body: JSON.stringify({
        application_id,
        user_id: user.id,
        resume_job_id: resume_job_id || "",
        recipient_name: recipient_name || "",
      }),
    });

    if (!workerRes.ok) {
      const detail = await workerRes.text().catch(() => "Unknown error");
      return Response.json({ error: `Worker error: ${detail}` }, { status: 502 });
    }
  } catch {
    return Response.json({ error: "Worker unreachable" }, { status: 503 });
  }

  return Response.json({ status: "generating", application_id }, { status: 202 });
}


export async function GET(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const application_id = searchParams.get("application_id");

  if (application_id) {
    // Fetch cover letter for specific application
    const { data, error } = await supabase
      .from("cover_letters")
      .select("*")
      .eq("application_id", application_id)
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (error) return Response.json({ error: error.message }, { status: 500 });
    return Response.json({ cover_letter: data });
  }

  // List all cover letters
  const { data, error } = await supabase
    .from("cover_letters")
    .select("id, application_id, company_name, role_name, status, created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ cover_letters: data ?? [] });
}
