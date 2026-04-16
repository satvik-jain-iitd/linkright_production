import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { WizardShell } from "./WizardShell";

export default async function NewResumePage({
  searchParams,
}: {
  searchParams: Promise<{ job?: string; retry_jd?: string }>;
}) {
  const { job, retry_jd } = await searchParams;
  // [PSA5-ayd.2.1.3] Decode retry_jd param to pre-fill JD textarea on retry
  const retryJdText = retry_jd ? decodeURIComponent(retry_jd as string) : undefined;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/auth");

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
  const [{ count: nuggetCount }, { count: chunkCount }] = await Promise.all([
    supabase
      .from("career_nuggets")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
    supabase
      .from("career_chunks")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
  ]);

  if ((nuggetCount ?? 0) === 0 && (chunkCount ?? 0) === 0) {
    redirect("/onboarding");
  }

  return (
    <div className="min-h-screen bg-background">
      <WizardShell userId={user.id} jobId={job} retryJdText={retryJdText} />
    </div>
  );
}
