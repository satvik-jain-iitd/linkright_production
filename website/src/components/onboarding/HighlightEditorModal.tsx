"use client";

// Editor for creating a new highlight OR editing an existing one.
// Create mode: 2-step — input → LLM structured preview → save.
// Edit mode: single form (company + role required).

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
  // Create mode: step 1 = input, step 2 = review
  const [step, setStep] = useState<1 | 2>(1);

  // Step 1 fields
  const [company, setCompany] = useState(existing?.company ?? "");
  const [role, setRole] = useState(existing?.role ?? "");
  const [rawText, setRawText] = useState("");

  // Step 2 / edit fields
  const [answer, setAnswer] = useState(existing?.answer ?? "");
  const [tags, setTags] = useState<string[]>(existing?.tags ?? []);
  const [importance, setImportance] = useState("P2");

  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !saving && !generating) onClose(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, saving, generating]);

  const generatePreview = async () => {
    if (!company.trim()) { setError("Company is required."); return; }
    if (!role.trim()) { setError("Role is required."); return; }
    if (rawText.trim().length < 10) { setError("Tell us what you did — at least a sentence."); return; }
    setError("");
    setGenerating(true);
    try {
      const res = await fetch("/api/onboarding/structure-highlight", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company: company.trim(), role: role.trim(), raw_text: rawText.trim() }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? "Preview generation failed. Try again.");
        return;
      }
      const data = await res.json();
      setAnswer(data.answer ?? rawText.trim());
      setTags(data.tags ?? []);
      setImportance(data.importance ?? "P2");
      setStep(2);
    } catch {
      setError("Network error — try again.");
    } finally {
      setGenerating(false);
    }
  };

  const save = async () => {
    const answerToSave = mode === "edit" ? answer : answer;
    if (mode === "create" && (!company.trim() || !role.trim())) {
      setError("Company and role are required.");
      return;
    }
    if (!answerToSave.trim() || answerToSave.trim().length < 5) {
      setError("Add at least a sentence.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const url = mode === "edit" && existing?.id
        ? `/api/nuggets/${existing.id}`
        : "/api/nuggets";
      const method = mode === "edit" ? "PATCH" : "POST";
      const payload = mode === "edit"
        ? {
            nugget_text: existing?.nugget_text ?? answerToSave.split(/[.!?]/)[0]?.trim(),
            answer: answerToSave,
            company: company.trim(),
            role: role.trim(),
          }
        : {
            title: answerToSave.split(/[.!?]/)[0]?.trim().slice(0, 120),
            body: answerToSave,
            company: company.trim(),
            role: role.trim(),
            tags,
            importance,
          };
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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

  const IMPORTANCE_LABELS: Record<string, string> = {
    P0: "Career-defining",
    P1: "Strong achievement",
    P2: "Supporting context",
    P3: "Background detail",
  };

  const isCreate = mode === "create";

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-foreground/40 p-6 pt-16"
      onClick={(e) => {
        if (e.target === e.currentTarget && !saving && !generating) onClose(false);
      }}
    >
      <div className="w-full max-w-xl rounded-[24px] bg-white p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-tertiary-700">
              Your profile
            </p>
            <h3 className="mt-1.5 text-lg font-bold tracking-tight">
              {mode === "edit" ? "Edit highlight" : isCreate && step === 2 ? "Review your highlight" : "Add a highlight"}
            </h3>
            {isCreate && step === 1 && (
              <p className="mt-1 text-xs text-muted">
                Tell us what you did — we&apos;ll shape it into a clean bullet.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => !saving && !generating && onClose(false)}
            aria-label="Close"
            className="text-muted transition hover:text-foreground"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Step 1 — Input (create mode only) */}
        {isCreate && step === 1 && (
          <div className="mt-4 space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-foreground">
                  Company <span className="text-cta">*</span>
                </label>
                <input
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="Amex"
                  className="mt-1 w-full rounded-[10px] border border-border bg-white px-3 py-2 text-sm focus:border-tertiary-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">
                  Role <span className="text-cta">*</span>
                </label>
                <input
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="Senior PM"
                  className="mt-1 w-full rounded-[10px] border border-border bg-white px-3 py-2 text-sm focus:border-tertiary-500 focus:outline-none"
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-foreground">
                What did you do? <span className="text-cta">*</span>
              </label>
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Problem, what you did, what changed. Numbers if you have them."
                rows={5}
                className="mt-1 w-full resize-none rounded-[10px] border border-border bg-white p-3 text-sm leading-relaxed focus:border-tertiary-500 focus:outline-none"
              />
            </div>
          </div>
        )}

        {/* Edit mode — single form */}
        {mode === "edit" && (
          <div className="mt-4 space-y-3">
            <div>
              <label className="text-xs font-semibold text-foreground">Answer / description</label>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={5}
                className="mt-1 w-full resize-none rounded-[10px] border border-border bg-white p-3 text-sm leading-relaxed focus:border-tertiary-500 focus:outline-none"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-foreground">
                  Company <span className="text-cta">*</span>
                </label>
                <input
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="Amex"
                  className="mt-1 w-full rounded-[10px] border border-border bg-white px-3 py-2 text-sm focus:border-tertiary-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">
                  Role <span className="text-cta">*</span>
                </label>
                <input
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="Senior PM"
                  className="mt-1 w-full rounded-[10px] border border-border bg-white px-3 py-2 text-sm focus:border-tertiary-500 focus:outline-none"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2 — Review (create mode only) */}
        {isCreate && step === 2 && (
          <div className="mt-4 space-y-3">
            <div>
              <label className="text-xs font-semibold text-foreground">Structured highlight</label>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={5}
                className="mt-1 w-full resize-none rounded-[10px] border border-border bg-white p-3 text-sm leading-relaxed focus:border-tertiary-500 focus:outline-none"
              />
              <p className="mt-1 text-[11px] text-muted">Edit anything that doesn&apos;t sound like you.</p>
            </div>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {tags.map((t) => (
                  <span
                    key={t}
                    className="rounded-full bg-tertiary-50 px-2.5 py-0.5 text-[11px] font-medium text-tertiary-700"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted">Importance:</span>
              <span className="rounded-full bg-gold-100 px-2.5 py-0.5 text-[11px] font-semibold text-gold-700">
                {IMPORTANCE_LABELS[importance] ?? importance}
              </span>
            </div>
          </div>
        )}

        {error && (
          <p className="mt-3 rounded-[10px] bg-red-50 p-2 text-xs text-red-700">{error}</p>
        )}

        {/* Footer */}
        <div className="mt-5 flex items-center justify-between">
          <span className="text-[11px] text-muted">
            {mode === "edit"
              ? "Updates the existing highlight + re-indexes it."
              : step === 1
              ? "We structure your raw notes into a clean achievement."
              : "Saved as a new highlight + indexed for matches."}
          </span>
          <div className="flex gap-2">
            {isCreate && step === 2 ? (
              <>
                <button
                  type="button"
                  onClick={() => { setStep(1); setError(""); }}
                  className="rounded-lg border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-tertiary-500"
                >
                  ← Edit back
                </button>
                <button
                  type="button"
                  onClick={save}
                  disabled={saving}
                  className="rounded-full bg-tertiary-500 px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-tertiary-600 disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Save highlight"}
                </button>
              </>
            ) : mode === "edit" ? (
              <>
                <button
                  type="button"
                  onClick={() => !saving && onClose(false)}
                  className="rounded-lg border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-tertiary-500"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={save}
                  disabled={saving}
                  className="rounded-full bg-tertiary-500 px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-tertiary-600 disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Save changes"}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => !generating && onClose(false)}
                  className="rounded-lg border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-tertiary-500"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={generatePreview}
                  disabled={generating}
                  className="inline-flex items-center gap-1.5 rounded-full bg-tertiary-500 px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-tertiary-600 disabled:opacity-50"
                >
                  {generating ? (
                    <>
                      <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Generating…
                    </>
                  ) : (
                    "Generate preview →"
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
