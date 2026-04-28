import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { OnboardingFlow } from "./OnboardingFlow";

export default async function OnboardingPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth");
  }

  // Onboarding is considered "completed" only when the user has explicitly
  // submitted their resume (Lock + Save and continue) — indicated by
  // resume_submitted_at being set on at least one career_chunk.
  //
  // Old predicate: `chunkCount > 0 || nuggetCount > 0` — this caused a
  // redirect loop for users who uploaded a resume but never clicked
  // Save and continue (chunks exist, resume_submitted_at is null, nuggets = 0).
  // Those users were bounced dashboard → onboarding → dashboard infinitely.
  //
  // Fix: redirect to dashboard ONLY when the story step was explicitly
  // submitted (resume_submitted_at IS NOT NULL on at least one chunk).
  const { count: submittedChunkCount } = await supabase
    .from("career_chunks")
    .select("*", { count: "exact", head: true })
    .eq("user_id", user.id)
    .not("resume_submitted_at", "is", null);

  // Story step submitted → user has completed onboarding past the story screen.
  // Redirect to dashboard to continue (profile / preferences / find-roles).
  if ((submittedChunkCount ?? 0) > 0) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto w-full max-w-[1200px] px-6 pt-16 pb-32">
        <OnboardingFlow />
      </div>
    </div>
  );
}
