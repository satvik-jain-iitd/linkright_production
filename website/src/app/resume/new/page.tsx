import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { WizardShell } from "./WizardShell";

export default async function NewResumePage({
  searchParams,
}: {
  searchParams: Promise<{ job?: string; retry_jd?: string; job_id?: string; discovery_id?: string }>;
}) {
  const { job, retry_jd, job_id, discovery_id } = await searchParams;
  // [PSA5-ayd.2.1.3] Decode retry_jd param to pre-fill JD textarea on retry
  let retryJdText = retry_jd ? decodeURIComponent(retry_jd as string) : undefined;
  let discoveryCompany: string | undefined;
  let discoveryRole: string | undefined;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/auth");

  // S08 → S09 handoff: Find Roles passes either ?job_id= or ?discovery_id=
  // referring to a job_discoveries row. We pull its JD + title so the user
  // skips pasting a JD when they came from Scout.
  const discoveryTarget = discovery_id || (job_id && job_id.length > 20 ? job_id : undefined);
  if (discoveryTarget && !retryJdText) {
    const { data: disc } = await supabase
      .from("job_discoveries")
      .select("title, company_name, jd_text")
      .eq("id", discoveryTarget)
      .maybeSingle();
    if (disc?.jd_text) {
      const header =
        disc.title && disc.company_name
          ? `Role: ${disc.title}\nCompany: ${disc.company_name}\n\n`
          : "";
      retryJdText = `${header}${disc.jd_text}`;
      if (disc.company_name) discoveryCompany = disc.company_name;
      if (disc.title) discoveryRole = disc.title;
    }
  }

  // Onboarding gate: redirect if user hasn't completed setup
  // [BYOK-REMOVED] const [{ count: keyCount }, { count: chunkCount }] = await Promise.all([
  // [BYOK-REMOVED]   supabase
  // [BYOK-REMOVED]     .from("user_api_keys")
  // [BYOK-REMOVED]     .select("*", { count: "exact", head: true })
  // [BYOK-REMOVED]     .eq("user_id", user.id)
  // [BYOK-REMOVED]     .eq("is_active", true),
  // [BYOK-REMOVED]   supabase
  // [BYOK-REMOVED]     .from("career_chunks")
  // [BYOK-REMOVED]     .select("*", { count: "exact", head: true })
  // [BYOK-REMOVED]     .eq("user_id", user.id),
  // [BYOK-REMOVED] ]);
  const [{ count: nuggetCount }, { count: chunkCount }, { count: resumeCount }] = await Promise.all([
    supabase
      .from("career_nuggets")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
    supabase
      .from("career_chunks")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
    supabase
      .from("resume_jobs")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id)
      .in("status", ["completed", "processing", "queued"]),
  ]);

  if ((nuggetCount ?? 0) === 0 && (chunkCount ?? 0) === 0) {
    redirect("/onboarding");
  }

  const isFirstResume = (resumeCount ?? 0) === 0;

  return (
    <div className="min-h-screen bg-background">
      <WizardShell userId={user.id} jobId={job} retryJdText={retryJdText} discoveryCompany={discoveryCompany} discoveryRole={discoveryRole} isFirstResume={isFirstResume} />
    </div>
  );
}
