import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { InterviewJourneyClient } from "./InterviewJourneyClient";

export const metadata = {
  title: "Interview prep — LinkRight",
};

export default async function InterviewPrepHub() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  // Fetch latest application with a role filled in
  const { data: latestApp } = await supabase
    .from("applications")
    .select("id, role, company, journey_bucket, journey_stage_index")
    .eq("user_id", user.id)
    .not("role", "is", null)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <InterviewJourneyClient initialApp={latestApp} />
    </div>
  );
}
