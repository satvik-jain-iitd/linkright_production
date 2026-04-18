"use client";

// Wave 2 / S17 — Compose broadcast post.
// Left: draft textarea + tone chips + save/schedule actions.
// Right: source insight panel + live LinkedIn preview.

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type Insight = {
  id: string;
  kind: "nugget" | "diary";
  title: string;
  body: string;
  source: string;
  type: string;
};

type ExistingPost = {
  id: string;
  status: string;
  content: string;
  scheduled_at: string | null;
  source_insight_id: string | null;
  source_insight_kind: string | null;
};

const TONES = [
  { key: "shorter", label: "Shorter" },
  { key: "punchier", label: "Punchier" },
  { key: "more_personal", label: "More personal" },
  { key: "add_question", label: "Add a question at the end" },
  { key: "sharper", label: "Sharper takeaway" },
] as const;

interface Props {
  insightId: string | null;
  insightKind: "nugget" | "diary" | null;
  existingPostId: string | null;
  authorName: string;
  authorEmail: string;
}

function initials(name: string): string {
  return name
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2) || "U";
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    day: "numeric",
    month: "short",
  });
}

export function BroadcastCompose({
  insightId,
  insightKind,
  existingPostId,
  authorName,
  authorEmail,
}: Props) {
  const router = useRouter();
  const [insight, setInsight] = useState<Insight | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [regensRemaining, setRegensRemaining] = useState<number | null>(null);
  const [scheduleAt, setScheduleAt] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);

  const loadInsight = useCallback(async () => {
    if (!insightId) return null;
    // Fetch all insights — lightweight — then find the one we need. The
    // browser endpoint is already cached & user-scoped, and it returns both
    // kinds in one shot.
    const res = await fetch("/api/broadcast/insights?limit=80", {
      cache: "no-store",
    });
    if (!res.ok) return null;
    const body = await res.json();
    const found = (body.insights as Insight[]).find((i) => i.id === insightId);
    return found ?? null;
  }, [insightId]);

  const initialDraft = useCallback(async () => {
    if (!insightId || !insightKind) return;
    setGenerating(true);
    setError("");
    try {
      const res = await fetch("/api/broadcast/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ insight_id: insightId, insight_kind: insightKind }),
      });
      const body = await res.json();
      if (!res.ok) {
        setError(body.error ?? "Couldn't generate draft. Try again.");
        return;
      }
      setDraft(body.content ?? "");
      setRegensRemaining(body.regens_remaining ?? null);
    } catch {
      setError("Network error — try again.");
    } finally {
      setGenerating(false);
    }
  }, [insightId, insightKind]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      if (existingPostId) {
        const res = await fetch(`/api/broadcast/posts?status=`, {
          cache: "no-store",
        });
        if (res.ok) {
          const body = await res.json();
          const p = (body.posts ?? []).find((x: ExistingPost) => x.id === existingPostId);
          if (p && mounted) {
            setDraft(p.content);
            if (p.scheduled_at) setScheduleAt(p.scheduled_at);
          }
        }
      }
      const i = await loadInsight();
      if (!mounted) return;
      setInsight(i);
      if (!existingPostId && insightId) {
        await initialDraft();
      }
      setLoading(false);
    })();
    return () => {
      mounted = false;
    };
  }, [existingPostId, insightId, loadInsight, initialDraft]);

  const regenerate = async (tone?: (typeof TONES)[number]["key"]) => {
    if (!insightId || !insightKind) return;
    setGenerating(true);
    setError("");
    try {
      const res = await fetch("/api/broadcast/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          insight_id: insightId,
          insight_kind: insightKind,
          tone,
          previous_draft: draft,
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        setError(body.error ?? "Couldn't regenerate draft.");
        return;
      }
      setDraft(body.content ?? draft);
      setRegensRemaining(body.regens_remaining ?? regensRemaining);
    } catch {
      setError("Network error — try again.");
    } finally {
      setGenerating(false);
    }
  };

  const save = async (mode: "draft" | "schedule" | "post_now") => {
    if (!draft.trim()) {
      setError("Draft is empty — write something first.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const status = mode === "draft" ? "draft" : mode === "schedule" ? "scheduled" : "posted";
      const scheduled_at =
        mode === "schedule" ? scheduleAt || new Date(Date.now() + 60 * 60 * 1000).toISOString() : null;
      const res = await fetch("/api/broadcast/posts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: draft,
          status,
          scheduled_at,
          source_insight_id: insightId,
          source_insight_kind: insightKind,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? "Save failed.");
        return;
      }
      router.push("/dashboard/broadcast/schedule");
    } catch {
      setError("Network error — try again.");
    } finally {
      setSaving(false);
    }
  };

  const charCount = draft.length;
  const charLimit = 3000;
  const previewLines = useMemo(
    () =>
      draft
        .split("\n")
        .slice(0, 5)
        .join("\n")
        .slice(0, 280),
    [draft],
  );

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Link
          href="/dashboard/broadcast"
          className="rounded-full border border-border bg-white px-3 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
        >
          ← Back
        </Link>
        <span className="rounded-full bg-pink-500/10 px-2.5 py-0.5 text-[11px] font-medium text-pink-700">
          Drafting a post
        </span>
        {insight && (
          <span className="rounded-full border border-border bg-white px-2.5 py-0.5 text-[11px] text-foreground">
            Based on: {insight.title}
          </span>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        {/* Compose */}
        <div>
          <div className="rounded-2xl border border-border bg-white p-6">
            <div className="flex items-center gap-2.5 border-b border-border pb-3.5">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-sm font-bold text-white">
                {initials(authorName || authorEmail)}
              </div>
              <div>
                <div className="text-sm font-semibold">
                  {authorName || authorEmail}
                </div>
                <div className="text-xs text-muted">
                  Posts to LinkedIn under your account
                </div>
              </div>
            </div>
            {loading || generating ? (
              <div className="py-8 text-center text-sm text-muted">
                {generating ? "Drafting from your source moment…" : "Loading…"}
              </div>
            ) : (
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={14}
                className="mt-3 w-full resize-y border-0 bg-transparent text-[15px] leading-[1.65] focus:outline-none"
                placeholder="Start typing — or regenerate from the source to get a draft."
              />
            )}
            <div className="mt-3 flex items-center justify-between border-t border-border pt-3">
              <span className="text-xs text-muted">
                {charCount} / {charLimit} characters · LinkedIn-friendly length
              </span>
              <span className="rounded-full bg-purple-500/10 px-2.5 py-0.5 text-[11px] font-medium text-purple-700">
                {regensRemaining != null
                  ? `${regensRemaining} regens left`
                  : "AI draft"}
              </span>
            </div>
          </div>

          {/* Tone chips */}
          {insightId && (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="mr-1 text-xs font-semibold text-muted">Adjust:</span>
              {TONES.map((t) => (
                <button
                  key={t.key}
                  type="button"
                  disabled={generating || regensRemaining === 0}
                  onClick={() => regenerate(t.key)}
                  className="rounded-full border border-border bg-white px-3 py-1.5 text-xs font-medium text-foreground transition hover:border-accent hover:text-accent disabled:opacity-50"
                >
                  {t.label}
                </button>
              ))}
            </div>
          )}

          {error && (
            <p className="mt-3 rounded-lg bg-red-50 p-2 text-xs text-red-600">
              {error}
            </p>
          )}

          {/* Actions */}
          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              disabled={saving || !draft.trim()}
              onClick={() => save("draft")}
              className="rounded-full border border-border bg-white px-4 py-2 text-sm font-semibold text-foreground transition hover:border-accent disabled:opacity-50"
            >
              Save as draft
            </button>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setPickerOpen((x) => !x)}
                className="inline-flex items-center gap-2 rounded-full border border-border bg-white px-3.5 py-2 text-sm font-semibold text-foreground transition hover:border-accent"
              >
                <svg
                  className="h-4 w-4"
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
                {scheduleAt
                  ? `Schedule · ${formatWhen(scheduleAt)}`
                  : "Schedule"}
              </button>
              <button
                type="button"
                disabled={saving || !draft.trim() || !scheduleAt}
                onClick={() => save("schedule")}
                className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-accent-hover disabled:opacity-50"
              >
                Queue for posting
              </button>
              <button
                type="button"
                disabled={saving || !draft.trim()}
                onClick={() => {
                  if (
                    confirm(
                      "Post this to LinkedIn now? We'll attempt to publish via your connected account.",
                    )
                  ) {
                    save("post_now");
                  }
                }}
                className="rounded-full bg-cta px-4 py-2 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-50"
              >
                Post now
              </button>
            </div>
          </div>

          {pickerOpen && (
            <div className="mt-3 rounded-xl border border-border bg-white p-3">
              <label className="text-xs font-semibold text-foreground">
                Pick date & time
              </label>
              <input
                type="datetime-local"
                value={scheduleAt ? scheduleAt.slice(0, 16) : ""}
                onChange={(e) =>
                  setScheduleAt(
                    e.target.value ? new Date(e.target.value).toISOString() : "",
                  )
                }
                className="mt-2 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent focus:outline-none"
              />
              <p className="mt-2 text-[11px] text-muted">
                We&apos;ll tell n8n to post at this time. You can still edit the
                draft right up to 5 minutes before.
              </p>
            </div>
          )}
        </div>

        {/* Right rail */}
        <div className="space-y-4">
          {/* Source */}
          <div
            className="rounded-2xl border p-5"
            style={{ background: "#FDF6F0", borderColor: "#F8E6D4" }}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#8A6E53]">
              Source
            </p>
            {insight ? (
              <>
                <p className="mt-2 text-sm font-semibold">{insight.title}</p>
                <p className="mt-2 text-[12.5px] leading-relaxed text-[#5F4632]">
                  {insight.body}
                </p>
                <p className="mt-3 text-[11px] text-[#8A6E53]">
                  {insight.source}
                </p>
              </>
            ) : (
              <p className="mt-2 text-xs text-muted">
                No source attached. Pick one from the{" "}
                <Link href="/dashboard/broadcast" className="text-accent">
                  insights browser
                </Link>
                .
              </p>
            )}
          </div>

          {/* LinkedIn preview */}
          <div className="overflow-hidden rounded-2xl border border-border">
            <div className="border-b border-[#E2E8F0] bg-[#F3F2EF] px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#666]">
              Preview on LinkedIn
            </div>
            <div className="bg-white p-4">
              <div className="flex items-start gap-2.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-sm font-bold text-white">
                  {initials(authorName || authorEmail)}
                </div>
                <div>
                  <div className="text-[13px] font-semibold text-[#111]">
                    {authorName || authorEmail}{" "}
                    <span className="text-[11px] font-normal text-[#666]">
                      · You
                    </span>
                  </div>
                  <div className="text-[11px] text-[#666]">
                    {authorEmail || "LinkedIn member"}
                  </div>
                  <div className="text-[11px] text-[#666]">Now · 🌐</div>
                </div>
              </div>
              <p className="mt-3 whitespace-pre-line text-[13px] leading-[1.55] text-black">
                {previewLines || "Your post will appear here."}
              </p>
              {draft.length > 280 && (
                <p className="mt-2 text-[11px] text-[#0a66c2]">…see more</p>
              )}
              <div className="mt-3.5 flex gap-4 border-t border-[#E2E8F0] pt-2.5 text-[11px] text-[#666]">
                <span>👍 Like</span>
                <span>💬 Comment</span>
                <span>↗ Share</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
