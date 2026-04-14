/**
 * POST /api/oracle/session-close
 *
 * Custom GPT proxy — mark a coaching session as complete.
 * Called by Custom GPT once at the end of the session (Phase 5),
 * OR by the Claude Code interview-coach skill using an LR-XXXXXXXX session token.
 *
 * Auth (two paths):
 *   Path 1 — Custom GPT: Bearer CUSTOM_GPT_SECRET in Authorization header
 *   Path 2 — Claude skill: valid LR-XXXXXXXX token in body (no auth header needed)
 *
 * Body: { token: string, user_id?: string }
 *   user_id is optional when using Path 2 (resolved from token in Supabase)
 *
 * Returns: { ok, error? }
 *
 * To update session-close logic: edit oracle-backend/main.py (/lifeos/session-close) only.
 * To update this proxy: edit this file only.
 */

import { createServiceClient } from "@/lib/supabase/service";

const CUSTOM_GPT_SECRET = process.env.CUSTOM_GPT_SECRET!;
const ORACLE_URL = process.env.ORACLE_BACKEND_URL!;
const ORACLE_SECRET = process.env.ORACLE_BACKEND_SECRET!;

function serviceClient() {
  return createServiceClient();
}

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
  let body: { token?: string; user_id?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { authorized, resolved_user_id } = await resolveAuth(request, body.token);
  if (!authorized) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { token } = body;
  const user_id = resolved_user_id ?? body.user_id;

  if (!token || !user_id) {
    return Response.json({ error: "token and user_id are required" }, { status: 400 });
  }

  // Mark session complete in Supabase — best-effort, non-blocking
  serviceClient()
    .from("profile_tokens")
    .update({ used_at: new Date().toISOString() })
    .eq("token", token)
    .then(undefined, () => {});

  try {
    const res = await fetch(`${ORACLE_URL}/lifeos/session-close`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ORACLE_SECRET}`,
      },
      body: JSON.stringify({ token, user_id }),
      signal: AbortSignal.timeout(8000),
    });

    const data = await res.json();

    if (!res.ok) {
      return Response.json(
        { ok: false, error: data.detail ?? "Session close failed" },
        { status: res.status }
      );
    }

    // ── Post-close: create career_chunks from nuggets + trigger embedding ──
    // Fire-and-forget: don't block the response
    createChunksFromNuggets(user_id).catch((err) =>
      console.error("[session-close] chunk creation failed:", err)
    );
    triggerNuggetEmbedding(user_id).catch((err) =>
      console.error("[session-close] embed trigger failed:", err)
    );

    return Response.json({ ok: true });
  } catch (err) {
    console.error("session-close proxy error:", err);
    return Response.json({ ok: false, error: "Oracle backend unavailable" }, { status: 502 });
  }
}

// ── career_chunks creation from career_nuggets ────────────────────────────
// After TruthEngine interview, nuggets exist but career_chunks may be empty.
// Text search, career_text reconstruction, and resume generation all read
// from career_chunks. This function synthesizes chunks from nuggets.

async function createChunksFromNuggets(userId: string) {
  const sb = serviceClient();

  // Skip if user already has career_chunks (from manual paste in onboarding step 2)
  const { count: existingChunks } = await sb
    .from("career_chunks")
    .select("id", { count: "exact", head: true })
    .eq("user_id", userId);
  if ((existingChunks ?? 0) > 0) {
    console.log("[session-close] user already has career_chunks, skipping synthesis");
    return;
  }

  // Fetch all career_nuggets for this user
  const { data: nuggets } = await sb
    .from("career_nuggets")
    .select("nugget_text, answer, company, role, section_type")
    .eq("user_id", userId)
    .order("created_at", { ascending: true });

  if (!nuggets || nuggets.length === 0) {
    console.log("[session-close] no nuggets found, skipping chunk creation");
    return;
  }

  // Group by company + role for structured text
  const grouped = new Map<string, string[]>();
  for (const n of nuggets) {
    const key = [n.company, n.role].filter(Boolean).join(" - ") || "General";
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(n.answer || n.nugget_text);
  }

  // Format as structured text blocks and chunk at ~1000 chars
  const fullText = Array.from(grouped.entries())
    .map(([heading, answers]) => `## ${heading}\n\n${answers.map((a) => `• ${a}`).join("\n")}`)
    .join("\n\n");

  // Simple chunking: split at ~1000 char boundaries on paragraph breaks
  const MAX_CHUNK = 1000;
  const paragraphs = fullText.split("\n\n");
  const chunks: string[] = [];
  let current = "";

  for (const para of paragraphs) {
    if (current.length + para.length + 2 > MAX_CHUNK && current.length > 0) {
      chunks.push(current.trim());
      current = "";
    }
    current += (current ? "\n\n" : "") + para;
  }
  if (current.trim()) chunks.push(current.trim());

  // Insert chunks into career_chunks
  const rows = chunks.map((text, i) => ({
    user_id: userId,
    chunk_index: i,
    chunk_text: text,
    is_active: true,
  }));

  const { error } = await sb.from("career_chunks").insert(rows);
  if (error) {
    console.error("[session-close] chunk insert failed:", error.message);
  } else {
    console.log(`[session-close] created ${rows.length} career_chunks for user ${userId.slice(0, 8)}…`);
  }
}

// ── Trigger nugget embedding via worker ───────────────────────────────────
// Calls the worker's /nuggets/embed endpoint to generate Jina embeddings
// for career_nuggets that don't have them yet.

async function triggerNuggetEmbedding(userId: string) {
  const workerUrl = process.env.WORKER_URL;
  const workerSecret = process.env.WORKER_SECRET;

  if (!workerUrl || workerUrl.includes("localhost")) {
    console.log("[session-close] WORKER_URL not set or localhost — skipping embed trigger");
    return;
  }

  try {
    await fetch(`${workerUrl}/nuggets/embed`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(workerSecret ? { Authorization: `Bearer ${workerSecret}` } : {}),
      },
      body: JSON.stringify({ user_id: userId }),
      signal: AbortSignal.timeout(5000),
    });
    console.log("[session-close] triggered nugget embedding for user", userId.slice(0, 8));
  } catch (err) {
    // Non-critical — embeddings improve JD matching but aren't required
    console.warn("[session-close] embed trigger failed (non-critical):", err instanceof Error ? err.message : err);
  }
}
