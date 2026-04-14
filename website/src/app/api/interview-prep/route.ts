/**
 * /api/interview-prep — Trigger + fetch interview prep
 *
 * POST → trigger interview prep generation (calls worker /jobs/interview-prep)
 * GET  → fetch prep for an application (query: application_id)
 */

import { createClient } from "@/lib/supabase/server";

const WORKER_URL = process.env.WORKER_URL;
const WORKER_SECRET = process.env.WORKER_SECRET;

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  let body: { application_id?: string };
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { application_id } = body;
  if (!application_id || typeof application_id !== "string") {
    return Response.json({ error: "application_id is required" }, { status: 400 });
  }

  // Verify application belongs to user
  const { data: app, error: appErr } = await supabase
    .from("applications")
    .select("id, jd_text")
    .eq("id", application_id)
    .eq("user_id", user.id)
    .single();

  if (appErr || !app) {
    return Response.json({ error: "Application not found" }, { status: 404 });
  }
  if (!app.jd_text) {
    return Response.json({ error: "Application has no JD text" }, { status: 400 });
  }

  // Check if prep already exists
  const { data: existing } = await supabase
    .from("interview_preps")
    .select("id")
    .eq("application_id", application_id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (existing) {
    return Response.json({ status: "already_exists", prep_id: existing.id });
  }

  // Trigger worker
  if (!WORKER_URL) {
    return Response.json({ error: "Worker not configured" }, { status: 503 });
  }

  try {
    const workerRes = await fetch(`${WORKER_URL}/jobs/interview-prep`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(WORKER_SECRET ? { Authorization: `Bearer ${WORKER_SECRET}` } : {}),
      },
      body: JSON.stringify({ application_id, user_id: user.id }),
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

  if (!application_id) {
    return Response.json({ error: "application_id query param required" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("interview_preps")
    .select("*")
    .eq("application_id", application_id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ prep: data });
}
