#!/usr/bin/env node
/**
 * backfill_embedding_jina.js
 * One-shot script: populate embedding_jina for all career_nuggets where it is NULL.
 *
 * Usage (from website/ dir after vercel env pull):
 *   node scripts/backfill_embedding_jina.js
 *
 * Requires env:
 *   NEXT_PUBLIC_SUPABASE_URL  — Supabase project URL
 *   SUPABASE_SERVICE_ROLE_KEY — service-role key (admin access)
 *   JINA_API_KEY              — at least one Jina API key
 *   JINA_API_KEY_2 / _3 / _4  — optional additional keys (round-robin)
 *
 * Batches: 16 texts per Jina call (safe within rate limits).
 * Skips nuggets with empty answer. Logs progress per batch.
 */

import { createClient } from "@supabase/supabase-js";
import fetch from "node-fetch";
import * as dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, "..", ".env.local") });

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
  console.error("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  process.exit(1);
}

// Round-robin Jina keys
const JINA_KEYS = [
  process.env.JINA_API_KEY,
  process.env.JINA_API_KEY_2,
  process.env.JINA_API_KEY_3,
  process.env.JINA_API_KEY_4,
].filter((k) => k && k.length > 0);

if (JINA_KEYS.length === 0) {
  console.error("No Jina API keys found. Set JINA_API_KEY in .env.local");
  process.exit(1);
}

let rrCounter = 0;
function nextJinaKey() {
  const key = JINA_KEYS[rrCounter % JINA_KEYS.length];
  rrCounter++;
  return key;
}

const BATCH_SIZE = 16;
const JINA_EMBED_URL = "https://api.jina.ai/v1/embeddings";
const JINA_MODEL = "jina-embeddings-v3";

const sb = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

async function jinaEmbed(texts) {
  const key = nextJinaKey();
  const resp = await fetch(JINA_EMBED_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({
      model: JINA_MODEL,
      input: texts,
      dimensions: 768,
      task: "text-matching",
    }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Jina API ${resp.status}: ${body.slice(0, 200)}`);
  }
  const data = await resp.json();
  if (!Array.isArray(data?.data)) throw new Error("Unexpected Jina response shape");
  const sorted = [...data.data].sort((a, b) => a.index - b.index);
  return sorted.map((item) => item.embedding);
}

async function main() {
  // Fetch all nuggets with null embedding_jina
  // Paginate in case there are many
  let page = 0;
  const PAGE_SIZE = 200;
  let totalProcessed = 0;
  let totalSkipped = 0;
  let totalFailed = 0;

  while (true) {
    const { data: nuggets, error } = await sb
      .from("career_nuggets")
      .select("id, answer")
      .is("embedding_jina", null)
      .not("answer", "is", null)
      .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1);

    if (error) {
      if (error.code === "42703" || error.message?.includes("embedding_jina")) {
        console.error(
          "Column embedding_jina does not exist yet. Run migration 051 first:\n" +
          "  ALTER TABLE career_nuggets ADD COLUMN IF NOT EXISTS embedding_jina vector(768);"
        );
        process.exit(1);
      }
      throw error;
    }

    if (!nuggets || nuggets.length === 0) break;

    // Filter out empty answers
    const valid = nuggets.filter((n) => n.answer && n.answer.trim().length >= 10);
    totalSkipped += nuggets.length - valid.length;

    // Process in batches of BATCH_SIZE
    for (let i = 0; i < valid.length; i += BATCH_SIZE) {
      const batch = valid.slice(i, i + BATCH_SIZE);
      const texts = batch.map((n) => n.answer);

      try {
        const vectors = await jinaEmbed(texts);
        // Upsert each nugget's embedding
        for (let j = 0; j < batch.length; j++) {
          const { error: updateErr } = await sb
            .from("career_nuggets")
            .update({ embedding_jina: vectors[j] })
            .eq("id", batch[j].id);
          if (updateErr) {
            console.warn(`Failed to update nugget ${batch[j].id}:`, updateErr.message);
            totalFailed++;
          } else {
            totalProcessed++;
          }
        }
        console.log(
          `Batch ${Math.floor(i / BATCH_SIZE) + 1}: embedded ${batch.length} nuggets ` +
          `(total processed: ${totalProcessed})`
        );
      } catch (err) {
        console.error(`Jina batch failed (offset ${i}):`, err.message);
        totalFailed += batch.length;
        // Wait 2s before continuing after rate limit / timeout
        await new Promise((r) => setTimeout(r, 2000));
      }

      // Small pause between batches to respect Jina rate limits
      if (i + BATCH_SIZE < valid.length) {
        await new Promise((r) => setTimeout(r, 300));
      }
    }

    page++;
    if (nuggets.length < PAGE_SIZE) break; // last page
  }

  console.log("\n--- Backfill complete ---");
  console.log(`Processed: ${totalProcessed}`);
  console.log(`Skipped (empty answer): ${totalSkipped}`);
  console.log(`Failed: ${totalFailed}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
