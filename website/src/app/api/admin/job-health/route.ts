import { createClient } from "@/lib/supabase/server";
import { checkAdmin } from "@/lib/admin-auth";

export async function GET() {
  const admin = await checkAdmin();
  if (!admin.ok) return Response.json({ error: admin.reason }, { status: admin.ok === false && admin.reason === "unauthenticated" ? 401 : 403 });

  const supabase = await createClient();

  const [total, byStatus, bySource, enrichmentPending] = await Promise.all([
    supabase.from("job_discoveries").select("id", { count: "exact", head: true }).is("user_id", null),
    supabase.from("job_discoveries").select("liveness_status").is("user_id", null),
    supabase.from("job_discoveries").select("source_type").is("user_id", null),
    supabase.from("job_discoveries").select("id", { count: "exact", head: true }).is("user_id", null).eq("enrichment_status", "pending"),
  ]);

  // Count by liveness_status
  const statusCounts: Record<string, number> = {};
  for (const row of byStatus.data || []) {
    const s = row.liveness_status || "unknown";
    statusCounts[s] = (statusCounts[s] || 0) + 1;
  }

  // Count by source_type
  const sourceCounts: Record<string, number> = {};
  for (const row of bySource.data || []) {
    const s = row.source_type || "ats";
    sourceCounts[s] = (sourceCounts[s] || 0) + 1;
  }

  return Response.json({
    total: total.count || 0,
    by_status: statusCounts,
    by_source: sourceCounts,
    enrichment_pending: enrichmentPending.count || 0,
  });
}

// DELETE: clean expired jobs older than 7 days
export async function DELETE() {
  const admin = await checkAdmin();
  if (!admin.ok) return Response.json({ error: admin.reason }, { status: admin.ok === false && admin.reason === "unauthenticated" ? 401 : 403 });

  const supabase = await createClient();
  const cutoff = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

  const { error, count } = await supabase
    .from("job_discoveries")
    .delete({ count: "exact" })
    .is("user_id", null)
    .eq("liveness_status", "expired")
    .lt("liveness_checked_at", cutoff);

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ ok: true, deleted: count });
}
