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

  // Check onboarding status: does user have career data?
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
  const [{ count: chunkCount }, { count: nuggetCount }] = await Promise.all([
    supabase
      .from("career_chunks")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
    supabase
      .from("career_nuggets")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
  ]);

  const hasCareerData = (chunkCount ?? 0) > 0 || (nuggetCount ?? 0) > 0;

  // Already onboarded → go to dashboard
  if (hasCareerData) {
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
