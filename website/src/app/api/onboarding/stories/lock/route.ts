// POST /api/onboarding/stories/lock
// Locks a single career_chunks row, runs enrich-chunk for it (creating nuggets
// in career_nuggets with source_chunk_id set), then fires worker embed per nugget.
//
// Body: { chunk_id: string }
//
// Semantics:
//   1. Stamp career_chunks.locked_at = now(), clear cancelled_at if set (re-lock)
//   2. Run enrich-chunk inline — creates career_nuggets rows with source_chunk_id = chunk_id
//   3. Fire worker POST /nuggets/embed (background — UI doesn't wait) [Oracle path]
//   4. Fire inline Jina embed for resume customization use case (sub-second, fire-and-forget)
//   5. Return immediately with { chunk_id, locked_at }
//
// 409 if resume_submitted_at is already set (session frozen).

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { enrichChunkInline, ENRICH_FALLBACK } from "@/lib/enrich-chunk";
import { jinaEmbed, getNextJinaKey } from "@/lib/jina-embed";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`stories-lock:${user.id}`, 30)) {
    return rateLimitResponse("stories lock");
  }

  let body: { chunk_id?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { chunk_id } = body;
  if (!chunk_id || typeof chunk_id !== "string") {
    return Response.json({ error: "chunk_id is required" }, { status: 400 });
  }

  // Check ownership + current state
  const { data: chunk } = await supabase
    .from("career_chunks")
    .select("id, user_id, chunk_text, metadata, locked_at, resume_submitted_at")
    .eq("id", chunk_id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (!chunk) {
    return Response.json({ error: "Chunk not found" }, { status: 404 });
  }

  // Guard: if resume was submitted, reject all mutations
  if (chunk.resume_submitted_at) {
    return Response.json(
      { error: "Resume already submitted — stories are frozen." },
      { status: 409 }
    );
  }

  // Stamp locked_at + clear cancelled_at (re-lock after an unlock)
  const lockedAt = new Date().toISOString();
  const { data: updated, error: updateError } = await supabase
    .from("career_chunks")
    .update({ locked_at: lockedAt, cancelled_at: null })
    .eq("id", chunk_id)
    .eq("user_id", user.id)
    .select("id, locked_at")
    .maybeSingle();

  if (updateError) {
    // Column may not exist yet (migration 046/050 not run) — degrade gracefully
    if (
      updateError.code === "42703" ||
      updateError.message?.includes("does not exist") || updateError.message?.includes("schema cache") || updateError.message?.includes("Could not find")
    ) {
      console.warn("[stories/lock] locked_at/cancelled_at column missing — migration not yet run");
      return Response.json({ chunk: { id: chunk_id, locked_at: lockedAt }, degraded: true });
    }
    return Response.json({ error: updateError.message }, { status: 500 });
  }

  // ── Background pipeline: enrich → create nuggets → embed ──────────────────
  // Fire-and-forget. UI polls /api/nuggets/list?embedded=true to see progress.
  const chunkText: string = chunk.chunk_text ?? "";
  const metadata = (chunk.metadata ?? {}) as Record<string, unknown>;
  const company = String(metadata.company ?? "");
  const role = String(metadata.role ?? "");
  const careerContext = [role, company].filter(Boolean).join(" at ");

  const workerUrl = process.env.WORKER_URL;
  const workerSecret = process.env.WORKER_SECRET;

  // We run this entire pipeline as a best-effort background chain.
  // Lock button returns immediately — UI doesn't wait for this.
  (async () => {
    try {
      // Step 1: Enrich chunk inline (no HTTP roundtrip — avoids NEXTAUTH_URL/localhost issue)
      // Blocker 4 fix: was self-fetching NEXTAUTH_URL which is undefined in production.
      let enrichedMeta = ENRICH_FALLBACK;
      try {
        enrichedMeta = await enrichChunkInline(chunkText, careerContext);
      } catch (enrichErr) {
        console.warn("[stories/lock] enrich-chunk failed:", (enrichErr as Error).message);
      }

      // Step 2: Create career_nugget row with source_chunk_id
      // Extract the body text (skip ## and ### headers)
      const bodyLines = chunkText
        .split("\n")
        .filter((l) => !l.startsWith("## ") && !l.startsWith("### ") && l.trim());
      const nuggetText = bodyLines.join(" ").slice(0, 2000).trim();

      if (nuggetText.length < 20) {
        console.warn("[stories/lock] chunk text too short for nugget creation:", chunk_id);
        return;
      }

      // Blocker 5 fix: prepend "source:onboarding" so worker's tag filter picks this up.
      // Worker embed query: .overlaps("tags", ["source:truthengine", "source:onboarding", "source:skill_upload"])
      const finalTags = ["source:onboarding", ...(enrichedMeta.tags ?? [])];

      const { data: nuggetRow, error: nuggetErr } = await supabase
        .from("career_nuggets")
        .insert({
          user_id: user.id,
          source_chunk_id: chunk_id,
          answer: nuggetText,
          nugget_text: chunkText.slice(0, 1000),
          company: company || null,
          role: role || null,
          section_type: "experience",
          importance: enrichedMeta.importance,
          tags: finalTags,
          leadership_signal: enrichedMeta.leadership || null,
        })
        .select("id")
        .maybeSingle();

      // Collect inserted nugget IDs for targeted worker calls
      const insertedNuggetIds: string[] = [];

      if (nuggetErr) {
        // source_chunk_id column may not exist yet — degrade to insert without it
        if (
          nuggetErr.code === "42703" ||
          nuggetErr.message?.includes("does not exist") || nuggetErr.message?.includes("schema cache") || nuggetErr.message?.includes("Could not find")
        ) {
          console.warn("[stories/lock] source_chunk_id column missing — inserting without it");
          const { data: fallbackRow } = await supabase
            .from("career_nuggets")
            .insert({
              user_id: user.id,
              answer: nuggetText,
              nugget_text: chunkText.slice(0, 1000),
              company: company || null,
              role: role || null,
              section_type: "experience",
              importance: enrichedMeta.importance,
              tags: finalTags,
            })
            .select("id")
            .maybeSingle();
          if (fallbackRow?.id) insertedNuggetIds.push(fallbackRow.id);
        } else {
          console.error("[stories/lock] nugget insert failed:", nuggetErr.message);
          return;
        }
      } else if (nuggetRow?.id) {
        insertedNuggetIds.push(nuggetRow.id);
      }

      // Step 3: Fire worker embed for THIS chunk's freshly-inserted nuggets —
      // one targeted call per nugget, fire-and-forget (Oracle path for job matching).
      // Avoids full user-sweep that would cause N×N redundant embed calls on rapid
      // multi-card locking.
      if (workerUrl && workerSecret && insertedNuggetIds.length > 0) {
        void Promise.all(
          insertedNuggetIds.map((nugget_id) =>
            fetch(`${workerUrl}/nuggets/embed`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${workerSecret}`,
              },
              body: JSON.stringify({ user_id: user.id, nugget_id }),
            }).catch(() => null) // best-effort fire-and-forget per nugget
          )
        );
      }

      // Step 4: Inline Jina embed for resume customization use case (sub-second user-facing).
      // Different vector space from Oracle — stored in embedding_jina column.
      // Fire-and-forget — do NOT block response on Jina latency (~500ms).
      const jinaKey = getNextJinaKey();
      if (jinaKey && insertedNuggetIds.length > 0) {
        void (async () => {
          for (const nuggetId of insertedNuggetIds) {
            try {
              const { data: nugget } = await supabase
                .from("career_nuggets")
                .select("answer")
                .eq("id", nuggetId)
                .maybeSingle();
              if (!nugget?.answer) continue;
              const vectors = await jinaEmbed([nugget.answer], jinaKey, "text-matching");
              if (vectors?.[0]) {
                await supabase
                  .from("career_nuggets")
                  .update({ embedding_jina: vectors[0] })
                  .eq("id", nuggetId);
              }
            } catch (jinaErr) {
              // Best-effort — Oracle path covers job matching; Jina is additive
              console.warn("[stories/lock] Jina embed failed for nugget:", nuggetId, jinaErr);
            }
          }
        })();
      }
    } catch (pipelineErr) {
      console.error("[stories/lock] background pipeline failed:", (pipelineErr as Error).message);
    }
  })();

  return Response.json({ chunk: updated });
}
