// GET /api/nuggets/status
// Returns progress info for the current user's nugget extraction/embedding
// so the UI can show a progress bar and gate the "Customize resume" journey.
//
//   total_extracted  — rows in career_nuggets for this user
//   total_locked     — rows whose locked_at is set (new in v2)
//   total_embedded   — rows whose embedding column is populated
//   embed_queued     — locked but not yet embedded
//   ready            — legacy field: true when ≥90% of all extracted are embedded
//   profile_ready    — new field: true when all locked nuggets are embedded
//   last_activity_at — most recent created_at (for detecting stalls)
//
// Hard timeout: returns current state within 25s regardless of DB latency.
// The 163s hang from the Playwright session was caused by a Supabase
// connection that stalled mid-query. Promise.race ensures the client
// always gets a timely response.

import { createClient } from "@/lib/supabase/server";

const MAX_WAIT_MS = 25_000; // 25s — well within the 30s acceptance criterion

export const maxDuration = 30; // Vercel function timeout (seconds)

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  // Race DB queries against a hard timeout so we never hang >30s
  const timeout = new Promise<null>((resolve) =>
    setTimeout(() => resolve(null), MAX_WAIT_MS)
  );

  const dbQuery = (async () => {
    const [totalRes, lockedRes, embeddedRes, lockedEmbeddedRes, latestRes] = await Promise.all([
      supabase
        .from("career_nuggets")
        .select("id", { count: "exact", head: true })
        .eq("user_id", user.id),
      supabase
        .from("career_nuggets")
        .select("id", { count: "exact", head: true })
        .eq("user_id", user.id)
        .not("locked_at", "is", null),
      supabase
        .from("career_nuggets")
        .select("id", { count: "exact", head: true })
        .eq("user_id", user.id)
        .not("embedding", "is", null),
      // Numerator for profileReady: locked AND embedded
      supabase
        .from("career_nuggets")
        .select("id", { count: "exact", head: true })
        .eq("user_id", user.id)
        .not("locked_at", "is", null)
        .not("embedding", "is", null),
      supabase
        .from("career_nuggets")
        .select("created_at")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle(),
    ]);
    return { totalRes, lockedRes, embeddedRes, lockedEmbeddedRes, latestRes };
  })();

  const result = await Promise.race([dbQuery, timeout]);

  if (result === null) {
    // Timed out — return a safe partial response so polling continues
    return Response.json(
      {
        total_extracted: 0,
        total_locked: 0,
        total_embedded: 0,
        embed_queued: 0,
        ready: false,
        profile_ready: false,
        last_activity_at: null,
        timed_out: true,
      },
      { status: 200 }
    );
  }

  const { totalRes, lockedRes, embeddedRes, lockedEmbeddedRes, latestRes } = result;
  const totalExtracted = totalRes.count ?? 0;
  const totalLocked = lockedRes.count ?? 0;
  const totalEmbedded = embeddedRes.count ?? 0;
  // Count of nuggets that are BOTH locked AND have an embedding.
  // This is the only correct numerator for profileReady — it is immune to
  // pre-existing embeddings from before the lock model was introduced.
  const lockedAndEmbedded = lockedEmbeddedRes.count ?? 0;

  // Legacy ready — preserves existing dashboard/jobs/enrich page semantics
  const ratio = totalExtracted > 0 ? totalEmbedded / totalExtracted : 0;
  const ready = totalExtracted > 0 && ratio >= 0.9;

  // Profile-step ready — correct semantic:
  //   true  iff  every locked nugget has been embedded (ratio == 1.0)
  //   false when totalLocked == 0 (nothing locked yet)
  //   false when a user has pre-existing embeddings but new locked ones aren't done yet
  const profileReady = totalLocked > 0 && lockedAndEmbedded >= totalLocked;

  return Response.json({
    total_extracted: totalExtracted,
    total_locked: totalLocked,
    total_embedded: totalEmbedded,
    embed_queued: Math.max(0, totalLocked - totalEmbedded),
    ready,
    profile_ready: profileReady,
    last_activity_at: latestRes.data?.created_at ?? null,
  });
}
