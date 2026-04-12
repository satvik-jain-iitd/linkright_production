/**
 * POST /api/oracle/ingest-atom
 *
 * Custom GPT proxy — ingest one confirmed career atom into the knowledge graph.
 * Called by Custom GPT after user explicitly confirms each achievement,
 * OR by the Claude Code interview-coach skill using an LR-XXXXXXXX session token.
 *
 * Auth (two paths):
 *   Path 1 — Custom GPT: Bearer CUSTOM_GPT_SECRET in Authorization header
 *   Path 2 — Claude skill: valid LR-XXXXXXXX token in body (no auth header needed)
 *
 * Body: { token: string, user_id?: string, atom: CareerAtom }
 *   user_id is optional when using Path 2 (resolved from token in Supabase)
 *
 * Returns: { ok, conflict?, existing_atom_id?, atom_id?, user_id?, error? }
 *
 * To update atom schema: edit knowledge/01_atom_schema.json only.
 * To update ingest logic: edit oracle-backend/lifeos/ingest.py only.
 * To update this proxy behavior: edit this file only.
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

/**
 * Resolves auth via CUSTOM_GPT_SECRET (Path 1) or LR-XXXXXXXX session token (Path 2).
 * Returns { authorized, resolved_user_id } — resolved_user_id is set on Path 2.
 */
async function resolveAuth(
  request: Request,
  token?: string
): Promise<{ authorized: boolean; resolved_user_id?: string }> {
  const auth = request.headers.get("authorization") ?? "";

  // Path 1: Custom GPT secret — existing behavior, unchanged
  if (auth === `Bearer ${CUSTOM_GPT_SECRET}`) {
    return { authorized: true };
  }

  // Path 2: LR-XXXXXXXX session token — for Claude Code interview-coach skill
  if (token?.startsWith("LR-")) {
    const { data } = await serviceClient()
      .from("profile_tokens")
      .select("user_id")
      .eq("token", token)
      .gt("expires_at", new Date().toISOString())
      .single();
    if (data) return { authorized: true, resolved_user_id: data.user_id };
  }

  return { authorized: false };
}

export async function POST(request: Request) {
  let body: { token?: string; user_id?: string; atom?: Record<string, unknown> };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { authorized, resolved_user_id } = await resolveAuth(request, body.token);
  if (!authorized) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { token, atom } = body;
  const user_id = resolved_user_id ?? body.user_id;

  if (!token || !user_id || !atom) {
    return Response.json({ error: "token, user_id, and atom are required" }, { status: 400 });
  }

  // Rate limit: max 30 ingestions per hour per user (generous for a full session)
  if (!rateLimit(`gpt-ingest:${user_id}`, 30, 3600_000)) {
    return rateLimitResponse("atom ingestion");
  }

  try {
    const res = await fetch(`${ORACLE_URL}/lifeos/ingest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ORACLE_SECRET}`,
      },
      body: JSON.stringify({ token, user_id, atom }),
      signal: AbortSignal.timeout(15000), // embed + Neo4j write can take a few seconds
    });

    const data = await res.json();

    if (!res.ok) {
      return Response.json(
        { ok: false, error: data.detail ?? "Oracle ingest failed" },
        { status: res.status }
      );
    }

    // Increment atoms_saved counter for new atoms (not conflicts/duplicates)
    if (data.ok && !data.conflict) {
      serviceClient().rpc("increment_atoms_saved", { p_token: token }).then(undefined, () => {});
    }

    // Include user_id in response so Claude Code skill can use it for session-close
    return Response.json({ ...data, user_id });
  } catch (err) {
    return Response.json(
      { ok: false, error: `Service unavailable: ${err instanceof Error ? err.message : "unknown"}` },
      { status: 503 }
    );
  }
}
