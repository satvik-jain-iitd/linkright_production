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
}

export function StepGenerate({ data, update, next }: Props) {
  const [phase, setPhase] = useState("queued");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const run = async () => {
      // If we already have a job_id (e.g. page refresh), resume watching it
      if (data.job_id) {
        try {
          const resp = await fetch(`/api/resume/${data.job_id}`);
          if (resp.ok) {
            const job = await resp.json();
            if (job.status === "completed") {
              setPhase("done");
              setProgress(100);
              setTimeout(next, 500);
              return;
            } else if (job.status === "failed") {
              setError(job.error_message || "Generation failed");
              return;
            }
            // Still processing — resume subscription
            setPhase(job.current_phase || "processing");
            setProgress(job.progress_pct || 0);
            subscribeToJob(data.job_id);
            return;
          }
        } catch {
          // Fallback: start a new job
        }
      }

      // Start a new job
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
          }),
        });
        const result = await resp.json();
        if (!resp.ok) {
          setError(result.error || "Failed to start job");
          return;
        }
        update({ job_id: result.job_id });
        subscribeToJob(result.job_id);
      } catch {
        setError("Network error — please try again");
      }
    };

    const subscribeToJob = (jobId: string) => {
      const supabase = createClient();

      // Subscribe to realtime changes
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
            setPhase((row.current_phase as string) || "processing");
            setProgress((row.progress_pct as number) || 0);

            if (row.status === "completed") {
              setPhase("done");
              setProgress(100);
              channel.unsubscribe();
              setTimeout(next, 1000);
            } else if (row.status === "failed") {
              setError((row.error_message as string) || "Generation failed");
              channel.unsubscribe();
            }
          }
        )
        .subscribe();

      // Polling fallback — in case Realtime misses updates
      const poll = setInterval(async () => {
        try {
          const resp = await fetch(`/api/resume/${jobId}`);
          if (!resp.ok) return;
          const job = await resp.json();
          setPhase(job.current_phase || "processing");
          setProgress(job.progress_pct || 0);
          if (job.status === "completed") {
            setPhase("done");
            setProgress(100);
            clearInterval(poll);
            channel.unsubscribe();
            setTimeout(next, 1000);
          } else if (job.status === "failed") {
            setError(job.error_message || "Generation failed");
            clearInterval(poll);
            channel.unsubscribe();
          }
        } catch {
          // Polling error — ignore, will retry
        }
      }, 5000);

      return () => {
        channel.unsubscribe();
        clearInterval(poll);
      };
    };

    run();
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
          <button
            onClick={() => window.location.reload()}
            className="mt-6 rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
          >
            Try Again
          </button>
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
            {phase !== "done" && (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            )}
            <span className="text-sm text-foreground">{phaseLabel}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
