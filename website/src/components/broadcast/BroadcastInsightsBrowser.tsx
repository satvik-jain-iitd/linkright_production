"use client";

// Wave 2 / S16 — Insights browser.
// Grid of moments pulled from /api/broadcast/insights. Click "Write a post"
// → /dashboard/broadcast/compose?insight_id=X&kind=nugget|diary.

import { useEffect, useState } from "react";
import Link from "next/link";

type Insight = {
  id: string;
  kind: "nugget" | "diary";
  title: string;
  body: string;
  source: string;
  type: string;
  accent: "teal" | "purple" | "gold" | "pink";
  created_at: string;
};

const FILTERS = ["All", "Wins", "Learnings", "Takes", "Failures", "Shipped"] as const;

const CHIP: Record<string, string> = {
  teal: "bg-primary-500/10 text-primary-700",
  purple: "bg-purple-500/10 text-purple-700",
  gold: "bg-gold-500/15 text-gold-700",
  pink: "bg-pink-500/10 text-pink-700",
};

type Status = {
  linkedin_connected: boolean;
  oauth_configured: boolean;
  counts: { scheduled: number; posted: number; draft: number };
};

export function BroadcastInsightsBrowser() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");
  const [insights, setInsights] = useState<Insight[]>([]);
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [smaPending, setSmaPending] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!cancelled) setLoading(true);
      const qs = filter === "All" ? "" : `?filter=${filter.toLowerCase()}`;
      const [iRes, sRes, smaRes] = await Promise.all([
        fetch(`/api/broadcast/insights${qs}`, { cache: "no-store" }),
        fetch("/api/broadcast/status", { cache: "no-store" }),
        fetch("/api/sma/suggestions?status=pending&limit=20", { cache: "no-store" }),
      ]);
      if (cancelled) return;
      if (iRes.ok) {
        const body = await iRes.json();
        if (!cancelled) setInsights(body.insights ?? []);
      }
      if (sRes.ok) {
        const body = await sRes.json();
        if (!cancelled) setStatus(body);
      }
      if (smaRes.ok) {
        const body = await smaRes.json();
        if (!cancelled) setSmaPending((body.suggestions ?? []).length);
      }
      if (!cancelled) setLoading(false);
    };
    // Defer loading state + fetches out of the synchronous effect body so the
    // react-hooks/set-state-in-effect rule is happy.
    queueMicrotask(() => {
      if (!cancelled) run();
    });
    return () => {
      cancelled = true;
    };
  }, [filter]);

  const queued = status?.counts?.scheduled ?? 0;

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-pink-700">
            Broadcast
          </p>
          <h1 className="mt-2 text-[28px] font-bold tracking-tight">
            Pick something worth posting.
          </h1>
          <p className="mt-1 text-sm text-muted">
            Drawn from your diary, profile, and application outcomes. All true.
          </p>
        </div>
        <Link
          href="/dashboard/broadcast/schedule"
          className="inline-flex items-center gap-2 rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
        >
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75"
            />
          </svg>
          Schedule · {queued} queued
        </Link>
      </div>

      {/* SMA suggestions banner — surfaces pending diary-driven concepts */}
      {smaPending > 0 && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-pink-500/40 bg-gradient-to-r from-pink-500/10 to-purple-500/5 p-4">
          <div>
            <p className="text-sm font-semibold text-pink-700">
              {smaPending} suggestion{smaPending === 1 ? "" : "s"} ready from your diary
            </p>
            <p className="mt-0.5 text-xs text-muted">
              Pick a concept, edit, publish — all in one click.
            </p>
          </div>
          <Link
            href="/dashboard/suggestions"
            className="rounded-lg bg-pink-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-pink-700"
          >
            View suggestions →
          </Link>
        </div>
      )}

      {/* Connect banner if LinkedIn not connected */}
      {status && !status.linkedin_connected && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-pink-500/30 bg-pink-500/5 p-4">
          <div>
            <p className="text-sm font-semibold text-pink-700">
              Drafting now, posting later.
            </p>
            <p className="mt-0.5 text-xs text-muted">
              You can draft posts without LinkedIn connected — we&apos;ll just need
              it to publish.
            </p>
          </div>
          <Link
            href="/dashboard/broadcast/connect"
            className="rounded-lg bg-cta px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-cta-hover"
          >
            Connect LinkedIn →
          </Link>
        </div>
      )}

      {/* Filter chips */}
      <div className="mb-5 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={
              filter === f
                ? "rounded-[10px] bg-pink-500/10 px-3.5 py-1.5 text-xs font-semibold text-pink-700"
                : "rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-medium text-foreground transition hover:border-accent"
            }
          >
            {f}
            {f === "All" && ` · ${insights.length}`}
          </button>
        ))}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-44 animate-pulse rounded-2xl border border-border bg-white"
            />
          ))}
        </div>
      ) : insights.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center">
          <p className="text-sm font-semibold">Not enough material yet.</p>
          <p className="mt-1 text-xs text-muted">
            Keep logging diary entries and shipping work — we&apos;ll start
            suggesting posts after ~7 entries.
          </p>
          <Link
            href="/dashboard"
            className="mt-3 inline-block rounded-full border border-border px-4 py-1.5 text-xs font-semibold transition hover:border-accent hover:text-accent"
          >
            Go log a diary entry →
          </Link>
        </div>
      ) : (
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {insights.map((i) => (
            <article
              key={i.id}
              className="flex flex-col rounded-2xl border border-border bg-white p-5 transition hover:border-accent/40 hover:shadow-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${CHIP[i.accent]}`}>
                  {i.type}
                </span>
                <span className="text-[11px] text-muted">{i.source}</span>
              </div>
              <h3 className="mt-2.5 text-[15px] font-semibold leading-snug tracking-tight">
                {i.title || "(Untitled)"}
              </h3>
              <p className="mt-1.5 line-clamp-4 flex-1 text-[12.5px] leading-relaxed text-muted">
                {i.body}
              </p>
              <Link
                href={`/dashboard/broadcast/compose?insight_id=${encodeURIComponent(i.id)}&kind=${i.kind}`}
                className="mt-4 inline-flex items-center gap-1.5 self-start rounded-full border border-accent bg-white px-3.5 py-1.5 text-[11.5px] font-semibold text-accent transition hover:bg-accent hover:text-white"
              >
                Write a post about this →
              </Link>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
