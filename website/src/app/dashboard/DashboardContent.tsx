"use client";

// Wave 2 / S12 — Dashboard (returning-user home).
// Design: screens-grow.jsx Screen12. Main column = matches → keep-going →
// Scout → your resumes. Right rail = profile card + daily diary.

import { useEffect, useState } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";
import { GRADE_COLORS } from "@/components/QualityPanel";
import { AppNav } from "@/components/AppNav";
import { DiaryQuickLog } from "@/components/DiaryQuickLog";

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
  target_role: string | null;
  target_company: string | null;
  error_message: string | null;
  jd_text: string | null;
  output_html: string | null;
  stats?: { quality_grade?: string } | null;
}

type JobDiscovery = {
  id: string;
  title: string;
  company_name: string;
  job_url: string | null;
};

type Top20Row = {
  id: string;
  rank: number;
  final_score: number | null;
  reason: string | null;
  resume_job_id: string | null;
  job_discoveries: JobDiscovery | null;
};

type RecsResponse = {
  date_utc: string;
  top20: Top20Row[];
};

type NuggetStatus = {
  total_extracted: number;
  total_embedded: number;
  embed_queued: number;
  ready: boolean;
};

type WatchedCompany = {
  id: string;
  company_name: string;
  last_scan_at?: string | null;
  new_jobs_last_scan?: number | null;
};

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

function pct(s: number | null | undefined) {
  if (s == null) return 0;
  return Math.round(Math.min(100, Math.max(0, s <= 1 ? s * 100 : s)));
}

function greetingName(user: User): string {
  const full = user.user_metadata?.full_name;
  if (typeof full === "string" && full) {
    const first = full.split(" ")[0];
    if (first && first.length < 20 && !first.includes("@")) return first;
  }
  return "there";
}

