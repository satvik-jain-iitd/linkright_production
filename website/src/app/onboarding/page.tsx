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

  // Check onboarding status: does user have API key + career data?
  const [{ count: keyCount }, { count: chunkCount }] = await Promise.all([
    supabase
      .from("user_api_keys")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id)
      .eq("is_active", true),
    supabase
      .from("career_chunks")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
  ]);

  const hasApiKey = (keyCount ?? 0) > 0;
  const hasCareerData = (chunkCount ?? 0) > 0;

  // Already onboarded → go to dashboard
  if (hasApiKey && hasCareerData) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <OnboardingFlow />
      </div>
    </div>
  );
}
