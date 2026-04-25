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
  const [diaryStreak, setDiaryStreak] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [cancelledId, setCancelledId] = useState<string | null>(null);
  const [pulse, setPulse] = useState<{
    funnel: { inProgress: number; sent: number; interview: number; offer: number };
    broadcast: { postsThisMonth: number; reactions: number; profileViews: number };
  } | null>(null);

  const fetchJobs = () =>
    fetch("/api/resume/list")
      .then((r) => r.json())
      .then((data) => setJobs(data.jobs || []))
      .catch(() => {});

  const loadDashboard = () => {
    setLoadError(false);
    setLoading(true);
    Promise.all([
      fetchJobs(),
      fetch("/api/recommendations/today", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => setRecs(data)),
      fetch("/api/nuggets/status", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => setStatus(data)),
      fetch("/api/diary?limit=1", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (data?.streak != null) setDiaryStreak(data.streak);
        }),
      fetch("/api/dashboard/pulse", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => { if (data) setPulse(data); }),
    ])
      .catch(() => setLoadError(true))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDashboard();
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
      setCancelledId(jobId);
      setTimeout(() => setCancelledId(null), 2500);
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

  if (loadError) {
    return (
      <div className="min-h-screen">
        <AppNav user={user} />
        <div className="flex flex-col items-center justify-center py-32 text-center">
          <div className="mb-3 text-3xl">⚠️</div>
          <p className="text-sm font-semibold text-foreground">Could not load your dashboard</p>
          <p className="mt-1 text-xs text-muted">Check your connection and try again.</p>
          <button
            onClick={loadDashboard}
            className="mt-5 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-accent/90"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

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
              : "We're still finding matches for you. Check back soon."}
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
              className="mt-3 inline-block rounded-lg bg-amber-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-amber-700"
            >
              Finish onboarding →
            </Link>
          </div>
        )}

        <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_340px]">
          {/* Main column */}
          <div className="space-y-8">
            {/* Today's pipeline */}
            <section>
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold tracking-tight">
                    Today&apos;s pipeline
                  </h2>
                  <p className="mt-0.5 text-[12px] text-muted">
                    Work you&apos;ve started · roles matched this morning
                  </p>
                </div>
                <Link
                  href="/dashboard/jobs"
                  className="text-xs font-semibold text-accent hover:text-accent-hover"
                >
                  Open pipeline →
                </Link>
              </div>

              {/* Funnel strip */}
              {!loading && (
                <div className="mb-3 grid grid-cols-5 divide-x divide-border overflow-hidden rounded-xl border border-border bg-white">
                  {[
                    { n: topMatches.length, label: "New matches", sub: "Today", color: "text-accent" },
                    { n: pulse?.funnel.inProgress ?? jobs.filter(j => j.status === "queued" || j.status === "processing").length, label: "In progress", sub: "Drafting now", color: "text-gold-700" },
                    { n: pulse?.funnel.sent ?? jobs.filter(j => j.status === "completed").length, label: "Sent", sub: "This week", color: "text-muted" },
                    { n: pulse?.funnel.interview ?? 0, label: "Interview", sub: "Active", color: "text-purple-700" },
                    { n: pulse?.funnel.offer ?? 0, label: "Offer", sub: "Deciding", color: "text-accent" },
                  ].map((s) => (
                    <div key={s.label} className="px-4 py-3">
                      <div className={`text-[22px] font-bold leading-none tracking-tight ${s.color}`}>{s.n}</div>
                      <div className="mt-1.5 text-[12px] font-semibold text-foreground">{s.label}</div>
                      <div className="text-[10.5px] text-muted">{s.sub}</div>
                    </div>
                  ))}
                </div>
              )}

              {loading ? (
                <div className="h-48 animate-pulse rounded-xl border border-border bg-white" />
              ) : topMatches.length === 0 && !inFlightJob ? (
                <div className="rounded-2xl border border-dashed border-border bg-white p-6 text-center">
                  <p className="text-sm font-medium">No matches yet today.</p>
                  <p className="mt-1 text-xs text-muted">
                    Matches refresh every 30 min. Try tuning your preferences.
                  </p>
                  <Link
                    href="/onboarding/preferences"
                    className="mt-3 inline-block rounded-lg border border-border px-3.5 py-1.5 text-xs font-semibold transition hover:border-accent hover:text-accent"
                  >
                    Tune preferences
                  </Link>
                </div>
              ) : (
                <div className="overflow-hidden rounded-xl border border-border bg-white">
                  <div className="grid grid-cols-[44px_1fr_180px_160px_100px] gap-3 border-b border-border px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-muted">
                    <span>Match</span>
                    <span>Role</span>
                    <span>Company · Location</span>
                    <span>Status</span>
                    <span className="text-right">Action</span>
                  </div>
                  {inFlightJob && (
                    <div className="grid grid-cols-[44px_1fr_180px_160px_100px] items-center gap-3 border-b border-border bg-gold-50/40 px-4 py-3 last:border-b-0">
                      <span className="text-[15px] font-bold text-gold-700">—</span>
                      <div>
                        <div className="text-[13.5px] font-semibold">{jobLabel(inFlightJob)}</div>
                      </div>
                      <div>
                        <div className="text-[12.5px] font-medium">{inFlightJob.target_company ?? "—"}</div>
                      </div>
                      <div>
                        <div className="text-[12.5px] font-medium text-[#8A6E1E]">Resume draft · {inFlightJob.progress_pct}% done</div>
                        <div className="text-[11px] text-muted">In progress</div>
                      </div>
                      <div className="flex justify-end">
                        <Link
                          href={`/resume/new?job=${inFlightJob.id}`}
                          className="rounded-full bg-gold-600 px-3 py-1 text-[11px] font-semibold text-white transition hover:bg-gold-700"
                        >
                          Resume →
                        </Link>
                      </div>
                    </div>
                  )}
                  {topMatches.map((r, i) => (
                    <div
                      key={r.id}
                      className={`grid grid-cols-[44px_1fr_180px_160px_100px] items-center gap-3 px-4 py-3 ${i < topMatches.length - 1 || inFlightJob ? "border-b border-border" : ""}`}
                    >
                      <span className={`text-[15px] font-bold ${pct(r.final_score) >= 80 ? "text-accent" : "text-gold-700"}`}>
                        {pct(r.final_score)}%
                      </span>
                      <div>
                        <div className="text-[13.5px] font-semibold leading-snug">{r.job_discoveries!.title}</div>
                      </div>
                      <div>
                        <div className="text-[12.5px] font-medium">{r.job_discoveries!.company_name}</div>
                      </div>
                      <div>
                        <div className="text-[12.5px] font-medium text-[#09766D]">New match · today</div>
                        {r.reason && <div className="line-clamp-1 text-[11px] text-muted">{r.reason}</div>}
                      </div>
                      <div className="flex justify-end">
                        <Link
                          href={`/resume/new?job_id=${encodeURIComponent(r.job_discoveries!.id)}`}
                          className="rounded-full border border-accent px-3 py-1 text-[11px] font-semibold text-accent transition hover:bg-accent hover:text-white"
                        >
                          Start →
                        </Link>
                      </div>
                    </div>
                  ))}
                  {jobs.filter(j => j.status === "completed").slice(0, 2).map((job) => (
                    <div
                      key={job.id}
                      className="grid grid-cols-[44px_1fr_180px_160px_100px] items-center gap-3 border-t border-border px-4 py-3"
                    >
                      <span className="text-[15px] font-bold text-muted">—</span>
                      <div>
                        <div className="text-[13.5px] font-semibold">{jobLabel(job)}</div>
                      </div>
                      <div>
                        <div className="text-[12.5px] font-medium">{job.target_company ?? "—"}</div>
                      </div>
                      <div>
                        <div className="text-[12.5px] font-medium text-[#475569]">
                          Applied · {new Date(job.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                        </div>
                      </div>
                      <div className="flex justify-end">
                        <Link
                          href={`/resume/new?job=${job.id}`}
                          className="rounded-full border border-border px-3 py-1 text-[11px] font-semibold text-foreground transition hover:border-accent hover:text-accent"
                        >
                          View
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Keep going — Interview prep */}
            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold tracking-tight">
                  Keep going — Interview prep
                </h2>
                <Link href="/dashboard/interview-prep" className="text-[13px] font-medium text-[#4A5D32] hover:text-[#6B8346]">
                  Open all drills
                </Link>
              </div>
              <div className="space-y-2.5">
                {status && !status.ready && status.total_extracted > 0 && (
                  <div className="flex items-center gap-3 rounded-xl border border-border bg-white p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold">Your profile is still setting up</div>
                      <div className="text-xs text-muted">{status.total_embedded}/{status.total_extracted} highlights processed</div>
                    </div>
                    <Link href="/onboarding/profile" className="rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent">
                      Add a few more →
                    </Link>
                  </div>
                )}
                <div className="flex items-center gap-3 rounded-xl border border-[#6B8346]/30 bg-[#6B8346]/[0.04] p-4">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-[#6B8346]/10 text-[#4A5D32]">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.129.164 2.27.294 3.423.39 1.1.092 1.907 1.056 1.907 2.16v4.773l3.423-3.423a1.125 1.125 0 01.8-.33 48.31 48.31 0 005.58-.498c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold">Practice interview questions</div>
                    <div className="text-xs text-muted">Drills tailored to your target roles · 15 minutes</div>
                  </div>
                  <Link href="/dashboard/interview-prep" className="rounded-full bg-[#6B8346] px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-[#5a6e3a]">
                    Start →
                  </Link>
                </div>
                <div className="flex items-center gap-3 rounded-xl border border-border bg-white p-4">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-[#6B8346]/10 text-[#4A5D32]">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold">Product-sense warmup · 8 questions</div>
                    <div className="text-xs text-muted">Tailored to your work history · 12 minutes</div>
                  </div>
                  <Link href="/dashboard/interview-prep" className="rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent">
                    Start
                  </Link>
                </div>
                <div className="flex items-center gap-3 rounded-xl border border-border bg-white p-4">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-[#6B8346]/10 text-[#4A5D32]">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold">Record a &ldquo;Tell me about yourself&rdquo; take</div>
                    <div className="text-xs text-muted">Voice mock interview · transcript saved after</div>
                  </div>
                  <Link href="/dashboard/interview-prep/coach" className="rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent">
                    Record
                  </Link>
                </div>
              </div>
            </section>

            {/* Broadcast pulse */}
            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold tracking-tight">Broadcast pulse</h2>
                <Link href="/dashboard/broadcast" className="text-xs font-semibold text-pink-600 hover:text-pink-700">
                  Write a post →
                </Link>
              </div>
              <div className="overflow-hidden rounded-xl border border-border bg-white">
                <div className="grid grid-cols-3 divide-x divide-border">
                  {[
                    { n: pulse?.broadcast.postsThisMonth ?? 0, label: "Posts this month" },
                    { n: pulse?.broadcast.reactions ?? 0, label: "Reactions" },
                    { n: pulse?.broadcast.profileViews ?? 0, label: "Profile views" },
                  ].map((s) => (
                    <div key={s.label} className="px-5 py-4">
                      <div className="text-2xl font-bold tracking-tight text-foreground">{s.n}</div>
                      <div className="mt-1 text-[12px] text-muted">{s.label}</div>
                    </div>
                  ))}
                </div>
                <div className="border-t border-border px-5 py-3 text-[12px] text-muted">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-pink-50 px-2 py-0.5 text-[11px] font-medium text-pink-600">
                    Coming soon
                  </span>
                  {" "}LinkedIn broadcast — drafts from your wins, scheduled automatically.
                </div>
              </div>
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
                                {cancellingId === job.id
                                  ? "Cancelling…"
                                  : cancelledId === job.id
                                  ? "Cancelled ✓"
                                  : "Cancel"}
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
                              className="rounded-lg bg-cta px-3 py-1 text-[11px] font-semibold text-white"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Retry
                            </Link>
                          )}
                          {job.status === "completed" && (
                            <button
                              onClick={(e) => handleDownload(job, e)}
                              disabled={!job.output_html}
                              title={!job.output_html ? "Resume is still being prepared" : undefined}
                              className="rounded-full border border-border px-3 py-1 text-[11px] font-semibold text-foreground transition hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-40"
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
