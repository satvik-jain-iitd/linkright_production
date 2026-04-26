"use client";

// SMA_v2 — Suggestions Inbox + Draft Editor.
// Polls /api/sma/suggestions every 30s; user picks concept → modal opens
// with generated draft → edit → publish to LinkedIn (via broadcast cron).

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

type Concept = {
  post_angle?: string;
  topic_tag?: string;
  hook_line?: string;
};

type Suggestion = {
  id: string;
  diary_entry_id: string | null;
  concepts: Concept[];
  status: string;
  picked_concept_index: number | null;
  created_at: string;
  picked_at: string | null;
};

type Draft = {
  id: string;
  draft_content: string;
  status: string;
  concept_index: number;
};

const POLL_MS = 30_000;

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.round(diff / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}

export function SuggestionsInbox() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeDraft, setActiveDraft] = useState<Draft | null>(null);
  const [picking, setPicking] = useState<{ sid: string; idx: number } | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch("/api/sma/suggestions?status=pending&limit=20", {
        cache: "no-store",
      });
      const body = await r.json();
      if (!r.ok) {
        setError(body.error ?? "Failed to load suggestions");
        return;
      }
      setSuggestions(body.suggestions ?? []);
      setError("");
    } catch {
      setError("Network error — retrying.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, POLL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [load]);

  const pickConcept = async (sid: string, idx: number) => {
    setPicking({ sid, idx });
    setError("");
    try {
      const r = await fetch(`/api/sma/suggestions/${sid}/pick`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ concept_index: idx }),
      });
      const body = await r.json();
      if (!r.ok) {
        setError(body.error ?? "Failed to generate draft");
        return;
      }
      setActiveDraft(body.draft);
      // Refresh inbox so the picked suggestion drops out
      load();
    } catch {
      setError("Network error generating draft.");
    } finally {
      setPicking(null);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Suggestions</h1>
          <p className="mt-1 text-sm text-muted">
            Diary likhne ke baad LinkedIn post concepts yahan dikhte hain. Ek
            pick karo, edit karo, LinkedIn pe publish karo.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-full border border-border bg-white px-3 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
        >
          Refresh
        </button>
      </div>

      {error && (
        <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </p>
      )}

      {loading ? (
        <div className="rounded-2xl border border-border bg-white p-10 text-center text-sm text-muted">
          Loading suggestions…
        </div>
      ) : suggestions.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-4">
          {suggestions.map((s) => (
            <SuggestionCard
              key={s.id}
              suggestion={s}
              onPick={pickConcept}
              picking={picking}
            />
          ))}
        </div>
      )}

      {activeDraft && (
        <DraftEditor
          draft={activeDraft}
          onClose={() => setActiveDraft(null)}
          onPublished={() => {
            setActiveDraft(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-border bg-white p-10 text-center">
      <h3 className="text-lg font-semibold">Nothing new yet</h3>
      <p className="mt-2 text-sm text-muted">
        Write a quick diary on the{" "}
        <Link href="/dashboard" className="text-accent">
          dashboard
        </Link>{" "}
        — within 30 seconds, three LinkedIn post concepts show up here.
      </p>
    </div>
  );
}

function SuggestionCard({
  suggestion,
  onPick,
  picking,
}: {
  suggestion: Suggestion;
  onPick: (sid: string, idx: number) => void;
  picking: { sid: string; idx: number } | null;
}) {
  const isPicking = (i: number) =>
    picking?.sid === suggestion.id && picking?.idx === i;
  const anyPicking = picking?.sid === suggestion.id;

  return (
    <div className="rounded-2xl border border-border bg-white p-5">
      <div className="mb-3 flex items-center justify-between">
        <span className="rounded-[10px] bg-pink-500/10 px-2.5 py-0.5 text-[11px] font-medium text-pink-700">
          {suggestion.concepts.length} concepts ready
        </span>
        <span className="text-xs text-muted">
          {relativeTime(suggestion.created_at)}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {suggestion.concepts.map((c, idx) => (
          <button
            key={idx}
            type="button"
            disabled={anyPicking}
            onClick={() => onPick(suggestion.id, idx)}
            className="group flex flex-col rounded-xl border border-border bg-surface p-4 text-left transition hover:border-accent hover:bg-white disabled:opacity-50"
          >
            {c.topic_tag && (
              <span className="mb-2 inline-block w-fit rounded-full bg-purple-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-purple-700">
                {c.topic_tag}
              </span>
            )}
            {c.hook_line && (
              <p className="text-sm font-semibold leading-snug text-foreground">
                {c.hook_line}
              </p>
            )}
            {c.post_angle && (
              <p className="mt-2 line-clamp-3 text-xs text-muted">
                {c.post_angle}
              </p>
            )}
            <span
              className={`mt-3 text-[11px] font-semibold ${
                isPicking(idx) ? "text-accent" : "text-muted group-hover:text-accent"
              }`}
            >
              {isPicking(idx) ? "Drafting…" : "Pick this →"}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function DraftEditor({
  draft,
  onClose,
  onPublished,
}: {
  draft: Draft;
  onClose: () => void;
  onPublished: () => void;
}) {
  const [content, setContent] = useState(draft.draft_content);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState("");
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const saveEdit = async () => {
    setSaving(true);
    setError("");
    try {
      const r = await fetch(`/api/sma/drafts/${draft.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ draft_content: content }),
      });
      const body = await r.json();
      if (!r.ok) {
        setError(body.error ?? "Failed to save");
        return;
      }
      setSavedAt(new Date().toISOString());
    } catch {
      setError("Network error saving.");
    } finally {
      setSaving(false);
    }
  };

  const publish = async () => {
    if (!content.trim()) {
      setError("Draft is empty.");
      return;
    }
    if (
      !confirm("Publish this to LinkedIn? It posts within ~5 minutes via your connected account.")
    ) {
      return;
    }
    setPublishing(true);
    setError("");
    try {
      // Save edits first (idempotent)
      if (content !== draft.draft_content) await saveEdit();
      const r = await fetch(`/api/sma/drafts/${draft.id}/publish`, {
        method: "POST",
      });
      const body = await r.json();
      if (!r.ok) {
        setError(body.error ?? "Publish failed");
        return;
      }
      onPublished();
    } catch {
      setError("Network error publishing.");
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-border bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h2 className="text-base font-semibold">Edit draft</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-muted hover:text-foreground"
          >
            ✕
          </button>
        </div>

        <div className="p-5">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={14}
            className="w-full resize-y rounded-xl border border-border bg-surface px-4 py-3 text-[14.5px] leading-[1.6] focus:border-accent focus:bg-white focus:outline-none"
          />
          <div className="mt-2 flex items-center justify-between text-xs text-muted">
            <span>
              {content.length} / 3000 characters
              {savedAt && <span className="ml-2 text-accent">· saved</span>}
            </span>
            {error && <span className="text-red-600">{error}</span>}
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-border bg-surface px-5 py-3">
          <button
            type="button"
            onClick={saveEdit}
            disabled={saving || publishing || content === draft.draft_content}
            className="rounded-full border border-border bg-white px-4 py-2 text-xs font-semibold text-foreground transition hover:border-accent disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save edits"}
          </button>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-border bg-white px-4 py-2 text-xs font-semibold text-foreground transition hover:border-accent"
            >
              Close
            </button>
            <button
              type="button"
              onClick={publish}
              disabled={publishing || saving || !content.trim()}
              className="rounded-lg bg-cta px-4 py-2 text-xs font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-50"
            >
              {publishing ? "Publishing…" : "Publish to LinkedIn"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
