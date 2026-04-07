import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { computeOverallConfidence } from "@/lib/confidence";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`onboarding-status:${user.id}`, 30)) {
    return rateLimitResponse("onboarding status");
  }

  const [{ count: keyCount }, { count: chunkCount }, { data: nuggets }] =
    await Promise.all([
      supabase
        .from("user_api_keys")
        .select("*", { count: "exact", head: true })
        .eq("user_id", user.id)
        .eq("is_active", true),
      supabase
        .from("career_chunks")
        .select("*", { count: "exact", head: true })
        .eq("user_id", user.id),
      supabase
        .from("career_nuggets")
        .select("id, company, role, answer, event_date, section_type")
        .eq("user_id", user.id),
    ]);

  const has_api_key = (keyCount ?? 0) > 0;
  const has_career_data = (chunkCount ?? 0) > 0;

  const nuggetRows = (nuggets ?? []) as Array<{
    id: string;
    company: string | null;
    role: string | null;
    answer: string | null;
    event_date: string | null;
    section_type: string;
  }>;

  const confidence = computeOverallConfidence(nuggetRows);

  return Response.json({
    has_api_key,
    has_career_data,
    onboarding_complete: has_api_key && has_career_data,
    confidence,
  });
}
