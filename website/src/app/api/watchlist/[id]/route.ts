/**
 * /api/watchlist/[id] — Update or delete a watched company
 *
 * PUT    → update company settings (keywords, active status, etc.)
 * DELETE → soft-delete (set is_active = false)
 */

import { createClient } from "@/lib/supabase/server";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;

  let body: Record<string, unknown>;
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const allowed: Record<string, unknown> = {};
  if (typeof body.company_name === "string") allowed.company_name = body.company_name.trim();
  if (typeof body.company_slug === "string") allowed.company_slug = body.company_slug.trim().toLowerCase();
  if (typeof body.careers_url === "string") allowed.careers_url = body.careers_url.trim();
  if (typeof body.ats_provider === "string") allowed.ats_provider = body.ats_provider.trim().toLowerCase();
  if (typeof body.is_active === "boolean") allowed.is_active = body.is_active;
  if (Array.isArray(body.positive_keywords)) {
    allowed.positive_keywords = body.positive_keywords.filter((k): k is string => typeof k === "string");
  }
  if (Array.isArray(body.negative_keywords)) {
    allowed.negative_keywords = body.negative_keywords.filter((k): k is string => typeof k === "string");
  }

  if (Object.keys(allowed).length === 0) {
    return Response.json({ error: "No valid fields to update" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("company_watchlist")
    .update(allowed)
    .eq("id", id)
    .eq("user_id", user.id)
    .select("id, company_name, company_slug, ats_provider, positive_keywords, negative_keywords, is_active")
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ error: "Company not found" }, { status: 404 });
  return Response.json({ company: data });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;

  // Soft-delete: deactivate rather than remove, preserves discovery history
  const { data, error } = await supabase
    .from("company_watchlist")
    .update({ is_active: false })
    .eq("id", id)
    .eq("user_id", user.id)
    .select("id, company_name")
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ error: "Company not found" }, { status: 404 });
  return Response.json({ deleted: data });
}
