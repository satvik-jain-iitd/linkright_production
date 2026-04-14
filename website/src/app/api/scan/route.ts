/**
 * /api/scan — Trigger and check scan status
 *
 * POST → trigger a new scan for all active watchlist companies
 * GET  → check scan status by scan_id (query param)
 */

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  // Max 1 scan trigger per 5 minutes per user
  if (!rateLimit(`scan-trigger:${user.id}`, 1, 300_000)) {
    return rateLimitResponse("scan trigger (max 1 per 5 minutes)");
  }

  // Get user's active watchlist companies
  const { data: companies, error: watchErr } = await supabase
    .from("company_watchlist")
    .select("id, company_name, company_slug, ats_provider, positive_keywords, negative_keywords")
    .eq("user_id", user.id)
    .eq("is_active", true);

  if (watchErr) return Response.json({ error: watchErr.message }, { status: 500 });
  if (!companies || companies.length === 0) {
    return Response.json({ error: "No active companies in watchlist" }, { status: 400 });
  }

  // Read worker URL from env
  const workerUrl = process.env.WORKER_URL;
  if (!workerUrl) {
    return Response.json({ error: "Scanner service not configured" }, { status: 503 });
  }

  let body: Record<string, unknown> = {};
  try { body = await request.json(); } catch { /* empty body OK */ }

  // Call worker /scan endpoint
  try {
    const resp = await fetch(`${workerUrl}/jobs/scan`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(process.env.WORKER_SECRET
          ? { Authorization: `Bearer ${process.env.WORKER_SECRET}` }
          : {}),
      },
      body: JSON.stringify({
        user_id: user.id,
        companies,
        callback_url: body.callback_url || null,
      }),
    });

    if (!resp.ok) {
      const err = await resp.text();
      return Response.json({ error: `Scanner error: ${err}` }, { status: resp.status });
    }

    const result = await resp.json();
    return Response.json({
      scan_id: result.scan_id ?? null,
      companies_queued: companies.length,
      status: "running",
    });
  } catch (err) {
    return Response.json(
      { error: `Failed to reach scanner: ${err instanceof Error ? err.message : "unknown"}` },
      { status: 502 }
    );
  }
}

export async function GET(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const url = new URL(request.url);
  const scanId = url.searchParams.get("scan_id");

  if (!scanId) {
    // Return latest scan summary: count of discoveries by status
    const { data, error } = await supabase
      .from("job_discoveries")
      .select("status", { count: "exact" })
      .eq("user_id", user.id);

    if (error) return Response.json({ error: error.message }, { status: 500 });

    const counts = { new: 0, saved: 0, dismissed: 0, applied: 0, total: data?.length ?? 0 };
    for (const row of data ?? []) {
      const s = row.status as keyof typeof counts;
      if (s in counts) counts[s]++;
    }

    // Get last scan time from watchlist
    const { data: latest } = await supabase
      .from("company_watchlist")
      .select("last_scanned_at")
      .eq("user_id", user.id)
      .not("last_scanned_at", "is", null)
      .order("last_scanned_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    return Response.json({
      last_scanned_at: latest?.last_scanned_at ?? null,
      counts,
    });
  }

  // If scan_id provided, check with worker
  const workerUrl = process.env.WORKER_URL;
  if (!workerUrl) {
    return Response.json({ error: "Scanner service not configured" }, { status: 503 });
  }

  try {
    const resp = await fetch(`${workerUrl}/jobs/scan/status?scan_id=${scanId}`, {
      headers: process.env.WORKER_SECRET
        ? { Authorization: `Bearer ${process.env.WORKER_SECRET}` }
        : {},
    });
    if (!resp.ok) return Response.json({ error: "Scan not found" }, { status: 404 });
    const result = await resp.json();
    return Response.json(result);
  } catch {
    return Response.json({ error: "Failed to reach scanner" }, { status: 502 });
  }
}
