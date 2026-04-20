"use client";

// Shown when the user moves an application card to a status that deserves
// a 1-line "what happened" note (Interview, Offer, Rejected, Ghosted).
// These notes become high-signal nuggets tagged "outcome" so the memory
// layer learns what worked + what didn't.

import { useEffect, useState } from "react";

type Outcome = "interview" | "offer" | "rejected" | "ghosted";

const PROMPTS: Record<Outcome, { title: string; sub: string; ph: string }> = {
  interview: {
    title: "Interview scheduled. What do you know so far?",
    sub: "Who's on the panel, what they care about, what you want to emphasise.",
    ph: "Second round with Priya (VP) — she led a similar returns rebuild at PhonePe. Plan to lead with the Amex metric and ask about their India roadmap.",
  },
  offer: {
    title: "Offer landed. What tipped it?",
    sub: "What they responded to + what you'd repeat for the next one.",
    ph: "Final call went deep on the refund-SLA story; the 5-days→8-hours framing landed. Will reuse for Cred and Groww.",
  },
  rejected: {
    title: "Rejected. What happened?",
    sub: "The reason they gave, your gut read, what you'd change next time.",
    ph: "Recruiter said they wanted more fintech depth. Felt like a timing thing — comp was stretched and they paused mid-process.",
  },
  ghosted: {
    title: "Ghosted. Your read?",
    sub: "If you know why, log it. If you don't, guess — the memory still learns.",
    ph: "No response after the take-home. Maybe the take-home was too generic — will tailor harder next time.",
  },
};

interface Props {
  applicationId: string;
  company: string;
  role: string;
  outcome: Outcome;
  onClose: () => void;
}

export function OutcomeModal({
  applicationId,
  company,
  role,
  outcome,
  onClose,
}: Props) {
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const save = async () => {
    if (note.trim().length < 10) {
      setError("Share at least one sentence.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await fetch("/api/applications/outcome", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          application_id: applicationId,
          outcome,
          note: note.trim(),
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? "Save failed.");
        return;
      }
      onClose();
    } catch {
      setError("Network error — try again.");
    } finally {
      setSaving(false);
    }
  };

  const prompt = PROMPTS[outcome];

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-foreground/40 p-6 pt-20"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-accent">
              Capture the outcome
            </p>
            <h3 className="mt-1.5 text-lg font-bold tracking-tight">
              {prompt.title}
            </h3>
            <p className="mt-1 text-xs text-muted">
              {[role, company].filter(Boolean).join(" · ")} · {prompt.sub}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-muted transition hover:text-foreground"
            aria-label="Close"
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

        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={prompt.ph}
          rows={5}
          className="mt-4 w-full resize-none rounded-xl border border-border bg-white p-3 text-sm leading-relaxed focus:border-accent focus:outline-none"
        />

        {error && (
          <p className="mt-2 text-xs text-red-600">{error}</p>
        )}

        <div className="mt-4 flex items-center justify-between">
          <span className="text-[11px] text-muted">
            Saved as a career highlight · tagged &quot;outcome&quot;
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
            >
              Skip for now
            </button>
            <button
              type="button"
              onClick={save}
              disabled={saving || note.trim().length < 10}
              className="rounded-lg bg-accent px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-hover disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save outcome"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
