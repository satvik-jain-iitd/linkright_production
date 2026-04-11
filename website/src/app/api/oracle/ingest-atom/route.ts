/**
 * POST /api/oracle/ingest-atom
 *
 * Custom GPT proxy — ingest one confirmed career atom into the knowledge graph.
 * Called by Custom GPT after user explicitly confirms each achievement.
 *
 * Auth: Bearer CUSTOM_GPT_SECRET
 * Body: { token: string, user_id: string, atom: CareerAtom }
 * Returns: { ok, conflict?, existing_atom_id?, atom_id?, error? }
 *
 * To update atom schema: edit knowledge/01_atom_schema.json only.
 * To update ingest logic: edit oracle-backend/lifeos/ingest.py only.
 * To update this proxy behavior: edit this file only.
 */

import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

const CUSTOM_GPT_SECRET = process.env.CUSTOM_GPT_SECRET!;
const ORACLE_URL = process.env.ORACLE_BACKEND_URL!;
const ORACLE_SECRET = process.env.ORACLE_BACKEND_SECRET!;

function verifyAuth(request: Request): boolean {
  const auth = request.headers.get("authorization") ?? "";
  return auth === `Bearer ${CUSTOM_GPT_SECRET}`;
}

export async function POST(request: Request) {
  if (!verifyAuth(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: { token?: string; user_id?: string; atom?: Record<string, unknown> };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { token, user_id, atom } = body;
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

    return Response.json(data);
  } catch (err) {
    return Response.json(
      { ok: false, error: `Service unavailable: ${err instanceof Error ? err.message : "unknown"}` },
      { status: 503 }
    );
  }
}
