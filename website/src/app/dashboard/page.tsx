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

  return <DashboardContent user={user} />;
}
