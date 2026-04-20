"use client";

// Wave 2 / Screen 08 — Find roles (ranked matches).
// Design handoff: specs/design-handoff-2026-04-18/ → screens-act.jsx Screen08.
//
// Pulls from /api/recommendations/today. Top-ranked role spotlighted with
// accent styling + 3 reason chips. Remaining matches listed below. Click
// "Start custom application" → /resume/new?job_id=XXX. If profile still
// embedding, inline banner gives "Add insights" or "Continue anyway".

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { track } from "@/lib/analytics";

type JobDiscovery = {
  id: string;
  title: string;
  company_name: string;
  job_url: string | null;
  liveness_status?: string | null;
};

type Top20Row = {
  id: string;
  rank: number;
  final_score: number | null;
  reason: string | null;
  resume_job_id: string | null;
  job_discoveries: JobDiscovery | null;
};

type ResumeJobStatus = { status: string; created_at: string };

type RecsResponse = {
  date_utc: string;
  top20: Top20Row[];
  resume_jobs_by_id: Record<string, ResumeJobStatus>;
  daily_resume_usage: { used: number; cap: number; remaining: number };
};

type NuggetStatus = {
  total_extracted: number;
  total_embedded: number;
  embed_queued: number;
  ready: boolean;
};

interface Props {
  embedded?: boolean;
}

const STEPS = [
  { n: 1, label: "Resume", state: "done" },
  { n: 2, label: "Profile", state: "done" },
  { n: 3, label: "Preferences", state: "done" },
  { n: 4, label: "First match", state: "active" },
] as const;

function pct(score: number | null | undefined): number {
  if (score == null) return 0;
  return Math.round(Math.min(100, Math.max(0, score <= 1 ? score * 100 : score)));
}

function reasonChips(reason: string | null): string[] {
  if (!reason) return [];
  return reason
    .split(/\s*[;·•]\s*|\s*\.\s+/)
    .map((c) => c.trim())
    .filter((c) => c.length > 3 && c.length < 80)
    .slice(0, 3);
}

