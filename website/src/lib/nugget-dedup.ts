/**
 * Hybrid nugget dedup utilities.
 *
 * 3-gate pipeline:
 *   Gate 1 (free):     Exact nugget_text match in DB.
 *   Gate 2 (cheap):    Same company + role + month → fetch context nuggets.
 *   Gate 3a (fast):    Cosine similarity > 0.92 against existing embeddings.
 *   Gate 3b (fallback): Jaccard token overlap > 0.50 (first session, no embeddings yet).
 *
 * Used by ingest-atom (TruthEngine path) and onboarding/confirm (onboarding path).
 */

import type { SupabaseClient } from "@supabase/supabase-js";

/** Cosine similarity between two equal-length vectors. */
export function cosineSim(a: number[], b: number[]): number {
  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom > 0 ? dot / denom : 0;
}

/** Jaccard similarity on word tokens longer than 3 chars. No API call. */
export function jaccardSim(a: string, b: string): number {
  const tokenize = (s: string) =>
    new Set(s.toLowerCase().split(/\W+/).filter((t) => t.length > 3));
  const setA = tokenize(a);
  const setB = tokenize(b);
  const intersection = [...setA].filter((t) => setB.has(t)).length;
  const union = new Set([...setA, ...setB]).size;
  return union > 0 ? intersection / union : 0;
}

/** Embed text via Oracle nomic-embed-text. Returns null if Oracle unavailable. */
export async function oracleEmbed(text: string): Promise<number[] | null> {
  const oracleUrl = process.env.ORACLE_BACKEND_URL;
  const oracleSecret = process.env.ORACLE_BACKEND_SECRET ?? "";
  if (!oracleUrl) return null;
  try {
    const resp = await fetch(`${oracleUrl.replace(/\/$/, "")}/lifeos/embed`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${oracleSecret}`,
      },
      body: JSON.stringify({ text }),
      signal: AbortSignal.timeout(5000),
    });
    if (!resp.ok) return null;
    const data = (await resp.json()) as Record<string, unknown>;
    return Array.isArray(data.embedding) ? (data.embedding as number[]) : null;
  } catch {
    return null;
  }
}

/**
 * Returns true if `nuggetText` is a duplicate of an existing nugget for this user.
 *
 * @param sb         Supabase client (service-role or user session)
 * @param userId     Target user
 * @param nuggetText Short label (~5-10 words)
 * @param company    Company name or null
 * @param role       Role/title or null
 * @param eventDate  Sanitized YYYY-MM-DD or null
 */
export async function isDuplicateNugget(
  sb: SupabaseClient,
  userId: string,
  nuggetText: string,
  company: string | null,
  role: string | null,
  eventDate: string | null
): Promise<boolean> {
  // ── Gate 1: exact text match (free DB lookup) ─────────────────────────────
  const { data: exactMatch } = await sb
    .from("career_nuggets")
    .select("id")
    .eq("user_id", userId)
    .eq("nugget_text", nuggetText)
    .limit(1);
  if (exactMatch && exactMatch.length > 0) {
    console.log(`[dedup] Gate 1 exact: "${nuggetText.slice(0, 60)}"`);
    return true;
  }

  // ── Gate 2: context narrowing — need company+role for meaningful comparison ─
  if (!company || !role) return false;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let q: any = sb
    .from("career_nuggets")
    .select("id, nugget_text, embedding")
    .eq("user_id", userId)
    .eq("company", company)
    .eq("role", role);

  // Narrow to the same calendar month when event_date is known
  if (eventDate) {
    const ym = eventDate.slice(0, 7); // "YYYY-MM"
    q = q.gte("event_date", `${ym}-01`).lte("event_date", `${ym}-28`);
  }

  const { data: ctx } = await q;
  if (!ctx || ctx.length === 0) return false;

  // ── Gate 3a: cosine similarity (requires embeddings + Oracle) ────────────
  const withEmb = ctx.filter(
    (n: { embedding: unknown }) =>
      Array.isArray(n.embedding) && (n.embedding as number[]).length > 0
  );
  if (withEmb.length > 0) {
    const newEmb = await oracleEmbed(nuggetText);
    if (newEmb) {
      for (const n of withEmb) {
        const sim = cosineSim(newEmb, n.embedding as number[]);
        if (sim > 0.92) {
          console.log(
            `[dedup] Gate 3a cosine dup (sim=${sim.toFixed(3)}): "${nuggetText.slice(0, 60)}"`
          );
          return true;
        }
      }
      return false; // embeddings checked — definitely not a duplicate
    }
  }

  // ── Gate 3b: Jaccard fallback (first session — embeddings don't exist yet) ─
  for (const n of ctx) {
    const jac = jaccardSim(nuggetText, n.nugget_text as string);
    if (jac > 0.5) {
      console.log(
        `[dedup] Gate 3b Jaccard dup (jac=${jac.toFixed(2)}): "${nuggetText.slice(0, 60)}"`
      );
      return true;
    }
  }

  return false;
}
