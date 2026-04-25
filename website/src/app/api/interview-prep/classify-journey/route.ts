/**
 * /api/interview-prep/classify-journey
 *
 * POST → classify an application into a role bucket, store in applications table,
 *         return the journey template for that bucket
 * PATCH → advance journey_stage_index by 1 for an application
 */

import { createClient } from "@/lib/supabase/server";

// ─── Role bucket keyword rules ─────────────────────────────────────────────
// Checked in order — first match wins. Title is lowercased before matching.
const BUCKET_RULES: { bucket: string; keywords: string[] }[] = [
  {
    bucket: "engineering_manager",
    keywords: [
      "engineering manager", "eng manager", "vp engineering", "vp of engineering",
      "director of engineering", "head of engineering", "cto",
    ],
  },
  {
    bucket: "software_engineer",
    keywords: [
      "software engineer", "software developer", "sde", "swe", "backend engineer",
      "frontend engineer", "fullstack engineer", "full stack engineer",
      "full-stack engineer", "mobile engineer", "ios engineer", "android engineer",
      "site reliability", "sre", "devops engineer", "platform engineer",
      "infrastructure engineer",
    ],
  },
  {
    bucket: "data_scientist",
    keywords: [
      "data scientist", "machine learning", "ml engineer", "ai engineer",
      "research scientist", "applied scientist", "data engineer", "nlp engineer",
      "computer vision", "deep learning",
    ],
  },
  {
    bucket: "ux_designer",
    keywords: [
      "ux designer", "product designer", "ui designer", "ui/ux", "ux/ui",
      "visual designer", "interaction designer", "design lead", "design manager",
      "head of design", "vp design",
    ],
  },
  {
    bucket: "growth_marketing",
    keywords: [
      "growth manager", "growth lead", "growth hacker", "marketing manager",
      "performance marketing", "digital marketing", "seo", "sem", "content marketing",
      "brand manager", "demand generation", "user acquisition",
    ],
  },
  {
    bucket: "business_analyst",
    keywords: [
      "business analyst", "operations analyst", "operations manager",
      "strategy analyst", "management consultant", "strategy consultant",
      "business operations", "revenue operations", "revops", "sales operations",
      "program manager",
    ],
  },
  {
    bucket: "product_manager",
    keywords: [
      "product manager", "product lead", "associate product manager", "apm",
      "senior product manager", "staff product manager", "principal product",
      "group product manager", "director of product", "vp product",
      "head of product", "chief product",
    ],
  },
];

function classifyBucket(role: string, department?: string | null): string {
  const lower = role.toLowerCase();

  for (const rule of BUCKET_RULES) {
    if (rule.keywords.some((kw) => lower.includes(kw))) {
      return rule.bucket;
    }
  }

  // Fallback: use job_discoveries.department if available
  if (department) {
    const deptMap: Record<string, string> = {
      product:     "product_manager",
      engineering: "software_engineer",
      design:      "ux_designer",
      data:        "data_scientist",
      growth:      "growth_marketing",
      platform:    "software_engineer",
    };
    if (deptMap[department]) return deptMap[department];
  }

  return "general";
}

// ─── GET — current stage for latest application (dashboard use) ────────────
export async function GET() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { data: app } = await supabase
    .from("applications")
    .select("id, role, company, journey_bucket, journey_stage_index")
    .eq("user_id", user.id)
    .not("role", "is", null)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!app) return Response.json({ stage: null });

  let bucket = app.journey_bucket as string | null;
  if (!bucket) {
    bucket = classifyBucket(app.role ?? "");
    await supabase
      .from("applications")
      .update({ journey_bucket: bucket })
      .eq("id", app.id)
      .eq("user_id", user.id);
  }

  const { data: template } = await supabase
    .from("interview_journey_templates")
    .select("stages, display_name")
    .eq("role_bucket", bucket)
    .single();

  const stageIndex = app.journey_stage_index ?? 0;
  const currentStage = (template?.stages as { name: string; stage_id: string }[] | null)?.[stageIndex] ?? null;

  return Response.json({
    application_id: app.id,
    role: app.role,
    company: app.company,
    bucket,
    journey_display_name: template?.display_name ?? null,
    current_stage_index: stageIndex,
    current_stage: currentStage,
    total_stages: (template?.stages as unknown[])?.length ?? 0,
  });
}

// ─── POST — classify & return journey ──────────────────────────────────────
export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  let body: { application_id?: string };
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { application_id } = body;
  if (!application_id || typeof application_id !== "string") {
    return Response.json({ error: "application_id is required" }, { status: 400 });
  }

  // Fetch application
  const { data: app, error: appErr } = await supabase
    .from("applications")
    .select("id, role, journey_bucket, journey_stage_index, company")
    .eq("id", application_id)
    .eq("user_id", user.id)
    .single();

  if (appErr || !app) {
    return Response.json({ error: "Application not found" }, { status: 404 });
  }

  // If already classified, just return existing template
  let bucket = app.journey_bucket as string | null;

  if (!bucket) {
    bucket = classifyBucket(app.role ?? "");

    await supabase
      .from("applications")
      .update({ journey_bucket: bucket })
      .eq("id", application_id)
      .eq("user_id", user.id);
  }

  // Fetch journey template
  const { data: template, error: tplErr } = await supabase
    .from("interview_journey_templates")
    .select("role_bucket, display_name, stages")
    .eq("role_bucket", bucket)
    .single();

  if (tplErr || !template) {
    return Response.json({ error: "Journey template not found" }, { status: 500 });
  }

  return Response.json({
    bucket,
    journey_template: template,
    current_stage_index: app.journey_stage_index ?? 0,
  });
}

// ─── PATCH — advance stage ─────────────────────────────────────────────────
export async function PATCH(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  let body: { application_id?: string };
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { application_id } = body;
  if (!application_id || typeof application_id !== "string") {
    return Response.json({ error: "application_id is required" }, { status: 400 });
  }

  const { data: app, error: appErr } = await supabase
    .from("applications")
    .select("id, journey_stage_index, journey_bucket")
    .eq("id", application_id)
    .eq("user_id", user.id)
    .single();

  if (appErr || !app) {
    return Response.json({ error: "Application not found" }, { status: 404 });
  }

  const newIndex = (app.journey_stage_index ?? 0) + 1;

  await supabase
    .from("applications")
    .update({ journey_stage_index: newIndex })
    .eq("id", application_id)
    .eq("user_id", user.id);

  return Response.json({ journey_stage_index: newIndex });
}
