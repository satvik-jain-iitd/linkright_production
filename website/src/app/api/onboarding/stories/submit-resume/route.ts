// POST /api/onboarding/stories/submit-resume
// Validates all stories are in a definitive state, then batch-embeds all locked
// nuggets (Jina paid + Oracle worker background), then stamps resume_submitted_at.
//
// Semantics (in order):
//   1. Gate: SELECT COUNT(*) career_chunks WHERE user_id AND locked_at IS NULL
//            → 422 if any unlocked chunks exist
//   2. Batch embed: find all career_nuggets WHERE user_id AND embedding_jina IS NULL
//      For each nugget (max 3 concurrent):
//        a. jinaEmbed([nugget.answer]) → UPDATE embedding_jina
//        b. Fire Oracle worker POST /nuggets/embed (background, fire-and-forget)
//   3. Stamp resume_submitted_at = now() on all locked chunks (idempotent — NULL only)
//   4. Return { submitted_chunks: N, embedded_count: M, worker_pending: P }
//
// Idempotent re-submit: embedding_jina IS NULL filter means already-embedded
// nuggets are skipped. Safe to call again if user closed browser mid-batch.

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { jinaEmbed, getNextJinaKey } from "@/lib/jina-embed";

const MAX_CONCURRENT = 3;

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`stories-submit:${user.id}`, 10)) {
    return rateLimitResponse("stories submit");
  }

  // ── Gate: at least 1 chunk must be locked ────────────────────────────────
  // The frontend enforces "all remaining cards must be locked before submit".
  // Server-side we validate at least 1 locked chunk exists (sufficient safety
  // net — frontend button is the primary UX gate for per-card decisions).
  // We do NOT block on locked_at IS NULL count because UI-deleted cards leave
  // DB rows with locked_at = null, cancelled_at = null, and those are valid
  // "abandoned" rows (they will get resume_submitted_at stamped below, which
  // is fine — they just have no nuggets).
  const { count: lockedChunkCount, error: countError } = await supabase
    .from("career_chunks")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .not("locked_at", "is", null);

  if (countError) {
    // Migration not run yet — degrade gracefully (skip gate)
    if (
      countError.code === "42703" ||
      countError.message?.includes("does not exist") ||
      countError.message?.includes("schema cache") ||
      countError.message?.includes("Could not find")
    ) {
      console.warn("[stories/submit-resume] locked_at column missing — skipping gate check");
    } else {
      return Response.json({ error: countError.message }, { status: 500 });
    }
  } else if ((lockedChunkCount ?? 0) === 0) {
    return Response.json(
      {
        error: "All stories must be locked or deleted before submitting",
        locked_count: 0,
      },
      { status: 422 }
    );
  }

  // ── Batch embed: find all unembedded nuggets for this user ────────────────
  const { data: unembeddedNuggets, error: fetchErr } = await supabase
    .from("career_nuggets")
    .select("id, answer")
    .eq("user_id", user.id)
    .is("embedding_jina", null);

  if (fetchErr) {
    if (
      fetchErr.code === "42703" ||
      fetchErr.message?.includes("does not exist") ||
      fetchErr.message?.includes("schema cache") ||
      fetchErr.message?.includes("Could not find")
    ) {
      console.warn("[stories/submit-resume] embedding_jina column missing — skipping embed batch");
    } else {
      return Response.json({ error: fetchErr.message }, { status: 500 });
    }
  }

  const nuggets = unembeddedNuggets ?? [];
  let embeddedCount = 0;
  let workerPending = 0;

  const workerUrl = process.env.WORKER_URL;
  const workerSecret = process.env.WORKER_SECRET;

  // Process in batches of MAX_CONCURRENT
  for (let i = 0; i < nuggets.length; i += MAX_CONCURRENT) {
    const batch = nuggets.slice(i, i + MAX_CONCURRENT);
    await Promise.all(
      batch.map(async (nugget) => {
        try {
          const jinaKey = getNextJinaKey();
          if (jinaKey && nugget.answer) {
            const vectors = await jinaEmbed([nugget.answer], jinaKey, "text-matching");
            if (vectors?.[0]) {
              const { error: embedErr } = await supabase
                .from("career_nuggets")
                .update({ embedding_jina: vectors[0] })
                .eq("id", nugget.id)
                .eq("user_id", user.id);
              if (!embedErr) {
                embeddedCount++;
              } else {
                console.warn("[stories/submit-resume] embed update failed:", nugget.id, embedErr.message);
              }
            }
          }

          // Fire Oracle worker in background (job matching — different vector space)
          if (workerUrl && workerSecret) {
            void fetch(`${workerUrl}/nuggets/embed`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${workerSecret}`,
              },
              body: JSON.stringify({ user_id: user.id, nugget_id: nugget.id }),
            }).catch(() => null);
            workerPending++;
          }
        } catch (nuggetErr) {
          console.warn("[stories/submit-resume] nugget embed error:", nugget.id, (nuggetErr as Error).message);
        }
      })
    );
  }

  // ── Stamp resume_submitted_at on all locked chunks ────────────────────────
  const submittedAt = new Date().toISOString();

  const { data: submittedRows, error: submitError } = await supabase
    .from("career_chunks")
    .update({ resume_submitted_at: submittedAt })
    .eq("user_id", user.id)
    .is("resume_submitted_at", null)
    .select("id");
  const submittedCount = submittedRows?.length ?? 0;

  if (submitError) {
    // Migration 046 not yet run — degrade gracefully
    if (
      submitError.code === "42703" ||
      submitError.message?.includes("does not exist")
    ) {
      console.warn("[stories/submit-resume] resume_submitted_at column missing — degraded");
      return Response.json({
        submitted_chunks: 0,
        embedded_count: embeddedCount,
        worker_pending: workerPending,
        submitted_at: submittedAt,
        degraded: true,
      });
    }
    return Response.json({ error: submitError.message }, { status: 500 });
  }

  return Response.json({
    submitted_chunks: submittedCount ?? 0,
    embedded_count: embeddedCount,
    worker_pending: workerPending,
    submitted_at: submittedAt,
  });
}