export function FindRolesView({ embedded }: Props) {
  const router = useRouter();
  const [recs, setRecs] = useState<RecsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [nuggetStatus, setNuggetStatus] = useState<NuggetStatus | null>(null);
  const [customOpen, setCustomOpen] = useState(false);
  const [customCompany, setCustomCompany] = useState("");
  const [customRole, setCustomRole] = useState("");
  const [customJD, setCustomJD] = useState("");
  const [customSaving, setCustomSaving] = useState(false);
  const [customError, setCustomError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [recRes, nugRes] = await Promise.all([
        fetch("/api/recommendations/today", { cache: "no-store" }),
        fetch("/api/nuggets/status", { cache: "no-store" }),
      ]);
      if (!recRes.ok) {
        setError("Couldn't load your matches — try again.");
        setLoading(false);
        return;
      }
      const recJson: RecsResponse = await recRes.json();
      setRecs(recJson);
      const nugJson = nugRes.ok ? await nugRes.json() : null;
      if (nugJson) setNuggetStatus(nugJson);
      setError("");
      // Track empty state for funnel analysis
      const hasRows = (recJson.top20 ?? []).filter((r: { job_discoveries: unknown }) => r.job_discoveries).length > 0;
      if (!hasRows) {
        const reason = nugJson && !nugJson.ready ? "profile_incomplete" : "no_matches";
        track({ event: "job_search_empty", properties: { reason } });
      }
    } catch {
      setError("Network error — try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const startApplication = (jobId: string) => {
    track({ event: "resume_builder_started", properties: { job_id: jobId } });
    router.push(`/resume/new?job_id=${encodeURIComponent(jobId)}`);
  };

  const submitCustomJob = async () => {
    if (!customCompany.trim()) { setCustomError("Company is required."); return; }
    if (!customRole.trim()) { setCustomError("Role is required."); return; }
    if (!customJD.trim() || customJD.trim().length < 20) { setCustomError("Paste the job description — at least a few lines."); return; }
    setCustomError("");
    setCustomSaving(true);
    try {
      const res = await fetch("/api/applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company: customCompany.trim(), role: customRole.trim(), jd_text: customJD.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        setCustomError(data.error ?? "Couldn't save. Try again.");
        return;
      }
      router.push(`/resume/new?application_id=${encodeURIComponent(data.id)}`);
    } catch {
      setCustomError("Network error — try again.");
    } finally {
      setCustomSaving(false);
    }
  };

  const rows = (recs?.top20 ?? []).filter((r) => r.job_discoveries);
  const [spotlight, ...rest] = rows;

  return (
    <div className="space-y-6">
      {embedded && (
        <>
          {/* Step indicator */}
          <div className="flex items-center justify-between border-b border-border pb-5">
            <div className="flex items-center gap-2 text-xs">
              {STEPS.map((s, i) => (
                <span key={s.n} className="flex items-center gap-2">
                  <span
                    className={
                      s.state === "active"
                        ? "rounded-full bg-accent px-3 py-1.5 font-semibold text-white"
                        : s.state === "done"
                          ? "rounded-full bg-accent/10 px-3 py-1.5 font-medium text-primary-700"
                          : "rounded-full border border-border bg-white px-3 py-1.5 font-medium text-muted"
                    }
                  >
                    {s.n} {s.state === "done" ? `${s.label} ✓` : s.label}
                  </span>
                  {i < STEPS.length - 1 && <span className="h-px w-4 bg-border" />}
                </span>
              ))}
            </div>
            <Link
              href="/onboarding/preferences"
              className="text-xs text-muted transition hover:text-foreground"
            >
              ← Tune preferences
            </Link>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-accent">
              The first magic moment
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground">
              Here are your best-fit roles today.
            </h1>
            <p className="mt-1 text-sm text-muted">
              Match scores are honest. If we say 62%, that&apos;s what we mean — and we&apos;ll
              show you the 3 real gaps.
            </p>
          </div>
        </>
      )}

      {/* Pending-embedding banner */}
      {nuggetStatus && !nuggetStatus.ready && nuggetStatus.total_extracted > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-tertiary-500/30 bg-tertiary-500/5 p-4">
          <div>
            <p className="text-sm font-semibold text-tertiary-700">
              We&apos;re still finishing your profile.
            </p>
            <p className="mt-0.5 text-xs text-muted">
              Adding a couple more details now will make your first draft sharper.
              {` ${nuggetStatus.total_embedded}/${nuggetStatus.total_extracted} processed.`}
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              href="/onboarding/profile"
              className="rounded-lg border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
            >
              Add a few more details →
            </Link>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-3">
          <div className="h-40 animate-pulse rounded-2xl border border-border bg-white" />
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-xl border border-border bg-white"
            />
          ))}
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
          <button onClick={load} type="button" className="ml-3 font-semibold underline">
            Retry
          </button>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && rows.length === 0 && !customOpen && (
        <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center">
          {nuggetStatus && !nuggetStatus.ready ? (
            <>
              <p className="text-sm font-semibold text-foreground">
                We&apos;re still building your profile ({nuggetStatus.total_embedded} of {nuggetStatus.total_extracted}).
              </p>
              <p className="mt-1 text-xs text-muted">Come back in a few minutes — matches will appear once your highlights are ready.</p>
            </>
          ) : (
            <>
              <p className="text-sm font-semibold text-foreground">Nothing matched right now.</p>
              <p className="mt-1 text-xs text-muted">Your preferences may be narrow, or we haven&apos;t finished scouting yet.</p>
            </>
          )}
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            <Link
              href="/onboarding/preferences"
              className="rounded-lg border border-border px-4 py-2 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
            >
              Tune preferences
            </Link>
            <button
              type="button"
              onClick={() => setCustomOpen(true)}
              className="rounded-full bg-cta px-4 py-2 text-xs font-semibold text-white shadow-cta transition hover:bg-cta-hover"
            >
              Add a custom job →
            </button>
          </div>
        </div>
      )}

      {/* Custom job form */}
      {!loading && !error && rows.length === 0 && customOpen && (
        <div className="rounded-2xl border border-border bg-white p-6">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-accent">Custom application</p>
              <h3 className="mt-1 text-base font-bold tracking-tight">Add your own job</h3>
              <p className="mt-0.5 text-xs text-muted">Paste the JD — we&apos;ll build you a tailored resume.</p>
            </div>
            <button type="button" onClick={() => setCustomOpen(false)} className="text-muted hover:text-foreground">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-foreground">Company <span className="text-cta">*</span></label>
                <input value={customCompany} onChange={(e) => setCustomCompany(e.target.value)} placeholder="Google" className="mt-1 w-full rounded-[10px] border border-border px-3 py-2 text-sm focus:border-accent focus:outline-none" />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">Role <span className="text-cta">*</span></label>
                <input value={customRole} onChange={(e) => setCustomRole(e.target.value)} placeholder="Product Manager" className="mt-1 w-full rounded-[10px] border border-border px-3 py-2 text-sm focus:border-accent focus:outline-none" />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-foreground">Job description <span className="text-cta">*</span></label>
              <textarea value={customJD} onChange={(e) => setCustomJD(e.target.value)} rows={8} placeholder="Paste the full job description here…" className="mt-1 w-full resize-y rounded-[10px] border border-border px-3 py-2.5 text-sm focus:border-accent focus:outline-none" />
            </div>
          </div>
          {customError && <p className="mt-2 rounded-[10px] bg-red-50 p-2 text-xs text-red-700">{customError}</p>}
          <div className="mt-4 flex justify-end gap-2">
            <button type="button" onClick={() => { setCustomOpen(false); setCustomError(""); }} className="rounded-lg border border-border px-4 py-1.5 text-xs font-semibold text-foreground hover:border-accent transition">Cancel</button>
            <button type="button" onClick={submitCustomJob} disabled={customSaving} className="inline-flex items-center gap-1.5 rounded-full bg-cta px-5 py-1.5 text-xs font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-50">
              {customSaving ? "Saving…" : "Build my resume →"}
            </button>
          </div>
        </div>
      )}

      {/* Spotlight + list */}
      {!loading && !error && spotlight && spotlight.job_discoveries && (
        <div className="space-y-3">
          <SpotlightCard
            row={spotlight}
            onStart={() => startApplication(spotlight.job_discoveries!.id)}
          />
          <p className="pt-3 text-xs font-medium uppercase tracking-[0.12em] text-muted">
            More matches for you
          </p>
          {rest.map((r) => (
            <RoleRow
              key={r.id}
              row={r}
              onStart={() => startApplication(r.job_discoveries!.id)}
            />
          ))}
        </div>
      )}

      {embedded && recs && (
        <p className="pt-4 text-center text-xs text-muted">
          Updated{" "}
          {new Date(recs.date_utc).toLocaleDateString(undefined, {
            weekday: "short",
            month: "short",
            day: "numeric",
          })}{" "}
          · Scout refreshes every 30 minutes
        </p>
      )}
    </div>
  );
}