function greetingWord(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export function DashboardContent({
  user,
  nuggetCount = 0,
}: {
  user: User;
  nuggetCount?: number;
}) {
  const [jobs, setJobs] = useState<ResumeJob[]>([]);
  const [recs, setRecs] = useState<RecsResponse | null>(null);
  const [status, setStatus] = useState<NuggetStatus | null>(null);
  const [watchlist, setWatchlist] = useState<WatchedCompany[]>([]);
  const [diaryStreak, setDiaryStreak] = useState(0);
  const [loading, setLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const fetchJobs = () =>
    fetch("/api/resume/list")
      .then((r) => r.json())
      .then((data) => setJobs(data.jobs || []))
      .catch(() => {});

  useEffect(() => {
    Promise.all([
      fetchJobs(),
      fetch("/api/recommendations/today", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => setRecs(data)),
      fetch("/api/nuggets/status", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => setStatus(data)),
      fetch("/api/watchlist", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : { watchlist: [] }))
        .then((data) => setWatchlist(data.watchlist ?? [])),
      fetch("/api/diary?limit=1", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (data?.streak != null) setDiaryStreak(data.streak);
        }),
    ]).finally(() => setLoading(false));
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

  const inFlightJob = jobs.find(
    (j) => j.status === "queued" || j.status === "processing",
  );
  const topMatches = (recs?.top20 ?? []).filter((r) => r.job_discoveries).slice(0, 3);
  const statusBadge = (s: string) => {
    const map: Record<string, string> = {
      queued: "bg-gold-100 text-gold-700",
      processing: "bg-primary-100 text-primary-700",
      completed: "bg-green-100 text-green-700",
      failed: "bg-red-100 text-red-700",
    };
    return map[s] || "bg-border text-muted";
  };
  const jobLabel = (job: ResumeJob) =>
    job.target_role || job.target_company || "Resume";

  return (
    <div className="min-h-screen">
      <AppNav user={user} />

      <div className="mx-auto max-w-[1200px] px-6 py-10">
        {/* Greeting — v2 audit removed the streak chip + subtitle tail. */}
        <div>
          <h1 className="text-[28px] font-bold tracking-tight">
            {greetingWord()}, {greetingName(user)}.
          </h1>
          <p className="mt-1.5 text-sm text-muted">
            {topMatches.length > 0
              ? `${topMatches.length} new match${topMatches.length === 1 ? "" : "es"} today.`
              : "Scout is still catching up. Check back soon for matches."}
          </p>
        </div>

        {nuggetCount === 0 && (
          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-semibold text-amber-900">
              Complete your profile to unlock matches and resume generation.
            </p>
            <p className="mt-1 text-sm text-amber-700">
              Upload your resume once — we handle the rest.
            </p>
            <Link
              href="/onboarding"
              className="mt-3 inline-block rounded-full bg-amber-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-amber-700"
            >
              Finish onboarding →
            </Link>
          </div>
        )}

        <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_340px]">
          {/* Main column */}
          <div className="space-y-8">
            {/* Today's matches */}
            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold tracking-tight">
                  Today&apos;s matches
                </h2>
                {topMatches.length > 0 && (
                  <Link
                    href="/dashboard/jobs"
                    className="text-xs font-semibold text-accent hover:text-accent-hover"
                  >
                    See all →
                  </Link>
                )}
              </div>
              {loading ? (
                <div className="grid gap-3 md:grid-cols-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-36 animate-pulse rounded-2xl border border-border bg-white"
                    />
                  ))}
                </div>
              ) : topMatches.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border bg-white p-6 text-center">
                  <p className="text-sm font-medium">No matches yet today.</p>
                  <p className="mt-1 text-xs text-muted">
                    Scout refreshes every 30 min. Try tuning your preferences.
                  </p>
                  <Link
                    href="/onboarding/preferences"
                    className="mt-3 inline-block rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold transition hover:border-accent hover:text-accent"
                  >
                    Tune preferences
                  </Link>
                </div>
              ) : (
                <div className="grid gap-3 md:grid-cols-3">
                  {topMatches.map((r) => (
                    <div
                      key={r.id}
                      className="rounded-2xl border border-border bg-white p-4 transition hover:border-accent/40 hover:shadow-sm"
                    >
                      <div className="flex items-start justify-between">
                        <div className="truncate text-sm font-semibold">
                          {r.job_discoveries!.company_name}
                        </div>
                        <span
                          className={`text-sm font-bold ${pct(r.final_score) >= 80 ? "text-accent" : "text-gold-700"}`}
                        >
                          {pct(r.final_score)}%
                        </span>
                      </div>
                      <div className="mt-1.5 line-clamp-2 text-sm text-foreground">
                        {r.job_discoveries!.title}
                      </div>
                      {r.reason && (
                        <p className="mt-1.5 line-clamp-1 text-xs text-muted">
                          {r.reason}
                        </p>
                      )}
                      <Link
                        href={`/resume/new?job_id=${encodeURIComponent(r.job_discoveries!.id)}`}
                        className="mt-3 block rounded-full border border-accent bg-white py-1.5 text-center text-xs font-semibold text-accent transition hover:bg-accent hover:text-white"
                      >
                        Start application
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Keep going */}
            <section>
              <h2 className="mb-3 text-base font-semibold tracking-tight">
                Keep going
              </h2>
              <div className="space-y-2.5">
                {inFlightJob && (
                  <div className="flex items-center gap-3 rounded-xl border border-purple-500/30 bg-purple-500/5 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10 text-purple-700">
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                        />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold">
                        Pick up where you left off
                      </div>
                      <div className="text-xs text-muted">
                        {jobLabel(inFlightJob)}
                        {inFlightJob.target_company &&
                          ` · ${inFlightJob.target_company}`}{" "}
                        · {inFlightJob.progress_pct}% done
                      </div>
                    </div>
                    <Link
                      href={`/resume/new?job=${inFlightJob.id}`}
                      className="rounded-full bg-accent px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-accent-hover"
                    >
                      Resume
                    </Link>
                  </div>
                )}

                {status && !status.ready && status.total_extracted > 0 && (
                  <div className="flex items-center gap-3 rounded-xl border border-border bg-white p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                        />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold">
                        Your profile is still setting up
                      </div>
                      <div className="text-xs text-muted">
                        {status.total_embedded}/{status.total_extracted} highlights
                        processed
                      </div>
                    </div>
                    <Link
                      href="/onboarding/profile"
                      className="rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
                    >
                      Add a few more →
                    </Link>
                  </div>
                )}

                {!inFlightJob && (status?.ready || status == null) && (
                  <div className="flex items-center gap-3 rounded-xl border border-border bg-white p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sage-100 text-sage-700">
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.129.164 2.27.294 3.423.39 1.1.092 1.907 1.056 1.907 2.16v4.773l3.423-3.423a1.125 1.125 0 01.8-.33 48.31 48.31 0 005.58-.498c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
                        />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold">
                        Practice interview questions
                      </div>
                      <div className="text-xs text-muted">
                        Drills tailored to your target roles · 15 minutes
                      </div>
                    </div>
                    <Link
                      href="/dashboard/interview-prep"
                      className="rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
                    >
                      Start →
                    </Link>
                  </div>
                )}
              </div>
            </section>

            {/* Scout watchlist */}
            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold tracking-tight">
                  Scout · companies you&apos;re watching
                </h2>
                <Link
                  href="/dashboard/scout"
                  className="text-xs font-semibold text-accent hover:text-accent-hover"
                >
                  Manage →
                </Link>
              </div>
              {watchlist.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border bg-white p-5 text-center">
                  <p className="text-sm">
                    Watch specific companies — we&apos;ll pulse you when they
                    post.
                  </p>
                  <Link
                    href="/dashboard/scout"
                    className="mt-3 inline-block rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold transition hover:border-accent hover:text-accent"
                  >
                    Add a company
                  </Link>
                </div>
              ) : (
                <div className="overflow-hidden rounded-2xl border border-border bg-white">
                  {watchlist.slice(0, 5).map((w, i, arr) => {
                    const dot =
                      (w.new_jobs_last_scan ?? 0) > 0
                        ? "bg-accent"
                        : w.last_scan_at
                          ? "bg-muted/50"
                          : "bg-border";
                    const updateText =
                      (w.new_jobs_last_scan ?? 0) > 0
                        ? `${w.new_jobs_last_scan} new role${w.new_jobs_last_scan === 1 ? "" : "s"} posted recently`
                        : w.last_scan_at
                          ? `Scanned ${new Date(w.last_scan_at).toLocaleDateString(
                              "en-IN",
                              { day: "numeric", month: "short" },
                            )}`
                          : "Not scanned yet";
                    return (
                      <div
                        key={w.id}
                        className={
                          "flex items-center gap-3.5 px-4 py-3" +
                          (i === arr.length - 1 ? "" : " border-b border-border")
                        }
                      >
                        <span className={`h-2 w-2 rounded-full ${dot}`} />
                        <div className="flex-1">
                          <div className="text-sm font-semibold">
                            {w.company_name}
                          </div>
                          <div className="text-xs text-muted">{updateText}</div>
                        </div>
                        <Link
                          href={`/dashboard/scout`}
                          className="text-xs text-muted transition hover:text-foreground"
                        >
                          View →
                        </Link>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* Your resumes (existing jobs list, compact) */}
            {jobs.length > 0 && (
              <section>
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-base font-semibold tracking-tight">
                    Your resumes
                  </h2>
                  <Link
                    href="/resume/new"
                    onClick={() =>
                      sessionStorage.removeItem("linkright_wizard_v4")
                    }
                    className="text-xs font-semibold text-accent hover:text-accent-hover"
                  >
                    + New
                  </Link>
                </div>
                <div className="space-y-2.5">
                  {jobs.slice(0, 5).map((job) => {
                    const cardInner = (
                      <div className="flex items-center justify-between rounded-xl border border-border bg-white p-3.5 transition hover:border-accent/40">
                        <div className="flex items-center gap-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusBadge(job.status)}`}
                          >
                            {job.status}
                          </span>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold">
                                {jobLabel(job)}
                              </p>
                              {job.stats?.quality_grade && (
                                <span
                                  className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                                    GRADE_COLORS[job.stats.quality_grade] ??
                                    "bg-gray-100 text-gray-600"
                                  }`}
                                >
                                  {job.stats.quality_grade}
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-muted">
                              {job.target_company && (
                                <span>{job.target_company} · </span>
                              )}
                              {new Date(job.created_at).toLocaleDateString(
                                "en-IN",
                                {
                                  day: "numeric",
                                  month: "short",
                                },
                              )}
                            </p>
                            {job.status === "failed" && job.error_message && (
                              <p className="mt-1 line-clamp-2 text-[11px] text-red-500">
                                {friendlyError(job.error_message)}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {(job.status === "queued" ||
                            job.status === "processing") && (
                            <>
                              {job.status === "processing" && (
                                <span className="text-[11px] text-muted">
                                  {job.progress_pct}%
                                </span>
                              )}
                              <button
                                onClick={(e) => handleCancel(job.id, e)}
                                disabled={cancellingId === job.id}
                                className="rounded-full border border-red-200 px-2.5 py-1 text-[11px] text-red-600 transition hover:border-red-400 hover:bg-red-50 disabled:opacity-50"
                              >
                                {cancellingId === job.id ? "Cancelling…" : "Cancel"}
                              </button>
                            </>
                          )}
                          {job.status === "failed" && (
                            <Link
                              href={
                                "/resume/new" +
                                (job.jd_text
                                  ? "?retry_jd=" + encodeURIComponent(job.jd_text)
                                  : "")
                              }
                              className="rounded-full bg-cta px-3 py-1 text-[11px] font-semibold text-white"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Retry
                            </Link>
                          )}
                          {job.status === "completed" && job.output_html && (
                            <button
                              onClick={(e) => handleDownload(job, e)}
                              className="rounded-full border border-border px-3 py-1 text-[11px] font-semibold text-foreground transition hover:border-accent hover:text-accent"
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
                    return <div key={job.id}>{cardInner}</div>;
                  })}
                </div>
              </section>
            )}
          </div>

          {/* Right rail */}
          <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start">
            {/* Your profile card */}
            <div
              className="rounded-2xl border p-5 shadow-sm"
              style={{
                background:
                  "linear-gradient(180deg, rgba(139,92,246,0.06) 0%, #FFFFFF 100%)",
                borderColor: "rgba(139,92,246,0.2)",
              }}
            >
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-purple-700">
                Your profile
              </p>
              <h3 className="mt-1.5 text-lg font-bold tracking-tight">
                Still growing.
              </h3>
              {/* v2 audit: stat grid of 4 was "data slop". Keep the single
                  useful number — highlights — and lose the rest. */}
              <div className="mt-4">
                <div className="text-[28px] font-bold tracking-tight text-purple-800">
                  {status?.total_extracted ?? nuggetCount ?? 0}
                </div>
                <div className="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
                  highlights in your profile
                </div>
              </div>
              <Link
                href="/onboarding/profile"
                className="mt-4 block rounded-full border border-accent py-2 text-center text-xs font-semibold text-accent transition hover:bg-accent hover:text-white"
              >
                Add more → sharpens every match
              </Link>
            </div>

            {/* Daily diary */}
            <DiaryQuickLog
              initialStreak={diaryStreak}
              onLogged={(s) => setDiaryStreak(s)}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}
