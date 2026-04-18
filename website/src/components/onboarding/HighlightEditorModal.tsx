"use client";

// Editor for creating a new highlight OR editing an existing one. Shared
// modal used by ProfileHighlightsView. When `existing` is null → POST
// /api/nuggets (create). When provided → PATCH /api/nuggets/[id].

import { useEffect, useState } from "react";

export type EditableNugget = {
  id?: string;
  nugget_text?: string | null;
  answer: string;
  company?: string | null;
  role?: string | null;
  tags?: string[] | null;
};

interface Props {
  existing: EditableNugget | null;
  mode: "create" | "edit";
  onClose: (saved: boolean) => void;
}

export function HighlightEditorModal({ existing, mode, onClose }: Props) {
  const [title, setTitle] = useState(existing?.nugget_text ?? "");
  const [bodyText, setBodyText] = useState(existing?.answer ?? "");
  const [company, setCompany] = useState(existing?.company ?? "");
  const [role, setRole] = useState(existing?.role ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !saving) onClose(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, saving]);

  const save = async () => {
    if (!title.trim() && bodyText.trim().length < 10) {
      setError("Needs a title or a sentence — give us something to work with.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const url =
        mode === "edit" && existing?.id
          ? `/api/nuggets/${existing.id}`
          : "/api/nuggets";
      const method = mode === "edit" ? "PATCH" : "POST";
      const payloadCreate = {
        title: title.trim(),
        body: bodyText.trim(),
        company: company.trim(),
        role: role.trim(),
      };
      const payloadEdit = {
        nugget_text: title.trim(),
        answer: bodyText.trim() || title.trim(),
        company: company.trim(),
        role: role.trim(),
      };
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mode === "edit" ? payloadEdit : payloadCreate),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? "Save failed.");
        return;
      }
      onClose(true);
    } catch {
      setError("Network error — try again.");
    } finally {
      setSaving(false);
    }
  };

  const heading =
    mode === "create"
      ? "Add a highlight"
      : "Edit highlight";

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-foreground/40 p-6 pt-16"
      onClick={(e) => {
        if (e.target === e.currentTarget && !saving) onClose(false);
      }}
    >
      <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-accent">
              Your profile
            </p>
            <h3 className="mt-1.5 text-lg font-bold tracking-tight">
              {heading}
            </h3>
            <p className="mt-1 text-xs text-muted">
              Anything we learn here sharpens matches, resumes, posts.
            </p>
          </div>
          <button
            type="button"
            onClick={() => !saving && onClose(false)}
            aria-label="Close"
            className="text-muted transition hover:text-foreground"
          >
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="mt-4 space-y-3">
          <div>
            <label className="text-xs font-semibold text-foreground">
              One-line title
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Led 12-person redesign of returns flow"
              maxLength={120}
              className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-foreground">
              What happened? (specifics + numbers help)
            </label>
            <textarea
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
              placeholder="Problem, what you did, what changed. 2-4 sentences."
              rows={5}
              className="mt-1 w-full resize-none rounded-lg border border-border bg-white p-3 text-sm leading-relaxed focus:border-accent focus:outline-none"
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs font-semibold text-foreground">
                Company (optional)
              </label>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Amex"
                className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-foreground">
                Role (optional)
              </label>
              <input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="Senior PM"
                className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent focus:outline-none"
              />
            </div>
          </div>
        </div>

        {error && (
          <p className="mt-3 rounded-lg bg-red-50 p-2 text-xs text-red-700">
            {error}
          </p>
        )}

        <div className="mt-5 flex items-center justify-between">
          <span className="text-[11px] text-muted">
            {mode === "edit"
              ? "Saving updates the existing highlight + re-indexes it."
              : "Saved as a new highlight + indexed for matches."}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => !saving && onClose(false)}
              className="rounded-full border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={save}
              disabled={saving}
              className="rounded-full bg-accent px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-hover disabled:opacity-50"
            >
              {saving
                ? "Saving…"
                : mode === "edit"
                  ? "Save changes"
                  : "Add highlight"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
