import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { OutreachView } from "@/components/outreach/OutreachView";

export const metadata = {
  title: "Outreach — LinkRight",
};

export default async function OutreachPage({
  searchParams,
}: {
  searchParams: Promise<{ resume_job?: string }>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  const params = await searchParams;
  if (!params.resume_job) {
    // No context — send user back to the dashboard so they pick a resume to
    // draft outreach against.
    redirect("/dashboard?outreach=need_resume");
  }

  // Prefetch the resume_job so we can show company/role in the header
  // without a client-side round trip.
  const { data: job } = await supabase
    .from("resume_jobs")
    .select("id, target_company, target_role")
    .eq("id", params.resume_job)
    .eq("user_id", user.id)
    .maybeSingle();

  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <main className="mx-auto max-w-[1100px] px-6 py-10">
        <OutreachView
          resumeJobId={params.resume_job}
          targetCompany={job?.target_company ?? null}
          targetRole={job?.target_role ?? null}
        />
      </main>
    </div>
  );
}
