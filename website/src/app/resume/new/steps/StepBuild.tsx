"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import type { WizardData } from "../WizardShell";

interface SubStep {
  label: string;
  done: boolean;
}

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  onReset: () => void;
  onRetry: () => void;
  onSubSteps?: (subSteps: SubStep[]) => void;
}

const PHASE_LABELS: Record<string, string> = {
  queued: "Waiting to start...",
  starting: "Initializing pipeline...",
  "Analyzing job description": "Analyzing job description...",
  "Retrieving relevant experience": "Searching career profile...",
  "Building layout stencil": "Building layout stencil...",
  "Stencil ready": "Layout ready",
  "Ranking by relevance": "Ranking bullets by relevance...",
  "Condensing to bullet points": "Condensing to bullet points...",
  "Optimizing bullet widths": "Optimizing bullet widths...",
  "Scoring bullets": "Scoring bullets...",
  "Validating colors & layout": "Validating...",
  "Assembling final HTML": "Final assembly...",
  "Resume complete": "Your resume is ready!",
  done: "Done!",
};

export function StepBuild({ data, update, next, onReset, onRetry, onSubSteps }: Props) {
  const [phase, setPhase] = useState("queued");
  const [progress, setProgress] = useState(0);
  const [draftHtml, setDraftHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  const subStepsRef = useRef<SubStep[]>([]);

  const updateSubSteps = useCallback((phaseName: string) => {
    // Derive sub-step completion from phase name
    const phaseMap: Record<string, number> = {
      "Building layout stencil": 0,
      "Stencil ready": 0,
    };

    // Detect company writing phases: "Writing paragraphs — CompanyName"
    const companyMatch = phaseName.match(/^Writing paragraphs/);
    const isCondensing = phaseName.includes("Condensing");
    const isWidthOpt = phaseName.includes("Optimizing bullet");
    const isScoring = phaseName.includes("Scoring");
    const isDone = phaseName === "Resume complete" || phaseName === "done";

    const steps: SubStep[] = [
      { label: "Layout stencil", done: phaseName !== "queued" && phaseName !== "starting" && phaseName !== "Analyzing job description" && phaseName !== "Retrieving relevant experience" },
      { label: "Writing paragraphs", done: isCondensing || isWidthOpt || isScoring || isDone },
      { label: "Condensing bullets", done: isWidthOpt || isScoring || isDone },
      { label: "Width optimization", done: isScoring || isDone },
      { label: "Scoring & validation", done: isDone },
    ];

    // If currently writing paragraphs, mark as in-progress (not done yet)
    if (companyMatch) {
      steps[0].done = true;
    }

    subStepsRef.current = steps;
    onSubSteps?.(steps);
  }, [onSubSteps]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    let cleanupFn: (() => void) | null = null;
    let lastPhase = 0;

    const applyUpdate = (phaseName: string, pct: number, phaseNum: number, html?: string | null) => {
      if (phaseNum < lastPhase) return;
      lastPhase = phaseNum;
      setPhase(phaseName);
      setProgress(pct);
      updateSubSteps(phaseName);
      if (html) setDraftHtml(html);
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
              updateSubSteps("done");
              setTimeout(next, 500);
              return;
            } else if (job.status === "failed") {
              setError(job.error_message || "Generation failed");
              return;
            }
            applyUpdate(
              job.current_phase || "processing",
              job.progress_pct || 0,
              job.phase_number || 0,
              job.draft_html
            );
            cleanupFn = subscribeToJob(data.job_id);
            return;
          }
        } catch {
          setError("Could not check existing job — please try again");
          return;
        }
      }

      // Pre-check: career_text is required for resume generation
      if (!data.career_text || data.career_text.trim().length < 100) {
        setError("Career profile is missing or too short. Go to My Career page to add your experience first.");
        return;
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
            override_theme_colors: data.brand_colors || null,
            target_role: data.target_role || "", // [PSA5-ayd.1.1.2]
            target_company: data.target_company || "", // [PSA5-ayd.1.1.2]
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
              (row.phase_number as number) || 0,
              row.draft_html as string | null
            );

            if (row.status === "completed") {
              applyUpdate("done", 100, 999);
              teardown();
              setTimeout(next, 1000);
            } else if (row.status === "failed") {
              setError((row.error_message as string) || "Generation failed");
              teardown();
            }
          }
        )
        .subscribe();

      // Polling fallback: also fetch draft_html
      const poll = setInterval(async () => {
        try {
          const resp = await fetch(`/api/resume/${jobId}`);
          if (!resp.ok) return;
          const job = await resp.json();
          applyUpdate(
            job.current_phase || "processing",
            job.progress_pct || 0,
            job.phase_number || 0,
            job.draft_html
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
          // Polling error — ignore
        }
      }, 5000);

      return teardown;
    };

    run();
    return () => { cleanupFn?.(); };
  }, []);

  const phaseLabel = PHASE_LABELS[phase] || phase;

  if (error) {
    return (
      <div className="text-center">
        <div className="mx-auto max-w-md rounded-2xl border border-red-200 bg-red-50 p-10">
          <div className="text-4xl">&#x26A0;&#xFE0F;</div>
          <h2 className="mt-4 text-xl font-semibold text-red-700">Generation Failed</h2>
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
              className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Progress header */}
      <div className="flex items-center gap-3">
        {phase !== "done" && (
          <div className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
        )}
        <span className="text-sm font-medium text-foreground">{phaseLabel}</span>
        <span className="ml-auto text-xs text-muted">{progress}%</span>
      </div>

      {/* Thin progress bar */}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
        <div
          className="h-full rounded-full bg-accent transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Resume preview iframe */}
      {draftHtml ? (
        <iframe
          srcDoc={draftHtml}
          className="h-[700px] w-full rounded-lg border border-border bg-white shadow-sm"
          title="Resume Preview"
        />
      ) : (
        <div className="flex h-[700px] items-center justify-center rounded-lg border border-border bg-surface">
          <div className="text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            <p className="mt-3 text-sm text-muted">Preparing preview...</p>
          </div>
        </div>
      )}
    </div>
  );
}
