"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
// [NAV-REDESIGN] createClient + useRouter only used by handleSignOut (now in AppNav)
// import { createClient } from "@/lib/supabase/client";
// import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import { GRADE_COLORS } from "@/components/QualityPanel";
import { AppNav } from "@/components/AppNav";

interface ResumeJob {
  id: string;
  status: string;
  current_phase: string;
  progress_pct: number;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  model_provider: string;
  model_id: string;
  target_role: string | null; // [PSA5-ayd.1.1.4]
  target_company: string | null;
  error_message: string | null; // [PSA5-ayd.2.1.1]
  jd_text: string | null; // [PSA5-ayd.2.1.2]
  output_html: string | null;
  stats?: { quality_grade?: string } | null;
}

// [PSA5R-1A] Human-readable error message mapping
const ERROR_PATTERNS: Array<[RegExp, string]> = [
  [/timed?\s*out/i, "Resume generation timed out. Please try again."],
  [/worker\s*(un)?reachable/i, "Our servers are busy. Please try again in a moment."],
  [/pydantic|validation|parse|schema/i, "The job description couldn't be processed. Try simplifying it."],
  [/rate\s*limit/i, "Too many requests. Please wait a few minutes."],
  [/api[_\s]?key|auth|unauthorized/i, "Service configuration error. Please contact support."],
  [/token|context.*length|too\s*long/i, "The input was too long. Try shortening your job description."],
];

const friendlyError = (raw: string): string => {
  for (const [pattern, message] of ERROR_PATTERNS) {
    if (pattern.test(raw)) return message;
  }
  return "Something went wrong. Please try again.";
};

