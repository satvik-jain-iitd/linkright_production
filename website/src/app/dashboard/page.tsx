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

  return <DashboardContent user={user} nuggetCount={nuggetCount ?? 0} />;
}