function SpotlightCard({ row, onStart }: { row: Top20Row; onStart: () => void }) {
  const j = row.job_discoveries!;
  const chips = reasonChips(row.reason);
  return (
    <div className="rounded-2xl border-2 border-accent/40 bg-gradient-to-br from-accent/5 via-white to-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-accent/10 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-primary-700">
            ★ Top pick for you
          </span>
          <h3 className="mt-2.5 text-xl font-bold tracking-tight text-foreground">
            {j.title}
          </h3>
          <p className="mt-0.5 text-sm text-muted">{j.company_name}</p>
          {chips.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {chips.map((c, i) => (
                <span
                  key={i}
                  className="rounded-full bg-white px-2.5 py-1 text-[11px] text-muted ring-1 ring-border"
                >
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold tracking-tight text-accent">
            {pct(row.final_score)}%
          </div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
            match
          </div>
        </div>
      </div>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        {j.job_url && (
          <a
            href={j.job_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs font-semibold text-accent hover:text-accent-hover"
          >
            View the job post →
          </a>
        )}
        <button
          type="button"
          onClick={onStart}
          className="inline-flex items-center gap-2 rounded-full bg-cta px-5 py-2.5 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
        >
          Start custom application
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}

function RoleRow({ row, onStart }: { row: Top20Row; onStart: () => void }) {
  const j = row.job_discoveries!;
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-white p-4 transition hover:border-accent/40 hover:shadow-sm">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-muted">#{row.rank}</span>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-foreground">{j.title}</div>
            <div className="truncate text-xs text-muted">{j.company_name}</div>
          </div>
        </div>
        {row.reason && (
          <p className="mt-1 line-clamp-1 text-xs text-muted">{row.reason}</p>
        )}
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <div className="text-base font-bold text-accent">{pct(row.final_score)}%</div>
          <div className="text-[9px] font-semibold uppercase tracking-wider text-muted">
            match
          </div>
        </div>
        <button
          type="button"
          onClick={onStart}
          className="rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-cta hover:bg-cta hover:text-white"
        >
          Start →
        </button>
      </div>
    </div>
  );
}
