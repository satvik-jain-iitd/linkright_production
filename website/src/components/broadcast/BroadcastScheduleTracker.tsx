"use client";

// Wave 2 / S18 — Schedule + tracker.
// Tabs: Scheduled | Posted | Drafts. Analytics rail on the right.

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type Post = {
  id: string;
  status: "draft" | "scheduled" | "posted" | "failed" | "cancelled";
  content: string;
  scheduled_at: string | null;
  posted_at: string | null;
  engagement_json: {
    likes?: number;
    comments?: number;
    shares?: number;
    impressions?: number;
  } | null;
  created_at: string;
};

const TABS = [
  { key: "scheduled", label: "Scheduled" },
  { key: "posted", label: "Posted" },
  { key: "draft", label: "Drafts" },
] as const;

function formatWhen(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function BroadcastScheduleTracker() {
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("scheduled");
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!cancelled) setLoading(true);
      const res = await fetch(`/api/broadcast/posts?status=${tab}`, {
        cache: "no-store",
      });
      if (cancelled) return;
      if (res.ok) {
        const body = await res.json();
        if (!cancelled) setPosts(body.posts ?? []);
      }
      if (!cancelled) setLoading(false);
    };
    queueMicrotask(() => {
      if (!cancelled) run();
    });
    return () => {
      cancelled = true;
    };
  }, [tab, reloadTick]);

  const deletePost = async (id: string) => {
    if (!confirm("Delete this post?")) return;
    const res = await fetch(`/api/broadcast/posts/${id}`, { method: "DELETE" });
    if (res.ok) setReloadTick((x) => x + 1);
  };

  const counts = useMemo(() => {
    const totals = { scheduled: 0, posted: 0, draft: 0 };
    for (const p of posts) {
      if (p.status in totals) totals[p.status as keyof typeof totals]++;
    }
    return totals;
  }, [posts]);

  // Aggregate engagement from posted list. `nowMs` is frozen at mount —
  // component re-mounts on navigation, which is often enough for "last 30 days".
  const [nowMs] = useState(() => Date.now());
  const posted30 = useMemo(() => {
    if (tab !== "posted") return { impressions: 0, likes: 0, comments: 0 };
    const cutoff = nowMs - 30 * 86400 * 1000;
    return posts.reduce(
      (acc, p) => {
        if (p.posted_at && new Date(p.posted_at).getTime() >= cutoff) {
          acc.impressions += p.engagement_json?.impressions ?? 0;
          acc.likes += p.engagement_json?.likes ?? 0;
          acc.comments += p.engagement_json?.comments ?? 0;
        }
        return acc;
      },
      { impressions: 0, likes: 0, comments: 0 },
    );
  }, [posts, tab, nowMs]);

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-pink-700">
            Broadcast · schedule
          </p>
          <h1 className="mt-2 text-[28px] font-bold tracking-tight">
            Your voice, on a schedule.
          </h1>
          <p className="mt-1 text-sm text-muted">
            {counts.scheduled} queued · {counts.posted} posted · {counts.draft}{" "}
            drafts
          </p>
        </div>
        <Link
          href="/dashboard/broadcast"
          className="inline-flex items-center gap-2 rounded-lg bg-cta px-3.5 py-1.5 text-xs font-semibold text-white shadow-cta transition hover:bg-cta-hover"
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
              d="M12 4.5v15m7.5-7.5h-15"
            />
          </svg>
          New post
        </Link>
      </div>

      {/* Tabs */}
      <div className="mb-5 flex gap-6 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={
              tab === t.key
                ? "-mb-px border-b-2 border-accent pb-2.5 text-sm font-semibold text-foreground"
                : "pb-2.5 text-sm font-medium text-muted transition hover:text-foreground"
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        {/* Posts list */}
        <div className="space-y-3">
          {loading && (
            <div className="h-20 animate-pulse rounded-xl border border-border bg-white" />
          )}
          {!loading && posts.length === 0 && (
            <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center">
              <p className="text-sm font-semibold">
                {tab === "scheduled"
                  ? "Nothing queued."
                  : tab === "posted"
                    ? "No posts shipped yet."
                    : "No drafts saved."}
              </p>
              <p className="mt-1 text-xs text-muted">
                Draft something from your moments.
              </p>
              <Link
                href="/dashboard/broadcast"
                className="mt-3 inline-block rounded-full border border-border px-4 py-1.5 text-xs font-semibold transition hover:border-accent hover:text-accent"
              >
                Pick an insight →
              </Link>
            </div>
          )}
          {posts.map((p) => (
            <article
              key={p.id}
              className="rounded-xl border border-border bg-white p-4.5 p-5"
            >
              <div className="flex items-start justify-between gap-3">
                {p.status === "scheduled" ? (
                  <span className="inline-flex items-center gap-1 rounded-[10px] bg-gold-500/15 px-2.5 py-0.5 text-[11px] font-medium text-gold-700">
                    <svg
                      className="h-3 w-3"
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
                    {formatWhen(p.scheduled_at)}
                  </span>
                ) : p.status === "posted" ? (
                  <span className="rounded-[10px] bg-primary-500/10 px-2.5 py-0.5 text-[11px] font-medium text-primary-700">
                    ✓ Posted {formatWhen(p.posted_at)}
                  </span>
                ) : (
                  <span className="rounded-full border border-border bg-white px-2.5 py-0.5 text-[11px] font-medium text-muted">
                    Draft
                  </span>
                )}
                <div className="flex gap-1">
                  {p.status !== "posted" && (
                    <Link
                      href={`/dashboard/broadcast/compose?post_id=${p.id}`}
                      className="rounded-full border border-border bg-white px-2.5 py-1 text-[11px] font-semibold text-foreground transition hover:border-accent"
                    >
                      Edit
                    </Link>
                  )}
                  <button
                    type="button"
                    onClick={() => deletePost(p.id)}
                    className="rounded-full border border-border bg-white px-2.5 py-1 text-[11px] text-muted transition hover:border-red-200 hover:text-red-600"
                  >
                    Delete
                  </button>
                </div>
              </div>
              <p className="mt-2.5 line-clamp-3 text-[13px] leading-relaxed text-foreground whitespace-pre-line">
                {p.content}
              </p>
              {p.engagement_json && (
                <div className="mt-3 flex gap-4 border-t border-dashed border-border pt-2.5 text-xs text-muted">
                  <span>👍 {p.engagement_json.likes ?? 0}</span>
                  <span>💬 {p.engagement_json.comments ?? 0}</span>
                  <span>↗ {p.engagement_json.shares ?? 0}</span>
                </div>
              )}
            </article>
          ))}
        </div>

        {/* Analytics rail */}
        <aside className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-pink-700">
            Last 30 days
          </p>
          <div className="mt-2 text-[36px] font-bold tracking-tight">
            {posted30.impressions.toLocaleString("en-IN")}
          </div>
          <p className="text-xs text-muted">total impressions</p>

          <div className="mt-5 grid grid-cols-2 gap-3">
            {[
              [posted30.likes.toString(), "total reactions"],
              [posted30.comments.toString(), "total comments"],
              [counts.posted.toString(), "posts shipped"],
              [counts.scheduled.toString(), "in queue"],
            ].map(([n, l]) => (
              <div key={l}>
                <div className="text-lg font-bold tracking-tight">{n}</div>
                <div className="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
                  {l}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-5 border-t border-border pt-4 text-[11px] leading-relaxed text-muted">
            Engagement updates from LinkedIn every 30 minutes via n8n.
          </p>
        </aside>
      </div>
    </div>
  );
}
