"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Top20Row = {
  id: string;
  rank: number;
  final_score: number;
  reason: string | null;
  resume_job_id: string | null;
  job_discoveries: {
    id: string;
    title: string;
    company_name: string;
    job_url: string;
    location?: string;
    discovered_at: string;
    liveness_status: string;
  } | null;
};

type Payload = {
  date_utc: string;
  top20: Top20Row[];
  resume_jobs_by_id: Record<string, { status: string; created_at: string }>;
  daily_resume_usage: { used: number; cap: number; remaining: number };
};

function scoreColor(pct: number) {
  if (pct >= 85) return { bg: "bg-accent/10", text: "text-[#09766D]" };
  if (pct >= 75) return { bg: "bg-amber-50", text: "text-amber-700" };
  return { bg: "bg-[#F3F4F6]", text: "text-muted" };
}

function resumeStatusLabel(status: string): string {
  const map: Record<string, string> = {
    queued: "Resume queued",
    processing: "Resume generating",
    completed: "Resume ready",
    failed: "Resume failed",
  };
  return map[status] ?? status;
}

export default function JobsPage() {
  const router = useRouter();
  const [data, setData] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRetried, setAutoRetried] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const r = await fetch("/api/recommendations/today");
    const body = await r.json();
    if (!r.ok) setError(body.error ?? "Failed to load matches");
    else setData(body);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  // One-shot auto-retry: when first load returns 0 matches, retry once after 20s.
  // Handles the race where score-now timed out but the cron is still finishing.
  useEffect(() => {
    if (!loading && !error && data && data.top20.length === 0 && !autoRetried) {
      const t = setTimeout(() => {
        setAutoRetried(true);
        load();
      }, 20_000);
      return () => clearTimeout(t);
    }
  }, [loading, error, data, autoRetried, load]);

  async function handleStart(row: Top20Row) {
    if (!row.job_discoveries) return;
    const r = await fetch("/api/nuggets/status");
    const body = await r.json();
    const ready = body.total_embedded > 0 && body.total_embedded / body.total_extracted >= 0.9;
    router.push(ready
      ? `/customize/${row.job_discoveries.id}`
      : `/customize/${row.job_discoveries.id}/enrich`
    );
  }

  const rows = data?.top20.filter((r) => r.job_discoveries) ?? [];

  return (
    <div className="min-h-screen bg-[#FAFBFC]">
      <div className="mx-auto max-w-[1080px] px-6 py-8">

        {/* Back + header */}
        <div className="mb-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-foreground"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Dashboard
          </Link>
          <div className="mt-3 flex items-end justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#09766D]">Apply · Scout</p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground">
                {loading ? "Loading matches…" : `${rows.length} roles matched today`}
              </h1>
              {data && (
                <p className="mt-1 text-sm text-muted">
                  {data.daily_resume_usage.remaining} of {data.daily_resume_usage.cap} resume slots left today
                </p>
              )}
            </div>
            <button
              onClick={load}
              className="rounded-lg border border-border bg-white px-3 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 rounded-xl border border-border bg-white p-4">
                <div className="h-9 w-9 flex-shrink-0 animate-pulse rounded-lg bg-[#E2E8F0]" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 animate-pulse rounded bg-[#E2E8F0]" style={{ width: `${40 + i * 5}%` }} />
                  <div className="h-2.5 animate-pulse rounded bg-[#EEF0F3]" style={{ width: "25%" }} />
                </div>
                <div className="h-7 w-16 animate-pulse rounded-full bg-[#E2E8F0]" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
            <button onClick={load} type="button" className="ml-3 font-semibold underline">Retry</button>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && rows.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border bg-white p-12 text-center">
            <p className="text-sm font-semibold text-foreground">
              {autoRetried ? "No matches yet for today." : "Computing your matches…"}
            </p>
            <p className="mt-1 text-xs text-muted">
              {autoRetried
                ? "Scout runs every few minutes — try Refresh in a bit."
                : "We're scoring jobs against your preferences. This usually takes 20-30 seconds. Auto-refreshing…"}
            </p>
          </div>
        )}

        {/* Table */}
        {!loading && !error && rows.length > 0 && (
          <div className="overflow-hidden rounded-2xl border border-border bg-white">
            <div className="hidden grid-cols-[56px_1fr_200px_160px_120px] gap-4 border-b border-border bg-[#FAFBFC] px-5 py-2.5 sm:grid">
              <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">Match</span>
              <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">Role</span>
              <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">Company</span>
              <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">Status</span>
              <span className="text-right text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">Action</span>
            </div>

            {rows.map((row, i) => {
              const job = row.job_discoveries!;
              const pct = Math.round(row.final_score * 100);
              const { bg, text } = scoreColor(pct);
              const resumeStatus = row.resume_job_id
                ? data!.resume_jobs_by_id[row.resume_job_id]?.status
                : null;
              const hasResume = !!resumeStatus;
              const isInProgress = resumeStatus && resumeStatus !== "completed" && resumeStatus !== "failed";

              return (
                <div
                  key={row.id}
                  className={`flex flex-col gap-3 px-5 py-4 transition hover:bg-[#FAFBFC] sm:grid sm:grid-cols-[56px_1fr_200px_160px_120px] sm:items-center sm:gap-4 sm:py-3.5 ${
                    i < rows.length - 1 ? "border-b border-border/60" : ""
                  } ${isInProgress ? "bg-amber-50/40" : ""}`}
                >
                  {/* Match % */}
                  <div className={`inline-flex h-9 w-9 items-center justify-center rounded-lg text-[13px] font-bold ${bg} ${text}`}>
                    {pct}
                  </div>

                  {/* Role */}
                  <div>
                    <a
                      href={job.job_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[14px] font-semibold text-foreground hover:text-accent hover:underline"
                    >
                      {job.title}
                    </a>
                    {row.reason && (
                      <p className="mt-0.5 text-[11.5px] leading-snug text-muted line-clamp-1">{row.reason}</p>
                    )}
                  </div>

                  {/* Company · location */}
                  <div>
                    <div className="text-[13px] font-medium text-foreground">{job.company_name}</div>
                    {job.location && (
                      <div className="text-[11.5px] text-muted">{job.location}</div>
                    )}
                  </div>

                  {/* Status */}
                  <div className="text-[12px]">
                    {hasResume ? (
                      <span className={`font-medium ${isInProgress ? "text-amber-700" : resumeStatus === "completed" ? "text-[#09766D]" : "text-muted"}`}>
                        {resumeStatusLabel(resumeStatus!)}
                      </span>
                    ) : (
                      <span className="text-muted">New match · today</span>
                    )}
                  </div>

                  {/* Action */}
                  <div className="flex sm:justify-end">
                    {resumeStatus === "completed" ? (
                      <Link
                        href="/resume/new"
                        className="rounded-full border border-border bg-white px-3.5 py-1.5 text-[12px] font-semibold text-foreground transition hover:border-accent"
                      >
                        View
                      </Link>
                    ) : isInProgress ? (
                      <button
                        type="button"
                        onClick={() => handleStart(row)}
                        className="rounded-full bg-amber-400 px-3.5 py-1.5 text-[12px] font-semibold text-white transition hover:bg-amber-500"
                      >
                        Resume →
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleStart(row)}
                        className="rounded-full bg-accent px-3.5 py-1.5 text-[12px] font-semibold text-white transition hover:opacity-80"
                      >
                        Start →
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
