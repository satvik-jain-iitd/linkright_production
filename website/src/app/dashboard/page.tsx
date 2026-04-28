import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { DashboardContent } from "./DashboardContent";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth");
  }

  const [
    { count: nuggetCount },
    { count: chunkCount },
    { count: submittedChunkCount },
  ] = await Promise.all([
    supabase
      .from("career_nuggets")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
    supabase
      .from("career_chunks")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
    // Determines if user completed the story-submit step.
    // resume_submitted_at is set by /api/onboarding/stories/submit-resume
    // when user clicks "Lock + Save and continue" on the story screen.
    supabase
      .from("career_chunks")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id)
      .not("resume_submitted_at", "is", null),
  ]);

  if ((nuggetCount ?? 0) === 0 && (chunkCount ?? 0) === 0) {
    redirect("/onboarding");
  }

  // resumeSubmitted: user has clicked "Save and continue" on story screen.
  // Used by DashboardContent to decide whether to show "Finish onboarding" CTA.
  const resumeSubmitted = (submittedChunkCount ?? 0) > 0;

  return (
    <DashboardContent
      user={user}
      nuggetCount={nuggetCount ?? 0}
      chunkCount={chunkCount ?? 0}
      resumeSubmitted={resumeSubmitted}
    />
  );
}
