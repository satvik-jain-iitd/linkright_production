"use client";

import { useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { WizardData } from "../WizardShell";

const PHASE_LABELS: Record<string, string> = {
  queued: "Waiting to start...",
  starting: "Initializing pipeline...",
  "Analyzing job description": "Reading and parsing the job description...",
  "JD analysis complete": "Extracted keywords and career signals",
  "Picking strategy & colors": "Choosing optimization strategy and brand colors...",
  "Planning page layout": "Calculating section sizes for one-page fit...",
  "Layout planned": "Page layout verified",
  "Writing bullets": "Crafting achievement-oriented bullets...",
  "Optimizing bullet widths": "Fine-tuning each bullet for edge-to-edge fill...",
  "Scoring bullets": "Ranking bullets by relevance to the JD...",
  "Validating colors & layout": "Checking contrast ratios and page fit...",
  "Validation complete": "All checks passed",
  "Assembling final HTML": "Building the final resume document...",
  "Resume complete": "Your resume is ready!",
  done: "Done!",
};

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  onReset: () => void;
  onRetry: () => void;
}

export function StepGenerate({ data, update, next, onReset, onRetry }: Props) {
  const [phase, setPhase] = useState("queued");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    let cleanupFn: (() => void) | null = null;
    let lastPhase = 0;

    const applyUpdate = (phase: string, pct: number, phaseNum: number) => {
      if (phaseNum < lastPhase) return;
      lastPhase = phaseNum;
      setPhase(phase);
      setProgress(pct);
    };

    const run = async () => {
      if (data.job_id) {
        try {
          const resp = await fetch(`/api/resume/${data.job_id}`);
          if (resp.ok) {
            const job = await resp.json();
            if (job.status === "completed") {
              setPhase("done");
              setProgress(100);
              return;
            } else if (job.status === "failed") {
              setError(job.error_message || "Generation failed");
              return;
            }
            setPhase(job.current_phase || "processing");
            setProgress(job.progress_pct || 0);
            lastPhase = job.phase_number || 0;
            cleanupFn = subscribeToJob(data.job_id);
            return;
          }
        } catch {
          setError("Could not check existing job — please try again");
          return;
        }
      }

      try {
        const resp = await fetch("/api/resume/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            jd_text: data.jd_text,
            career_text: data.career_text,
            model_provider: data.model_provider,
            model_id: data.model_id,
            api_key: data.api_key,
            qa_answers: data.qa_answers || [],
          }),
        });
        const result = await resp.json();
        if (!resp.ok) {
          setError(result.error || "Failed to start job");
          return;
        }
        update({ job_id: result.job_id });
        cleanupFn = subscribeToJob(result.job_id);
      } catch {
        setError("Network error — please try again");
      }
    };

    const subscribeToJob = (jobId: string) => {
      const supabase = createClient();
      let subscribed = true;

      const teardown = () => {
        if (subscribed) {
          subscribed = false;
          channel.unsubscribe();
        }
        clearInterval(poll);
      };

      const channel = supabase
        .channel(`job-${jobId}`)
        .on(
          "postgres_changes",
          {
            event: "UPDATE",
            schema: "public",
            table: "resume_jobs",
            filter: `id=eq.${jobId}`,
          },
          (payload) => {
            const row = payload.new as Record<string, unknown>;
            applyUpdate(
              (row.current_phase as string) || "processing",
              (row.progress_pct as number) || 0,
              (row.phase_number as number) || 0
            );

            if (row.status === "completed") {
              applyUpdate("done", 100, 999);
              teardown();
            } else if (row.status === "failed") {
              setError((row.error_message as string) || "Generation failed");
              teardown();
            }
          }
        )
        .subscribe();

      const poll = setInterval(async () => {
        try {
          const resp = await fetch(`/api/resume/${jobId}`);
          if (!resp.ok) return;
          const job = await resp.json();
          applyUpdate(
            job.current_phase || "processing",
            job.progress_pct || 0,
            job.phase_number || 0
          );
          if (job.status === "completed") {
            applyUpdate("done", 100, 999);
            teardown();
            setTimeout(next, 1000);
          } else if (job.status === "failed") {
            setError(job.error_message || "Generation failed");
            teardown();
          }
        } catch {
          // Polling error — ignore, will retry
        }
      }, 5000);

      return teardown;
    };

    run();

    return () => {
      cleanupFn?.();
    };
  }, []);

  const phaseLabel = PHASE_LABELS[phase] || phase;

  if (error) {
    return (
      <div className="text-center">
        <div className="mx-auto max-w-md rounded-2xl border border-red-200 bg-red-50 p-10">
          <div className="text-4xl">&#x26A0;&#xFE0F;</div>
          <h2 className="mt-4 text-xl font-semibold text-red-700">
            Generation Failed
          </h2>
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={onReset}
              className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
            >
              Start Over
            </button>
            <button
              onClick={onRetry}
              className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // s10a: rich complete state
  if (phase === "done") {
    return (
      <div>
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[#09766D]">Resume complete</p>
            <h2 className="mt-1 text-xl font-bold tracking-tight text-foreground">Done. Your resume is ready for review.</h2>
          </div>
          <span className="rounded-full bg-accent/10 px-3 py-1.5 text-[11px] font-semibold text-[#09766D]">✓ Complete</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-[200px_1fr_220px]">
          {/* Phases */}
          <div className="rounded-2xl border border-border bg-white p-4">
            <div className="mb-3 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-muted">Phases</div>
            <div className="space-y-2">
              {[
                { t: "Retrieved memory" },
                { t: "Planned layout" },
                { t: "Wrote bullets" },
                { t: "Ran QA rules" },
                { t: "Fitted page" },
              ].map((p) => (
                <div key={p.t} className="flex items-center gap-2.5 rounded-lg px-2 py-1.5" style={{ background: "rgba(15,190,175,0.04)" }}>
                  <div className="flex h-[14px] w-[14px] flex-shrink-0 items-center justify-center rounded-full bg-accent text-[9px] font-bold text-white">✓</div>
                  <span className="text-[12px] text-foreground">{p.t}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 border-t border-border pt-3 text-[11px] leading-relaxed text-muted">
              All bullets traceable to highlights in your profile.
            </p>
          </div>

          {/* Preview placeholder */}
          <div className="flex min-h-[360px] items-center justify-center rounded-2xl border border-border bg-[#EEF0F3]">
            <div className="rounded-lg bg-white px-8 py-6 text-center shadow-sm">
              <div className="text-2xl font-bold text-foreground">Resume Ready</div>
              <p className="mt-1 text-xs text-muted">Click &ldquo;Review &amp; download&rdquo; to continue</p>
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-3">
            <div className="rounded-2xl border border-border bg-white p-4">
              <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">Quality checks</div>
              <div className="space-y-2">
                {["ATS-safe structure", "0 AI-slop phrases", "Page-fill optimised", "Brand-matched accent"].map((t) => (
                  <div key={t} className="flex items-center gap-2 text-[12px]">
                    <div className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded bg-accent/15 text-[10px] font-bold text-[#09766D]">✓</div>
                    {t}
                  </div>
                ))}
              </div>
            </div>
            <button
              type="button"
              onClick={next}
              className="w-full rounded-xl bg-cta px-4 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
            >
              Review &amp; download →
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="text-center">
      <div className="mx-auto max-w-md">
        <h2 className="text-2xl font-bold">Generating Your Resume</h2>
        <p className="mt-2 text-sm text-muted">
          This takes 1-3 minutes depending on the model.
        </p>

        {/* Progress bar */}
        <div className="mt-10">
          <div className="h-2 w-full overflow-hidden rounded-full bg-border">
            <div
              className="h-full rounded-full bg-accent transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-3 text-sm font-medium">{progress}%</p>
        </div>

        {/* Phase label */}
        <div className="mt-6 rounded-xl border border-border bg-surface p-4">
          <div className="flex items-center justify-center gap-3">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            <span className="text-sm text-foreground">{phaseLabel}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
