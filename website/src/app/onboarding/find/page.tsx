import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { FindRolesView } from "@/components/onboarding/FindRolesView";

export const metadata = {
  title: "Find matching roles — LinkRight",
  description: "Your top-ranked role matches, refreshed daily.",
};

export default async function OnboardingFindPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth?mode=signin");
  }

  return (
    <main className="mx-auto min-h-screen max-w-[1200px] px-6 py-10">
      <FindRolesView embedded />
    </main>
  );
}
