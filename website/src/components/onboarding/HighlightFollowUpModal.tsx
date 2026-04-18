"use client";

// Wave 2 / Screen 06 — Highlight follow-up modal.
// Opens from Screen 05 when the user clicks a highlight card.
// Shows parent highlight + 3 LLM-generated follow-up questions.
// Per-question save creates a new career_nuggets row via add-from-answer.

import { useCallback, useEffect, useState } from "react";

type Nugget = {
  id: string;
  answer: string;
  nugget_text?: string | null;
  company?: string | null;
  role?: string | null;
  section_type?: string | null;
};

interface Props {
  nugget: Nugget;
  onClose: () => void;
}

type Qstate = {
  question: string;
  answer: string;
  saving: boolean;
  saved: boolean;
};

function sourceChip(n: Nugget): string {
  const sec = (n.section_type ?? "").toLowerCase();
  if (n.company) return `from your ${n.company} role`;
  if (sec.includes("education")) return "from your education";
  if (sec.includes("certif")) return "from your certifications";
  if (sec.includes("project")) return "from your projects";
  return "from your resume";
}

export function HighlightFollowUpModal({ nugget, onClose }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [questions, setQuestions] = useState<Qstate[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/nuggets/follow-ups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nugget_id: nugget.id }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? "Couldn't load follow-ups. Try again.");
        return;
      }
      const body = await res.json();
      const qs: string[] = Array.isArray(body.questions) ? body.questions.slice(0, 3) : [];
      setQuestions(
        qs.map((q) => ({ question: q, answer: "", saving: false, saved: false })),
      );
    } catch {
      setError("Network error. Try again.");
    } finally {
      setLoading(false);
    }
  }, [nugget.id]);

  useEffect(() => {
    load();
  }, [load]);

  // ESC to close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const save = async (idx: number) => {
    const q = questions[idx];
    if (!q || !q.answer.trim() || q.saving || q.saved) return;
    setQuestions((prev) =>
      prev.map((x, i) => (i === idx ? { ...x, saving: true } : x)),
    );
    try {
      const res = await fetch("/api/nuggets/add-from-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parent_nugget_id: nugget.id,
          question: q.question,
          answer: q.answer.trim(),
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? "Save failed. Try again.");
        setQuestions((prev) =>
          prev.map((x, i) => (i === idx ? { ...x, saving: false } : x)),
        );
        return;
      }
      setQuestions((prev) =>
        prev.map((x, i) =>
          i === idx ? { ...x, saving: false, saved: true } : x,
        ),
      );
    } catch {
      setError("Network error. Try again.");
      setQuestions((prev) =>
        prev.map((x, i) => (i === idx ? { ...x, saving: false } : x)),
      );
    }
  };

  const savedCount = questions.filter((q) => q.saved).length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/40 p-6 pt-16"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
          <div>
            <span className="rounded-full bg-primary-500/10 px-2.5 py-0.5 text-[11px] font-medium text-primary-700">
              {sourceChip(nugget)}
            </span>
            <h3 className="mt-2 text-base font-semibold leading-snug tracking-tight">
              {nugget.nugget_text || nugget.answer}
            </h3>
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
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="bg-[#FAFBFC] px-6 py-5">
          <p className="mb-4 text-xs text-muted">
            Three quick questions — answer any, all, or none. Each one makes your profile
            sharper.
          </p>

          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-24 animate-pulse rounded-lg border border-border bg-white" />
              ))}
            </div>
          )}

          {!loading && error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
              {error}
              <button
                onClick={load}
                className="ml-2 font-semibold underline"
                type="button"
              >
                Retry
              </button>
            </div>
          )}

          {!loading &&
            questions.map((q, idx) => (
              <div key={idx} className="relative mb-4 pl-6 last:mb-0">
                {idx < questions.length - 1 && (
                  <span className="absolute left-[7px] top-4 bottom-[-16px] w-px bg-border" />
                )}
                <span
                  className={`absolute left-0 top-2 flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold text-white ${q.saved ? "bg-accent" : "border border-border bg-white"}`}
                >
                  {q.saved ? "✓" : ""}
                </span>
                <div
                  className={`rounded-xl border p-4 ${q.saved ? "border-border bg-white" : "border-accent bg-white shadow-[0_0_0_3px_rgba(15,190,175,0.08)]"}`}
                >
                  <div className="text-sm font-semibold leading-snug">{q.question}</div>
                  {q.saved ? (
                    <p className="mt-2 rounded-lg bg-primary-500/8 p-2.5 text-xs leading-relaxed text-foreground">
                      {q.answer}
                    </p>
                  ) : (
                    <div className="mt-3">
                      <textarea
                        value={q.answer}
                        onChange={(e) =>
                          setQuestions((prev) =>
                            prev.map((x, i) =>
                              i === idx ? { ...x, answer: e.target.value } : x,
                            ),
                          )
                        }
                        rows={2}
                        placeholder="A few sentences is plenty…"
                        className="w-full resize-none rounded-lg border border-border bg-white p-2.5 text-xs text-foreground focus:border-accent focus:outline-none"
                      />
                      <div className="mt-2 flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            setQuestions((prev) =>
                              prev.map((x, i) =>
                                i === idx ? { ...x, answer: "", saved: true } : x,
                              ),
                            )
                          }
                          className="rounded-full border border-border px-3 py-1 text-[11px] font-semibold text-muted transition hover:border-accent hover:text-accent"
                        >
                          Skip
                        </button>
                        <button
                          type="button"
                          onClick={() => save(idx)}
                          disabled={q.saving || !q.answer.trim()}
                          className="rounded-full bg-accent px-3 py-1 text-[11px] font-semibold text-white shadow-sm transition hover:bg-accent-hover disabled:opacity-50"
                        >
                          {q.saving ? "Saving…" : "Save"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border bg-white px-6 py-3.5">
          <span className="text-xs text-muted">
            {savedCount} of {questions.length || 3} answered · profile gets sharper
          </span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
