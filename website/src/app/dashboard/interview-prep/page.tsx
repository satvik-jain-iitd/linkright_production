import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";

// Wave 4 — Dynamic Interview Journey Hub.
// Displays sequential interview stages tailored to the user's career bucket.

export const metadata = {
  title: "Interview prep — LinkRight",
};

async function getUserBucket(supabase: any, userId: string) {
  // 1. Check if user has an application
  const { data: app } = await supabase
    .from("applications")
    .select("role")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const role = app?.role?.toLowerCase() || "";

  // 2. Simple mapping logic (in production this would be a DB field)
  if (role.includes("engineer") && !role.includes("manager")) return "software_engineer";
  if (role.includes("product manager") || role.includes("pm")) return "product_manager";
  if (role.includes("designer") || role.includes("ux")) return "ux_designer";
  if (role.includes("growth") || role.includes("marketer")) return "growth_marketer";
  if (role.includes("manager") && role.includes("engineer")) return "engineering_manager";
  if (role.includes("analyst")) return "business_analyst";
  
  return "product_manager"; // Default to PM for now
}

export default async function InterviewPrepHub() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  const bucketSlug = await getUserBucket(supabase, user.id);

  // Fetch stages for this bucket
  const { data: stages } = await supabase
    .from("interview_journey_stages")
    .select(`
      display_name,
      round_type,
      sort_order,
      interview_journey_buckets!inner(name, slug)
    `)
    .eq("interview_journey_buckets.slug", bucketSlug)
    .order("sort_order", { ascending: true });

  const bucketName = stages?.[0]?.interview_journey_buckets?.name || "Standard";

  return (
    <div className="min-h-screen bg-[#F9FBF6]">
      <AppNav user={user} />
      <main className="mx-auto max-w-[1100px] px-6 py-10">
        <div className="mb-10 max-w-2xl">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-sage-600">
            Journey: {bucketName}
          </p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-sage-900">
            Your Interview Roadmap
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-sage-700/70">
            We&apos;ve mapped out the standard interview flow for {bucketName} roles. 
            Each stage is a high-fidelity voice drill tailored to your profile.
          </p>
        </div>

        {/* The Timeline View */}
        <div className="relative space-y-4">
          {/* Vertical Line */}
          <div className="absolute left-[26px] top-8 bottom-8 w-px border-l border-dashed border-sage-300" />

          {stages?.map((s, idx) => (
            <div key={s.round_type + idx} className="group relative flex items-start gap-6">
              {/* Connector Dot */}
              <div className="relative z-10 flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white shadow-sm ring-1 ring-sage-200 transition-all group-hover:ring-sage-400 group-hover:shadow-md">
                <span className="text-xs font-black text-sage-400">{s.sort_order}</span>
              </div>

              {/* Card */}
              <div className="flex-1 rounded-2xl border border-sage-200 bg-white p-5 shadow-sm transition-all hover:border-sage-300 hover:shadow-md">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-[15px] font-bold text-sage-900">{s.display_name}</h3>
                    <p className="mt-1 text-[12px] text-sage-600/80">
                      Practice this 45-min {s.display_name.toLowerCase()} simulation.
                    </p>
                  </div>
                  <a
                    href={`/dashboard/interview-prep/coach?round=${s.round_type}`}
                    className="rounded-full bg-sage-700 px-5 py-2 text-[11px] font-black uppercase tracking-widest text-white transition-all hover:bg-sage-900 hover:scale-105 active:scale-95"
                  >
                    Start Drill
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Oracle roundtable — coming soon tease */}
        <div className="mt-12 flex flex-wrap items-center gap-4 rounded-3xl border border-dashed border-sage-300 bg-sage-50/30 p-8">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-purple-500/10 text-purple-700 shadow-inner">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold tracking-tight text-sage-900">
                Oracle Roundtable
              </h3>
              <span className="rounded-full bg-gold-500/10 px-2.5 py-0.5 text-[9px] font-black uppercase tracking-widest text-gold-700 ring-1 ring-inset ring-gold-500/20">
                Exclusive
              </span>
            </div>
            <p className="mt-1 text-sm text-sage-600/70">
              Three personas — HM, Recruiter, XFN Partner — grill you in parallel. 
              Unlock this after completing your roadmap.
            </p>
          </div>
          <button
            type="button"
            disabled
            className="rounded-full border border-sage-200 bg-white px-6 py-2 text-[11px] font-bold text-sage-400"
          >
            Soon
          </button>
        </div>
      </main>
    </div>
  );
}
