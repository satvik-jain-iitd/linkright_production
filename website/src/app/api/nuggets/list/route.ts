// GET: Paginated list of user's career nuggets with filters

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`nuggets-list:${user.id}`, 90)) {
    return rateLimitResponse("nuggets list");
  }

  const url = new URL(request.url);
  const page = Math.max(1, parseInt(url.searchParams.get("page") || "1", 10));
  const limit = Math.min(100, Math.max(1, parseInt(url.searchParams.get("limit") || "50", 10)));
  const sectionType = url.searchParams.get("section_type");
  const company = url.searchParams.get("company");
  const importance = url.searchParams.get("importance");
  const search = url.searchParams.get("search");
  const embeddedFilter = url.searchParams.get("embedded");
  const primaryLayer = url.searchParams.get("primary_layer"); // [PSA5-z0c.1.1.3]

  // Select includes locked_at + profile_submitted_at (added in migration 045).
  // If migration hasn't run yet, Supabase returns an error; we fall back to
  // the pre-045 column set so existing data is never silently lost.
  const SELECT_V2 =
    "id, nugget_text, answer, company, role, event_date, section_type, importance, resume_relevance, tags, created_at, primary_layer, life_domain, leadership_signal, locked_at, profile_submitted_at, source_chunk_id";
  const SELECT_V1 =
    "id, nugget_text, answer, company, role, event_date, section_type, importance, resume_relevance, tags, created_at, primary_layer, life_domain, leadership_signal";

  async function runQuery(selectCols: string) {
    let query = supabase
      .from("career_nuggets")
      .select(selectCols, { count: "exact" })
      .eq("user_id", user!.id)
      .order("created_at", { ascending: false })
      .range((page - 1) * limit, page * limit - 1);

    if (sectionType) query = query.eq("section_type", sectionType);
    if (company) query = query.eq("company", company);
    if (importance) query = query.eq("importance", importance);
    if (search) query = query.ilike("answer", `%${search}%`);
    if (embeddedFilter === "true") query = query.or("embedding.not.is.null,embedding_jina.not.is.null");
    if (embeddedFilter === "false") query = query.is("embedding", null).is("embedding_jina", null);
    if (primaryLayer) query = query.eq("primary_layer", primaryLayer);

    return query;
  }

  // Run query — fall back to pre-045 columns if migration hasn't run
  let queryResult = await runQuery(SELECT_V2);

  // Migration 045 may not have run yet — fall back to pre-045 columns
  if (queryResult.error && (
    queryResult.error.code === "42703" ||
    queryResult.error.message?.includes("does not exist")
  )) {
    console.warn("[nuggets/list] locked_at column missing — using v1 schema fallback");
    queryResult = await runQuery(SELECT_V1);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data, count, error } = queryResult as any;

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  // Get embedded IDs for the returned nuggets.
  // A card is considered embedded when EITHER embedding (legacy Oracle/nomic)
  // OR embedding_jina (new Jina flow) is populated. This ensures ProfileHighlightsView
  // polling terminates correctly after Jina embedding completes.
  const nuggetIds = (data || []).map((n: { id: string }) => n.id);
  let embeddedIds = new Set<string>();

  if (nuggetIds.length > 0) {
    // First try OR query (requires migration 051 — adds embedding_jina column).
    // If the column is missing (code 42703), fall back to legacy single-column check
    // so existing users are not affected during the deploy-to-migration gap.
    const { data: embRows, error: embErr } = await supabase
      .from("career_nuggets")
      .select("id")
      .in("id", nuggetIds)
      .or("embedding.not.is.null,embedding_jina.not.is.null");

    if (embErr && (
      embErr.code === "42703" ||
      embErr.message?.includes("embedding_jina") ||
      embErr.message?.includes("does not exist") ||
      embErr.message?.includes("Could not find") ||
      embErr.message?.includes("schema cache")
    )) {
      // Migration 051 not yet applied — fall back to legacy embedding column only
      console.warn("[nuggets/list] embedding_jina column missing — using legacy embedding fallback for is_embedded");
      const { data: legacyEmbRows } = await supabase
        .from("career_nuggets")
        .select("id")
        .in("id", nuggetIds)
        .not("embedding", "is", null);
      embeddedIds = new Set((legacyEmbRows || []).map((r: { id: string }) => r.id));
    } else {
      embeddedIds = new Set((embRows || []).map((r: { id: string }) => r.id));
    }
  }

  const totalCount = count || 0;
  const nuggets = (data || []).map((n: Record<string, unknown> & { id: string }) => ({
    ...n,
    is_embedded: embeddedIds.has(n.id),
  }));

  return Response.json({
    nuggets,
    total: totalCount,
    page,
    has_more: page * limit < totalCount,
  });
}
