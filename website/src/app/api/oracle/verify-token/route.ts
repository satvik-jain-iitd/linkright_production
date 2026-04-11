/**
 * POST /api/oracle/verify-token
 *
 * Custom GPT proxy — verifies a profile token and returns the user_id.
 * Called by the Custom GPT at the start of every career coaching session.
 *
 * Auth: Bearer CUSTOM_GPT_SECRET (stored in GPT Action config, never exposed to user)
 * Body: { token: string }
 * Returns: { valid, user_id?, session_active?, existing_atom_count?, error? }
 *
 * To update behavior: edit this file only.
 */

import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

const CUSTOM_GPT_SECRET = process.env.CUSTOM_GPT_SECRET!;
const ORACLE_URL = process.env.ORACLE_BACKEND_URL!;
const ORACLE_SECRET = process.env.ORACLE_BACKEND_SECRET!;

function serviceClient() {
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

function verifyAuth(request: Request): boolean {
  const auth = request.headers.get("authorization") ?? "";
  return auth === `Bearer ${CUSTOM_GPT_SECRET}`;
}

export async function POST(request: Request) {
  if (!verifyAuth(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: { token?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { token } = body;
  if (!token || typeof token !== "string") {
    return Response.json({ error: "token is required" }, { status: 400 });
  }

  // Rate limit: 5 verify attempts per token per hour
  if (!rateLimit(`gpt-verify:${token}`, 5, 3600_000)) {
    return rateLimitResponse("token verification");
  }

  const supabase = serviceClient();

  // Validate token
  const { data, error } = await supabase
    .from("profile_tokens")
    .select("id, user_id, expires_at, used_at, atoms_saved")
    .eq("token", token)
    .single();

  if (error || !data) {
    return Response.json({ valid: false, error: "Token not found" }, { status: 404 });
  }

  if (new Date(data.expires_at) < new Date()) {
    return Response.json({ valid: false, error: "Token expired. Please generate a new code from your LinkRight dashboard." }, { status: 401 });
  }

  // Fetch existing atom count from Oracle for orientation
  let existing_atom_count = 0;
  try {
    const atomsRes = await fetch(
      `${ORACLE_URL}/lifeos/existing-atoms?user_id=${encodeURIComponent(data.user_id)}`,
      {
        headers: { Authorization: `Bearer ${ORACLE_SECRET}` },
        signal: AbortSignal.timeout(6000),
      }
    );
    if (atomsRes.ok) {
      const { count } = await atomsRes.json();
      existing_atom_count = count ?? 0;
    }
  } catch {
    // Oracle unavailable — continue without atom count
  }

  return Response.json({
    valid: true,
    user_id: data.user_id,
    session_active: !data.used_at,
    existing_atom_count,
    atoms_saved_this_session: data.atoms_saved,
  });
}
