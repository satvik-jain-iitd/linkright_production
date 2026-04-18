import { authorizeExtensionRequest } from "@/lib/extension-jwt";
import { createServiceClient } from "@/lib/supabase/service";

/** POST /api/extension/parse-job
 *
 * Content script sends the JD it detected on whatever career page the user
 * is browsing. We:
 *   1. Upsert a row in `job_scans` so the user can find the job later.
 *   2. Cheap keyword match against the user's memory-atom text to compute
 *      a preliminary match score + approximate gap count for the overlay.
 *      (The full semantic scoring in /api/jd/analyze runs inside the
 *      resume builder — we don't want every extension hover to trigger
 *      an LLM + embedding call.)
 *
 * Response: { job_id, match_score, gaps, atoms_used, atoms_total, insiders }
 * — shape matches what content.js renders in the overlay.
 *
 * Auth: Authorization: Bearer <extension-jwt>
 */

interface ParseJobBody {
  source?: string;    // 'linkedin' | 'greenhouse' | 'lever' | ...
  title?: string;
  company?: string;
  jd?: string;
  url?: string;
}

export async function POST(request: Request) {
  const claims = await authorizeExtensionRequest(request);
  if (!claims) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: ParseJobBody;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const title = (body.title ?? "").trim().slice(0, 300);
  const company = (body.company ?? "").trim().slice(0, 200);
  const jd = (body.jd ?? "").trim().slice(0, 12_000);
  const url = (body.url ?? "").trim().slice(0, 500);
  const source = (body.source ?? "").trim().slice(0, 40);

  if (!title || !jd || !url) {
    return Response.json({ error: "title, jd, url required" }, { status: 400 });
  }

  const sb = createServiceClient();

  // ── 1. Upsert job_scans row (dedupe on (user_id, url)) ───────────────
  const { data: existing } = await sb
    .from("job_scans")
    .select("id")
    .eq("user_id", claims.sub)
    .eq("jd_url", url)
    .maybeSingle();

  let jobId: string;
  if (existing?.id) {
    jobId = existing.id;
  } else {
    const { data: inserted, error } = await sb
      .from("job_scans")
      .insert({
        user_id: claims.sub,
        company_slug: null, // extension doesn't know the canonical slug; left null
        ats_identifier: source || null,
        job_id: null,
        job_title: title,
        jd_url: url,
        jd_text: jd,
        source: "extension",
      })
      .select("id")
      .single();
    if (error || !inserted) {
      console.error("[ext-parse-job] insert failed:", error);
      return Response.json({ error: "Could not save job" }, { status: 500 });
    }
    jobId = inserted.id;
  }

  // ── 2. Cheap keyword overlap score (placeholder until full analysis) ──
  // Count how many of the user's atom-text tokens appear in the JD.
  const { count: atomCount } = await sb
    .from("career_nuggets")
    .select("id", { count: "exact", head: true })
    .eq("user_id", claims.sub)
    .eq("primary_layer", "A");

  const { data: sampleAtoms } = await sb
    .from("career_nuggets")
    .select("answer, company")
    .eq("user_id", claims.sub)
    .eq("primary_layer", "A")
    .limit(50);

  const jdTokens = new Set<string>(
    jd
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((t: string) => t.length >= 4),
  );

  let hitAtoms = 0;
  const atomsTotal = atomCount ?? 0;
  for (const atom of (sampleAtoms ?? []) as Array<{ answer: string | null }>) {
    const atomTokens = (atom.answer ?? "")
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((t: string) => t.length >= 4);
    const hit = atomTokens.some((t: string) => jdTokens.has(t));
    if (hit) hitAtoms++;
  }

  const matchScore = atomsTotal > 0 ? Math.round((hitAtoms / Math.min(atomsTotal, 50)) * 100) : 0;

  // ── 3. Gaps + insiders (stubs until Wave 8 peer-graph ships) ─────────
  // For now, gaps are derived from a very rough keyword check — the
  // extension overlay just needs a "3 gaps flagged" indicator; the real
  // analysis happens when the user opens the apply-pack in-app.
  const gapKeywords = ["required", "must have", "5+ years", "bachelor", "master", "phd"];
  const gaps = gapKeywords
    .filter((kw) => jd.toLowerCase().includes(kw))
    .slice(0, 5);

  return Response.json({
    job_id: jobId,
    match_score: matchScore,
    gaps,
    atoms_used: hitAtoms,
    atoms_total: atomsTotal,
    insiders: [], // Wave 8: peer-graph lookup
    company,
    title,
  });
}
