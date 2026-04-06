"use client";

import { useEffect, useRef, useState } from "react";
import type { WizardData } from "../WizardShell";

interface GapQuestion {
  req_id: string;
  question: string;
}

interface AnswerStatus {
  status: "idle" | "saving" | "added" | "duplicate" | "error";
  message?: string;
}

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

export function StepEnrich({ data, update, next, back }: Props) {
  const hasGaps = (data.jd_analysis?.gaps?.length ?? 0) > 0;

  // ── Gap-filling mode (when JD analysis found gaps) ──────────────────────
  const [gapQuestions, setGapQuestions] = useState<GapQuestion[]>([]);
  const [gapAnswers, setGapAnswers] = useState<Record<string, string>>({});
  const [answerStatuses, setAnswerStatuses] = useState<Record<string, AnswerStatus>>({});
  const [loadingGapQuestions, setLoadingGapQuestions] = useState(hasGaps);
  const [gapQuestionsError, setGapQuestionsError] = useState<string | null>(null);
  const [toastMessages, setToastMessages] = useState<string[]>([]);

  // ── Standard enrich mode (always available) ──────────────────────────────
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(!hasGaps);
  const [error, setError] = useState<string | null>(null);
  const [autoFilled, setAutoFilled] = useState<Set<number>>(new Set());
  const [searching, setSearching] = useState<Set<number>>(new Set());

  const started = useRef(false);
  const gapStarted = useRef(false);

  // ── Gap questions fetch ─────────────────────────────────────────────────
  useEffect(() => {
    if (!hasGaps || gapStarted.current) return;
    gapStarted.current = true;

    const gaps = data.jd_analysis!.gaps;
    fetch("/api/enrich/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gaps,
        model_provider: data.model_provider,
        model_id: data.model_id,
        api_key: data.api_key,
      }),
    })
      .then((r) => r.json())
      .then((result) => {
        if (result.questions) setGapQuestions(result.questions);
        else setGapQuestionsError("Could not generate gap questions");
      })
      .catch(() => setGapQuestionsError("Network error generating gap questions"))
      .finally(() => setLoadingGapQuestions(false));
  }, [hasGaps]);

  // ── Standard Q&A fetch ──────────────────────────────────────────────────
  useEffect(() => {
    if (started.current) return;
    started.current = true;

    if (data.qa_answers && data.qa_answers.length > 0) {
      const qs = data.qa_answers.map((qa) => qa.question);
      const ans: Record<number, string> = {};
      data.qa_answers.forEach((qa, i) => { ans[i] = qa.answer; });
      setQuestions(qs);
      setAnswers(ans);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    const generate = async () => {
      try {
        const resp = await fetch("/api/resume/questions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            jd_text: data.jd_text,
            career_text: data.career_text,
            model_provider: data.model_provider,
            model_id: data.model_id,
            api_key: data.api_key,
          }),
          signal: controller.signal,
        });
        const result = await resp.json();
        if (!resp.ok) {
          setError(result.error || "Failed to generate questions");
          return;
        }
        const qs = result.questions || [];
        setQuestions(qs);
        if (qs.length > 0) autoFillFromProfile(qs);
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") {
          setError("Question generation timed out — you can skip this step");
        } else {
          setError("Network error — please try again");
        }
      } finally {
        clearTimeout(timeout);
        setLoading(false);
      }
    };

    generate();
  }, []);

  const autoFillFromProfile = async (qs: string[]) => {
    setSearching(new Set(qs.map((_, i) => i)));
    try {
      const results = await Promise.allSettled(
        qs.map((q) =>
          fetch("/api/career/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: q }),
          }).then((r) => r.json())
        )
      );
      const newAnswers: Record<number, string> = {};
      const filled = new Set<number>();
      results.forEach((r, i) => {
        if (r.status === "fulfilled" && r.value.chunks?.length > 0) {
          newAnswers[i] = r.value.chunks.join("\n\n");
          filled.add(i);
        }
      });
      setAnswers((prev) => ({ ...prev, ...newAnswers }));
      setAutoFilled(filled);
    } catch {
      // Best-effort
    } finally {
      setSearching(new Set());
    }
  };

  const showToast = (msg: string) => {
    setToastMessages((prev) => [...prev, msg]);
    setTimeout(() => {
      setToastMessages((prev) => prev.filter((m) => m !== msg));
    }, 4000);
  };

  const submitGapAnswer = async (reqId: string) => {
    const answer = gapAnswers[reqId]?.trim();
    if (!answer || answer.length < 10) return;

    setAnswerStatuses((prev) => ({ ...prev, [reqId]: { status: "saving" } }));
    try {
      const resp = await fetch("/api/enrich/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answer,
          model_provider: data.model_provider,
          model_id: data.model_id,
          api_key: data.api_key,
        }),
      });
      const result = await resp.json();
      if (!resp.ok) {
        setAnswerStatuses((prev) => ({
          ...prev,
          [reqId]: { status: "error", message: result.error || "Failed to save" },
        }));
        return;
      }
      setAnswerStatuses((prev) => ({
        ...prev,
        [reqId]: { status: result.status, message: result.message },
      }));
      if (result.status === "added") {
        showToast(`Career profile enriched: ${result.summary || "New experience added"}`);
      } else if (result.status === "duplicate") {
        showToast("Already in your profile — skipped.");
      }
    } catch {
      setAnswerStatuses((prev) => ({
        ...prev,
        [reqId]: { status: "error", message: "Network error" },
      }));
    }
  };

  const handleNext = () => {
    const qa_answers = questions
      .map((q, i) => ({
        question: q,
        answer: (answers[i] || "").trim(),
      }))
      .filter((qa) => qa.answer.length > 0);
    update({ qa_answers });
    next();
  };

  const handleSkip = () => {
    update({ qa_answers: [] });
    next();
  };

  const answeredCount = Object.values(answers).filter((a) => a.trim().length > 0).length;

  return (
    <div>
      {/* Toasts */}
      {toastMessages.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
          {toastMessages.map((msg, i) => (
            <div
              key={i}
              className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800 shadow-lg"
            >
              ✓ {msg}
            </div>
          ))}
        </div>
      )}

      <h2 className="text-2xl font-bold">Enrich Your Profile</h2>
      <p className="mt-2 text-sm text-muted">
        {hasGaps
          ? `Answer gap-filling questions to strengthen your match, then review auto-generated bullets.`
          : "Answer these questions to help the AI write stronger, more targeted bullets."}
      </p>

      {/* ── Gap-filling section ─────────────────────────────────────────── */}
      {hasGaps && (
        <div className="mt-8">
          <div className="mb-4 flex items-center gap-2">
            <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
              {data.jd_analysis!.gaps.length} gaps detected
            </span>
            <span className="text-sm text-muted">
              These requirements were not found in your career profile.
            </span>
          </div>

          {loadingGapQuestions ? (
            <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-5">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
              <span className="text-sm text-muted">Generating gap-filling questions...</span>
            </div>
          ) : gapQuestionsError ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
              {gapQuestionsError}
            </div>
          ) : (
            <div className="space-y-4">
              {gapQuestions.map((gq) => {
                const status = answerStatuses[gq.req_id];
                const gap = data.jd_analysis!.gaps.find((g) => g.req_id === gq.req_id);
                const isSaved = status?.status === "added" || status?.status === "duplicate";
                return (
                  <div
                    key={gq.req_id}
                    className={`rounded-xl border p-5 transition-colors ${
                      isSaved ? "border-green-200 bg-green-50" : "border-border bg-surface"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        {gap && (
                          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted">
                            <span className="rounded bg-red-100 px-1.5 py-0.5 text-red-600">GAP</span>
                            {gap.text}
                          </p>
                        )}
                        <label className="text-sm font-medium text-foreground">
                          {gq.question}
                        </label>
                      </div>
                      {isSaved && (
                        <span className="flex-shrink-0 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
                          {status?.status === "duplicate" ? "Already captured" : "Saved"}
                        </span>
                      )}
                    </div>
                    {!isSaved && (
                      <>
                        <textarea
                          value={gapAnswers[gq.req_id] || ""}
                          onChange={(e) =>
                            setGapAnswers((prev) => ({ ...prev, [gq.req_id]: e.target.value }))
                          }
                          placeholder="Describe a specific example with measurable outcomes..."
                          className="mt-3 w-full resize-none rounded-lg border border-border bg-background p-3 text-sm text-foreground placeholder-muted focus:border-accent/50 focus:outline-none"
                          rows={3}
                          disabled={status?.status === "saving"}
                        />
                        <div className="mt-2 flex items-center justify-between">
                          {status?.status === "error" && (
                            <p className="text-xs text-red-600">{status.message}</p>
                          )}
                          <div className="ml-auto">
                            <button
                              onClick={() => submitGapAnswer(gq.req_id)}
                              disabled={
                                status?.status === "saving" ||
                                !gapAnswers[gq.req_id]?.trim() ||
                                (gapAnswers[gq.req_id]?.trim().length ?? 0) < 10
                              }
                              className="rounded-lg bg-accent px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
                            >
                              {status?.status === "saving" ? "Saving..." : "Save to Profile"}
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Standard Q&A section ────────────────────────────────────────── */}
      <div className={hasGaps ? "mt-8 border-t border-border pt-8" : "mt-8"}>
        {hasGaps && (
          <h3 className="mb-4 text-lg font-semibold">Additional Profile Questions</h3>
        )}

        {loading ? (
          <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-5">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            <span className="text-sm text-muted">Generating profile questions...</span>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-5">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        ) : (
          <div className="space-y-6">
            {questions.map((q, i) => (
              <div key={i} className="rounded-xl border border-border bg-surface p-5">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-foreground">
                    {i + 1}. {q}
                  </label>
                  {searching.has(i) && (
                    <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
                  )}
                  {autoFilled.has(i) && !searching.has(i) && (
                    <span className="rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                      Auto-filled from profile
                    </span>
                  )}
                </div>
                <textarea
                  value={answers[i] || ""}
                  onChange={(e) => {
                    setAnswers((prev) => ({ ...prev, [i]: e.target.value }));
                    setAutoFilled((prev) => {
                      const next = new Set(prev);
                      next.delete(i);
                      return next;
                    });
                  }}
                  placeholder={searching.has(i) ? "Searching your profile..." : "Your answer (optional)..."}
                  className="mt-3 w-full resize-none rounded-lg border border-border bg-background p-3 text-sm text-foreground placeholder-muted transition-colors focus:border-accent/50 focus:outline-none"
                  rows={3}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-8 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={back}
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            &larr; Back
          </button>
          {!hasGaps && (
            <span className="text-xs text-muted">
              {answeredCount}/{questions.length} answered
            </span>
          )}
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleSkip}
            className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
          >
            Skip
          </button>
          <button
            onClick={handleNext}
            className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
          >
            Generate Resume
          </button>
        </div>
      </div>
    </div>
  );
}
