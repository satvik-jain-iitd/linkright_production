"use client";

import { useEffect, useRef, useState } from "react";
import type { WizardData } from "../WizardShell";

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

export function StepEnrich({ data, update, next, back }: Props) {
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  const [autoFilled, setAutoFilled] = useState<Set<number>>(new Set());
  const [searching, setSearching] = useState<Set<number>>(new Set());

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
      // Auto-fill is best-effort
    } finally {
      setSearching(new Set());
    }
  };

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    // If we already have Q&A answers (restored from session), show them
    if (data.qa_answers && data.qa_answers.length > 0) {
      const qs = data.qa_answers.map((qa) => qa.question);
      const ans: Record<number, string> = {};
      data.qa_answers.forEach((qa, i) => {
        ans[i] = qa.answer;
      });
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

  const answeredCount = Object.values(answers).filter(
    (a) => a.trim().length > 0
  ).length;

  if (loading) {
    return (
      <div className="text-center">
        <div className="mx-auto max-w-md">
          <h2 className="text-2xl font-bold">Analyzing Your Profile</h2>
          <p className="mt-2 text-sm text-muted">
            Reading your career profile and JD to generate targeted questions...
          </p>
          <div className="mt-10 flex justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center">
        <div className="mx-auto max-w-md rounded-2xl border border-red-200 bg-red-50 p-10">
          <h2 className="mt-4 text-xl font-semibold text-red-700">
            Could not generate questions
          </h2>
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={back}
              className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
            >
              Go Back
            </button>
            <button
              onClick={handleSkip}
              className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
            >
              Skip &amp; Generate
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold">Enrich Your Profile</h2>
      <p className="mt-2 text-sm text-muted">
        Answer these questions to help the AI write stronger, more targeted
        bullets. Skip any that don&apos;t apply.
      </p>

      <div className="mt-8 space-y-6">
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

      <div className="mt-8 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={back}
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            &larr; Back
          </button>
          <span className="text-xs text-muted">
            {answeredCount}/{questions.length} answered
          </span>
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
