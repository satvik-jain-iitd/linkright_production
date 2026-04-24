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

const MAX_POLLS = 8;
const POLL_INTERVAL_MS = 10_000;

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
  const [pollCount, setPollCount] = useState(0);

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

  // Poll every 10s (up to 80s) while top20 is empty — matches may still be computing
  useEffect(() => {
    const hasMatches = (recs?.top20 ?? []).filter((r) => r.job_discoveries).length > 0;
    if (!loading && recs && !hasMatches && pollCount < MAX_POLLS) {
      const timer = setTimeout(() => {
        setPollCount((c) => c + 1);
        load();
      }, POLL_INTERVAL_MS);
      return () => clearTimeout(timer);
    }
  }, [loading, recs, pollCount, load]);

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
                        ? "rounded-[10px] bg-accent px-3 py-1.5 font-semibold text-white"
                        : s.state === "done"
                          ? "rounded-[10px] bg-accent/10 px-3 py-1.5 font-medium text-primary-700"
                          : "rounded-[10px] border border-border bg-white px-3 py-1.5 font-medium text-muted"
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

      {/* Loading — s08a: 2-col calibrating state */}
      {loading && (
        <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 rounded-2xl border border-border bg-white p-4">
                <div className="h-12 w-12 flex-shrink-0 animate-pulse rounded-xl bg-[#F3F4F6]" />
                <div className="flex-1 space-y-2">
                  <div className="h-3.5 animate-pulse rounded bg-[#E2E8F0]" style={{ width: `${45 + i * 7}%` }} />
                  <div className="h-2.5 animate-pulse rounded bg-[#E8ECF0]" style={{ width: "30%" }} />
                  <div className="flex gap-1.5">
                    {[0, 1, 2].map((j) => (
                      <div key={j} className="h-5 w-14 animate-pulse rounded-full bg-[#F3F4F6]" />
                    ))}
                  </div>
                </div>
                <div className="h-8 w-16 animate-pulse rounded-full bg-[#F3F4F6]" />
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-border bg-white p-5 self-start">
            <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-[#09766D]">What Scout is doing</div>
            <div className="space-y-2.5">
              {[
                { t: "Scanning active listings", done: true },
                { t: "Matching against your profile", done: true },
                { t: "Filtering by your preferences", active: true },
                { t: "Ranking by fit + recency", pending: true },
                { t: "Enriching with company signals", pending: true },
              ].map((s, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  <div
                    style={{
                      width: 14, height: 14, borderRadius: "50%", flexShrink: 0,
                      background: s.done ? "var(--color-accent, #0FBEAF)" : s.active ? "rgba(15,190,175,0.2)" : "#F3F4F6",
                      border: s.active ? "2px solid var(--color-accent, #0FBEAF)" : "none",
                      display: "inline-flex", alignItems: "center", justifyContent: "center",
                      color: "#fff", fontSize: 9,
                    }}
                  >{s.done && "✓"}</div>
                  <span className={`text-xs ${s.pending ? "text-muted" : "text-foreground"} ${s.active ? "font-semibold" : ""}`}>{s.t}</span>
                </div>
              ))}
            </div>
            <p className="mt-4 border-t border-border pt-3 text-[11px] leading-relaxed text-muted">
              Matches appear as soon as they&apos;re ready — no need to wait here.
            </p>
          </div>
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

      {/* Empty — computing (spinner) or timed out (s08b rich empty state) */}
      {!loading && !error && rows.length === 0 && !customOpen && (
        <>
          {pollCount < MAX_POLLS ? (
            // Still polling — matches are being computed
            <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center">
              <div className="mx-auto mb-3 h-5 w-5 animate-spin rounded-full border-2 border-border border-t-accent" />
              <p className="text-sm font-semibold text-foreground">Computing your first matches…</p>
              <p className="mt-1 text-xs text-muted">Scoring jobs against your profile. This takes about 30–60 seconds.</p>
            </div>
          ) : (
            // s08b: rich no-matches state
            <div className="grid gap-5 lg:grid-cols-[1fr_280px]">
              <div
                className="rounded-2xl border border-border p-10 text-center"
                style={{ background: "linear-gradient(180deg, #FDF6F0 0%, #fff 60%)" }}
              >
                <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent/10 text-accent">
                  <svg className="h-8 w-8" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-foreground">Nothing matches today — and that&apos;s fine.</h3>
                <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-muted">
                  Your filters are tight. Here&apos;s how to widen the net without lowering the bar.
                </p>

                <div className="mx-auto mt-6 max-w-lg space-y-2.5 text-left">
                  {[
                    { t: "Widen location", d: "Include more cities or Remote-India", action: "Try it", onClick: () => {} },
                    { t: "Include early-stage companies", d: "Seed & Series A may have more openings", action: "Try it", onClick: () => {} },
                    { t: "Keep these filters, notify me", d: "We'll ping you the moment one lands", action: "Turn on", onClick: () => {} },
                  ].map((s) => (
                    <div key={s.t} className="flex items-center gap-3 rounded-xl border border-border bg-white p-3.5">
                      <div className="flex-1">
                        <div className="text-[13px] font-semibold text-foreground">{s.t}</div>
                        <div className="text-[11.5px] text-muted">{s.d}</div>
                      </div>
                      <button
                        type="button"
                        onClick={s.onClick}
                        className="rounded-full border border-accent px-3.5 py-1.5 text-[11px] font-semibold text-accent transition hover:bg-accent/5"
                      >
                        {s.action}
                      </button>
                    </div>
                  ))}
                </div>

                <div className="mt-5 flex flex-wrap justify-center gap-2.5">
                  <button
                    type="button"
                    onClick={() => { setPollCount(0); load(); }}
                    className="rounded-lg border border-border px-4 py-2 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
                  >
                    Refresh
                  </button>
                  <Link
                    href="/onboarding/preferences"
                    className="rounded-lg border border-border px-4 py-2 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
                  >
                    Tune preferences
                  </Link>
                  <button
                    type="button"
                    onClick={() => setCustomOpen(true)}
                    className="rounded-lg bg-cta px-4 py-2 text-xs font-semibold text-white shadow-cta transition hover:bg-cta-hover"
                  >
                    Add a custom job →
                  </button>
                </div>
              </div>

              <div className="rounded-2xl border border-border bg-white p-5 self-start">
                <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">While you wait</div>
                <div className="space-y-2">
                  {[
                    { t: "Practice an interview drill", d: "Stay sharp between applications", href: "/dashboard/interview-prep" },
                    { t: "Add companies to watch", d: "Get pinged when they open a role", href: "/onboarding/preferences" },
                    { t: "Log a win from today", d: "Feeds tomorrow's resume", href: "/onboarding/profile" },
                  ].map((s) => (
                    <Link
                      key={s.t}
                      href={s.href}
                      className="block rounded-xl border border-border p-3 transition hover:border-accent"
                    >
                      <div className="text-[12.5px] font-semibold text-foreground">{s.t}</div>
                      <div className="mt-0.5 text-[11px] text-muted">{s.d}</div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
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
            <button type="button" onClick={submitCustomJob} disabled={customSaving} className="inline-flex items-center gap-1.5 rounded-lg bg-cta px-5 py-1.5 text-xs font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-50">
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
          <span className="inline-flex items-center gap-1.5 rounded-[10px] bg-accent/10 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-primary-700">
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
                  className="rounded-[10px] bg-white px-2.5 py-1 text-[11px] text-muted ring-1 ring-border"
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
          className="inline-flex items-center gap-2 rounded-lg bg-cta px-5 py-2.5 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
        >
          Customise Resume
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
          className="rounded-lg border border-border bg-white px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-cta hover:bg-cta hover:text-white"
        >
          Customise →
        </button>
      </div>
    </div>
  );
}
