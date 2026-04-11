// DELETE: Remove a key
// PATCH: Update priority, label, or active status

// [BYOK-REMOVED] Supabase + rate-limit imports no longer needed
// import { createClient } from "@/lib/supabase/server";
// import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function DELETE() {
  // [BYOK-REMOVED] API key management disabled — server manages keys
  /* [BYOK-REMOVED]
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`keys-delete:${user.id}`, 10)) {
    return rateLimitResponse("key deletion");
  }

  const { error } = await supabase
    .from("user_api_keys")
    .delete()
    .eq("id", id)
    .eq("user_id", user.id); // RLS double-check

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ deleted: true });
  */
  return Response.json({ error: "API key management is handled server-side" }, { status: 410 });
}

export async function PATCH() {
  // [BYOK-REMOVED] API key management disabled — server manages keys
  /* [BYOK-REMOVED]
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`keys-patch:${user.id}`, 10)) {
    return rateLimitResponse("key update");
  }

  const body = await request.json();
  const updates: Record<string, unknown> = {};

  if (body.label !== undefined) updates.label = body.label;
  if (body.priority !== undefined) updates.priority = body.priority;
  if (body.is_active !== undefined) updates.is_active = body.is_active;

  if (Object.keys(updates).length === 0) {
    return Response.json(
      { error: "No valid fields to update" },
      { status: 400 }
    );
  }

  const { data, error } = await supabase
    .from("user_api_keys")
    .update(updates)
    .eq("id", id)
    .eq("user_id", user.id)
    .select("id, provider, label, priority, is_active")
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ key: data });
  */
  return Response.json({ error: "API key management is handled server-side" }, { status: 410 });
}
