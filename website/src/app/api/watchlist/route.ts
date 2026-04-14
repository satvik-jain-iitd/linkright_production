/**
 * /api/watchlist — CRUD for company watchlist
 *
 * GET  → list all watched companies for current user
 * POST → add company to watchlist
 */

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function GET() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { data, error } = await supabase
    .from("company_watchlist")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ watchlist: data ?? [] });
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`watchlist-create:${user.id}`, 20)) {
    return rateLimitResponse("watchlist addition");
  }

  let body: Record<string, unknown>;
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { company_name, company_slug, careers_url, ats_provider, positive_keywords, negative_keywords } = body;

  if (!company_name || typeof company_name !== "string") {
    return Response.json({ error: "company_name is required" }, { status: 400 });
  }
  if (!company_slug || typeof company_slug !== "string") {
    return Response.json({ error: "company_slug is required" }, { status: 400 });
  }

  // Dedup: same company_slug for this user
  const { data: existing } = await supabase
    .from("company_watchlist")
    .select("id, company_name")
    .eq("user_id", user.id)
    .eq("company_slug", (company_slug as string).trim().toLowerCase())
    .limit(1)
    .maybeSingle();

  if (existing) {
    return Response.json({
      error: `"${existing.company_name}" is already in your watchlist`,
      existing_id: existing.id,
    }, { status: 409 });
  }

  const row = {
    user_id: user.id,
    company_name: (company_name as string).trim(),
    company_slug: (company_slug as string).trim().toLowerCase(),
    careers_url: typeof careers_url === "string" ? careers_url.trim() : null,
    ats_provider: typeof ats_provider === "string" ? ats_provider.trim().toLowerCase() : null,
    positive_keywords: Array.isArray(positive_keywords)
      ? positive_keywords.filter((k): k is string => typeof k === "string")
      : [],
    negative_keywords: Array.isArray(negative_keywords)
      ? negative_keywords.filter((k): k is string => typeof k === "string")
      : [],
    is_active: true,
  };

  const { data, error } = await supabase
    .from("company_watchlist")
    .insert(row)
    .select("id, company_name, company_slug, ats_provider, is_active, created_at")
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ company: data }, { status: 201 });
}
