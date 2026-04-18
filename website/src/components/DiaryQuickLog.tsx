"use client";

// Wave 2 / S19 — Daily diary quick-log widget.
// Compact right-rail card on the dashboard. Also reusable as a modal.
// Posts to /api/diary which returns { entry, streak }.

import { useState } from "react";

interface Props {
  /** kept for API-compatibility with existing callers; not displayed. */
  initialStreak?: number;
  /** fired with the new streak count after a save — callers may still use it. */
  onLogged?: (streak: number) => void;
  variant?: "card" | "modal";
  onClose?: () => void;
}

const HINT_PROMPTS = [
  "What did you ship?",
  "What did you learn?",
  "What pissed you off?",
  "Who surprised you?",
];

export function DiaryQuickLog({
  onLogged,
  variant = "card",
  onClose,
}: Props) {
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [savedJustNow, setSavedJustNow] = useState(false);

  const save = async () => {
    if (!content.trim() || saving) return;
    setSaving(true);
    setError("");
    try {
      const res = await fetch("/api/diary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content.trim(), source: "web" }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? "Save failed — try again.");
        return;
      }
      const body = (await res.json()) as { streak: number };
      setContent("");
      setSavedJustNow(true);
      onLogged?.(body.streak);
      setTimeout(() => setSavedJustNow(false), 2400);
    } catch {
      setError("Network error — try again.");
    } finally {
      setSaving(false);
    }
  };

  const header = (
    <div className="flex items-center justify-between">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-purple-700">
        Daily diary
      </p>
      {/* Streak chip deleted per v2 audit (gamification contradicted
          product positioning). Activity is visible elsewhere. */}
    </div>
  );

  const body = (
    <>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {HINT_PROMPTS.map((h) => (
          <button
            type="button"
            key={h}
            onClick={() =>
              setContent(
                (prev) => (prev ? prev.trimEnd() + " " : "") + h + " ",
              )
            }
            className="rounded-full border border-border bg-white px-2 py-0.5 text-[11px] text-muted transition hover:border-accent hover:text-accent"
          >
            {h}
          </button>
        ))}
      </div>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Just write. Doesn't have to be polished."
        rows={variant === "modal" ? 5 : 3}
        className="mt-2.5 w-full resize-none rounded-lg border border-border bg-white p-2.5 text-sm leading-relaxed focus:border-accent focus:outline-none"
      />
      {error && (
        <p className="mt-2 text-xs text-red-600">{error}</p>
      )}
      {savedJustNow && (
        <p className="mt-2 text-xs font-semibold text-accent">
          +1 added to your profile
        </p>
      )}
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-[11px] text-muted">
          +1 highlight added to your profile
        </span>
        <div className="flex gap-2">
          {variant === "modal" && onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
            >
              Close
            </button>
          )}
          <button
            type="button"
            onClick={save}
            disabled={saving || !content.trim()}
            className="rounded-full bg-accent px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-hover disabled:opacity-50"
          >
            {saving ? "Logging…" : "Log"}
          </button>
        </div>
      </div>
    </>
  );

  if (variant === "modal") {
    return (
      <div
        className="fixed inset-0 z-50 flex items-start justify-center bg-foreground/40 p-6 pt-20"
        onClick={(e) => {
          if (e.target === e.currentTarget && onClose) onClose();
        }}
      >
        <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
          {header}
          <h3 className="mt-1.5 text-xl font-bold tracking-tight">
            What happened today?
          </h3>
          <div className="mt-3">{body}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
      {header}
      {body}
    </div>
  );
}
