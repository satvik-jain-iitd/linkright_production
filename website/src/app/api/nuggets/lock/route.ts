// POST /api/nuggets/lock
// Locks or unlocks a single nugget.
//
// Body: { id: string, action: "lock" | "unlock" }
//
// Lock:   sets locked_at = now(), fires worker embed for THAT nugget only.
// Unlock: clears locked_at + embedding (so re-locking re-embeds).

import { createClient } from "@/lib/supabase/server";

const WORKER_URL = process.env.WORKER_URL ?? "";
const WORKER_SECRET = process.env.WORKER_SECRET ?? "";

async function fireNuggetEmbed(userId: string, nuggetId: string) {
  if (!WORKER_URL || !WORKER_SECRET) return;
  try {
    await fetch(`${WORKER_URL}/nuggets/embed`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      // Provide nugget_id so worker embeds this one nugget only.
      // Falls back to user_id sweep if worker doesn't support nugget_id.
      body: JSON.stringify({ user_id: userId, nugget_id: nuggetId }),
    });
  } catch {
    // Best-effort — do not bubble up
  }
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  let body: { id?: string; action?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { id, action } = body;
  if (!id || typeof id !== "string") {
    return Response.json({ error: "id is required" }, { status: 400 });
  }
  if (action !== "lock" && action !== "unlock") {
    return Response.json({ error: "action must be lock or unlock" }, { status: 400 });
  }

  // Check ownership
  const { data: nugget } = await supabase
    .from("career_nuggets")
    .select("id, user_id, locked_at, profile_submitted_at")
    .eq("id", id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (!nugget) {
    return Response.json({ error: "Nugget not found" }, { status: 404 });
  }

  // Guard: if profile was submitted, reject all mutations.
  if (nugget.profile_submitted_at) {
    return Response.json(
      { error: "Profile already submitted — nuggets are locked." },
      { status: 409 }
    );
  }

  if (action === "lock") {
    const { data: updated, error } = await supabase
      .from("career_nuggets")
      .update({ locked_at: new Date().toISOString() })
      .eq("id", id)
      .eq("user_id", user.id)
      .select("id, locked_at")
      .maybeSingle();

    if (error) return Response.json({ error: error.message }, { status: 500 });

    // Fire embed immediately — best effort, non-blocking
    fireNuggetEmbed(user.id, id);

    return Response.json({ nugget: updated });
  } else {
    // unlock — clear locked_at + embedding so re-lock re-embeds
    const { data: updated, error } = await supabase
      .from("career_nuggets")
      .update({ locked_at: null, embedding: null })
      .eq("id", id)
      .eq("user_id", user.id)
      .select("id, locked_at")
      .maybeSingle();

    if (error) return Response.json({ error: error.message }, { status: 500 });

    return Response.json({ nugget: updated });
  }
}
