import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ProfileHighlightsView } from "@/components/onboarding/ProfileHighlightsView";

export const metadata = {
  title: "Your profile — LinkRight",
  description: "Review and expand the highlights we extracted from your resume.",
};

export default async function OnboardingProfilePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth?mode=signin");
  }

  return (
    <main className="mx-auto min-h-screen max-w-[1200px] px-6 py-10">
      <ProfileHighlightsView />
    </main>
  );
}
