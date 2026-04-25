/**
 * GET /api/interview-prep/journey-template?bucket=<role_bucket>
 * Returns journey template for a given role bucket (no auth required — templates are public).
 */

import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const bucket = searchParams.get("bucket");

  if (!bucket) {
    return Response.json({ error: "bucket is required" }, { status: 400 });
  }

  const supabase = await createClient();

  const { data: template, error } = await supabase
    .from("interview_journey_templates")
    .select("role_bucket, display_name, stages")
    .eq("role_bucket", bucket)
    .single();

  if (error || !template) {
    return Response.json({ error: "Template not found" }, { status: 404 });
  }

  return Response.json({ journey_template: template });
}
