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

  // Onboarding gate: redirect if user hasn't completed setup
  const [{ count: keyCount }, { count: chunkCount }, { count: nuggetCount }] = await Promise.all([
    supabase
      .from("user_api_keys")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id)
      .eq("is_active", true),
    supabase
      .from("career_chunks")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
    supabase
      .from("career_nuggets")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id),
  ]);

  if ((keyCount ?? 0) === 0 || ((chunkCount ?? 0) === 0 && (nuggetCount ?? 0) === 0)) {
    redirect("/onboarding");
  }

  return <DashboardContent user={user} />;
}
