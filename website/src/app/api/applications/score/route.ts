/**
 * /api/applications/score — Trigger job scoring + fetch score results
 *
 * POST → trigger scoring for an application (calls worker /jobs/score)
 * GET  → fetch score for an application (query param: application_id)
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

  // Verify the application belongs to this user and has JD text
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
    return Response.json({ error: "Application has no JD text — add a job description first" }, { status: 400 });
  }

  // Check if score already exists (avoid duplicate scoring)
  const { data: existing } = await supabase
    .from("job_scores")
    .select("id, overall_grade")
    .eq("application_id", application_id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (existing) {
    return Response.json({
      status: "already_scored",
      score_id: existing.id,
      grade: existing.overall_grade,
    });
  }

  // Trigger worker scoring (fire-and-forget)
  if (!WORKER_URL) {
    return Response.json({ error: "Worker not configured" }, { status: 503 });
  }

  try {
    const workerRes = await fetch(`${WORKER_URL}/jobs/score`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(WORKER_SECRET ? { Authorization: `Bearer ${WORKER_SECRET}` } : {}),
      },
      body: JSON.stringify({
        application_id,
        user_id: user.id,
      }),
    });

    if (!workerRes.ok) {
      const detail = await workerRes.text().catch(() => "Unknown error");
      return Response.json({ error: `Worker error: ${detail}` }, { status: 502 });
    }
  } catch (e) {
    return Response.json({ error: "Worker unreachable" }, { status: 503 });
  }

  return Response.json({ status: "scoring", application_id }, { status: 202 });
}


export async function GET(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const application_id = searchParams.get("application_id");

  if (!application_id) {
    // Return all scores for this user
    const { data, error } = await supabase
      .from("job_scores")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false });

    if (error) return Response.json({ error: error.message }, { status: 500 });
    return Response.json({ scores: data ?? [] });
  }

  // Return score for specific application
  const { data, error } = await supabase
    .from("job_scores")
    .select("*")
    .eq("application_id", application_id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ score: null, status: "not_scored" });
  return Response.json({ score: data });
}