export function DashboardContent({ user }: { user: User }) {
  // [NAV-REDESIGN] const router = useRouter();
  const [jobs, setJobs] = useState<ResumeJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const fetchJobs = () =>
    fetch("/api/resume/list")
      .then((r) => r.json())
      .then((data) => setJobs(data.jobs || []))
      .catch(() => {});

  useEffect(() => {
    fetchJobs().finally(() => setLoading(false));
  }, []);

  const handleCancel = async (jobId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setCancellingId(jobId);
    try {
      await fetch("/api/resume/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId }),
      });
      await fetchJobs();
    } finally {
      setCancellingId(null);
    }
  };

  // [NAV-REDESIGN] handleSignOut — AppNav handles sign out internally
  // const handleSignOut = async () => {
  //   const supabase = createClient();
  //   await supabase.auth.signOut({ scope: "global" });
  //   router.push("/auth");
  // };

  const handleDownload = (job: ResumeJob, e: React.MouseEvent) => {
    e.preventDefault();
    if (!job.output_html) return;
    const blob = new Blob([job.output_html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resume-${job.target_company || job.id}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      queued: "bg-gold-100 text-gold-700",
      processing: "bg-primary-100 text-primary-700",
      completed: "bg-green-100 text-green-700",
      failed: "bg-red-100 text-red-700",
    };
    return map[status] || "bg-border text-muted";
  };

  // [PSA5-ayd.1.1.4] Primary label: role > company > fallback
  const jobLabel = (job: ResumeJob) =>
    job.target_role || job.target_company || "Resume";

  // [NAV-REDESIGN] Inline nav replaced by shared AppNav component
  // <nav className="flex items-center justify-between border-b border-border px-6 py-4">
  //   <Link href="/dashboard" className="text-lg font-bold tracking-tight">
  //     Link<span className="text-accent">Right</span>
  //   </Link>
  //   <div className="flex items-center gap-4">
  //     <Link
  //       href="/dashboard/career"
  //       className="text-sm text-muted transition-colors hover:text-foreground"
  //     >
  //       My Career
  //     </Link>
  //     <Link
  //       href="/dashboard/nuggets"
  //       className="text-sm text-muted transition-colors hover:text-foreground"
  //     >
  //       Career Highlights
  //     </Link>
  //     {/* [BYOK-REMOVED] Settings link removed
  //     <Link
  //       href="/dashboard/settings"
  //       className="text-sm text-muted transition-colors hover:text-foreground"
  //     >
  //       Settings
  //     </Link>
  //     */}
  //     <div className="flex items-center gap-3">
  //       {user.user_metadata?.avatar_url && (
  //         <img
  //           src={user.user_metadata.avatar_url}
  //           alt=""
  //           className="h-8 w-8 rounded-full"
  //         />
  //       )}
  //       <span className="text-sm text-muted">
  //         {user.user_metadata?.full_name || user.email}
  //       </span>
  //     </div>
  //     <button
  //       onClick={handleSignOut}
  //       className="rounded-lg border border-border px-3 py-1.5 text-sm text-muted transition-colors hover:text-foreground"
  //     >
  //       Sign out
  //     </button>
  //   </div>
  // </nav>

  return (
    <div className="min-h-screen">
      <AppNav user={user} />

      {/* Main content */}
      <div className="mx-auto max-w-4xl px-6 py-12">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              {/* [DASHBOARD-CLEANUP] Old greeting: user.user_metadata?.full_name?.split(" ")[0] || "there" */}
              Welcome, {(() => {
                const firstName = user.user_metadata?.full_name?.split(" ")[0];
                const greeting = firstName && firstName.length < 20 && !firstName.includes("@") ? firstName : "there";
                return greeting;
              })()}!
            </h1>
            <p className="mt-2 text-muted">Manage your tailored resumes.</p>
          </div>
          {/* [DASHBOARD-CLEANUP] Duplicate "Create Resume" CTA — AppNav already has one */}
          {/* <Link */}
          {/*   href="/resume/new" */}
          {/*   onClick={() => sessionStorage.removeItem("linkright_wizard_v4")} */}
          {/*   className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover" */}
          {/* > */}
          {/*   + Create Resume */}
          {/* </Link> */}
        </div>

        {/* [DASHBOARD-CLEANUP] Feedback/pricing survey banner removed — revisit when pricing is finalized */}
        {/* <div className="mt-8 rounded-2xl border border-border bg-surface p-6 shadow-sm"> */}
        {/*   <div className="flex items-center justify-between"> */}
        {/*     <div> */}
        {/*       <p className="text-sm text-muted">Help us build the right pricing</p> */}
        {/*       <p className="mt-1 text-sm text-foreground"> */}
        {/*         Your first resume is free. Share feedback to shape what&apos;s next. */}
        {/*       </p> */}
        {/*     </div> */}
        {/*     <Link */}
        {/*       href="/pricing" */}
        {/*       className="rounded-full border border-accent bg-accent/10 px-4 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent/20" */}
        {/*     > */}
        {/*       Share feedback */}
        {/*     </Link> */}
        {/*   </div> */}
        {/* </div> */}

        {/* Resume list */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold">Your resumes</h2>

          {loading ? (
            <div className="mt-4 flex justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            </div>
          ) : jobs.length === 0 ? (
            <div className="mt-4 rounded-2xl border border-dashed border-border bg-surface/50 p-12 text-center">
              <p className="font-medium">No resumes yet</p>
              <p className="mt-1 text-sm text-muted">
                Create your first pixel-perfect resume in minutes.
              </p>
              <Link
                href="/resume/new"
                onClick={() => sessionStorage.removeItem("linkright_wizard_v4")}
                className="mt-6 inline-block rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
              >
                Create resume
              </Link>
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              {jobs.map((job) => {
                const cardInner = (
                  <div className="flex items-center justify-between rounded-xl border border-border bg-surface p-4 transition-colors hover:bg-surface-hover">
                    <div className="flex items-center gap-4">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusBadge(job.status)}`}
                      >
                        {job.status}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium">{jobLabel(job)}</p>
                          {job.stats?.quality_grade && (
                            <span
                              className={`text-xs font-medium px-2 py-0.5 rounded-full ${GRADE_COLORS[job.stats.quality_grade] ?? "bg-gray-100 text-gray-600"}`}
                              aria-label={`Quality grade: ${job.stats.quality_grade}`}
                            >
                              {job.stats.quality_grade}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted">
                          {job.target_company && (
                            <span>{job.target_company} · </span>
                          )}
                          {new Date(job.created_at).toLocaleDateString("en-IN", {
                            day: "numeric",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                          {// [PSA5-ayd.3.1.1] model name removed from card subtitle — old: job.model_id.split("/").pop()?.replace(/:.*/,"")
                          }
                        </p>
                        {job.status === "failed" && job.error_message && (
                          <p className="text-xs text-red-500 mt-1 line-clamp-2">{friendlyError(job.error_message)}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {(job.status === "queued" || job.status === "processing") && (
                        <div className="flex items-center gap-2">
                          {job.status === "processing" && (
                            <>
                              <div className="h-3 w-3 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
                              <span className="text-xs text-muted">{job.progress_pct}%</span>
                            </>
                          )}
                          <button
                            onClick={(e) => handleCancel(job.id, e)}
                            disabled={cancellingId === job.id}
                            className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-500 transition-colors hover:border-red-400 hover:bg-red-50 disabled:opacity-50"
                          >
                            {cancellingId === job.id ? "Cancelling..." : "Cancel"}
                          </button>
                        </div>
                      )}
                      {/* [PSA5-ayd.3.1.2] duration_ms display removed from completed cards */}
                      {/* {job.duration_ms && ( */}
                      {/*   <span className="text-xs text-muted"> */}
                      {/*     {Math.round(job.duration_ms / 1000)}s */}
                      {/*   </span> */}
                      {/* )} */}
                      {job.status === "failed" && (
                        <Link
                          href={"/resume/new" + (job.jd_text ? "?retry_jd=" + encodeURIComponent(job.jd_text) : "")}
                          className="rounded-full bg-cta px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-cta-hover"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Retry
                        </Link>
                      )}
                      {job.status === "completed" && job.output_html && (
                        <button
                          onClick={(e) => handleDownload(job, e)}
                          className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted transition-colors hover:border-accent/50 hover:text-accent"
                        >
                          Download
                        </button>
                      )}
                    </div>
                  </div>
                );

                if (job.status === "completed") {
                  return (
                    <Link key={job.id} href={`/resume/new?job=${job.id}`}>
                      {cardInner}
                    </Link>
                  );
                }
                return (
                  <div key={job.id}>
                    {cardInner}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
