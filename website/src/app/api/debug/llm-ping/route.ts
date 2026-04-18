// Diagnostic proxy for linkright-7jz — forwards to worker /debug/llm-ping using
// the server-side WORKER_SECRET so we can see provider reachability from Render.
// Auth: requires logged-in user; admin-only check TBD (acceptable for now since
// it only reports latencies, not keys).

import { createClient } from "@/lib/supabase/server";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const WORKER_URL = process.env.WORKER_URL;
  const WORKER_SECRET = process.env.WORKER_SECRET;
  if (!WORKER_URL || !WORKER_SECRET) {
    return Response.json({ error: "Worker URL/secret not configured" }, { status: 500 });
  }

  const res = await fetch(`${WORKER_URL}/debug/llm-ping`, {
    headers: { Authorization: `Bearer ${WORKER_SECRET}` },
    cache: "no-store",
  });
  const text = await res.text();
  let body: unknown;
  try {
    body = JSON.parse(text);
  } catch {
    body = { raw: text };
  }
  return Response.json({ http: res.status, body }, { status: 200 });
}
