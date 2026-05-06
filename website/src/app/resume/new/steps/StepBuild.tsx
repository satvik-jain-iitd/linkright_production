"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { friendlyError } from "@/lib/friendly-error";
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
  onNeedCareer?: () => void;
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

function extractBullets(htmlStr: string): string[] {
  if (typeof window === "undefined") return [];
  try {
    const doc = new DOMParser().parseFromString(htmlStr, "text/html");
    return Array.from(doc.querySelectorAll("li"))
      .map((li) => li.textContent?.trim() || "")
      .filter((b) => b.length > 8);
  } catch {
    return [];
  }
}

function BulletItem({ text }: { text: string }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 40);
    return () => clearTimeout(t);
  }, []);
  return (
    <div
      className={`flex gap-2 text-sm text-foreground transition-all duration-300 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
      }`}
    >
      <span className="mt-0.5 shrink-0 text-accent">•</span>
      <span>{text}</span>
    </div>
  );
}

export function StepBuild({ data, update, next, onReset, onRetry, onSubSteps, onNeedCareer }: Props) {
  const [phase, setPhase] = useState("queued");
  const [progress, setProgress] = useState(0);
  const [draftHtml, setDraftHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [streamedBullets, setStreamedBullets] = useState<string[]>([]);
  const seenBullets = useRef<Set<string>>(new Set());
  // Pipeline review gates (8 phase-boundary checkpoints, 3 editable, 5 read-only).
  const [gate, setGate] = useState<{ name: string; artifacts: Record<string, unknown>; editable: boolean } | null>(null);
  const [gateNotes, setGateNotes] = useState("");
  const [gateContinuing, setGateContinuing] = useState(false);
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
              setError(friendlyError(job.error_message, "Generation failed"));
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
          setError("Could not check existing job. Please try again.");
          return;
        }
      }

      // Pre-check: career_text is required for resume generation
      if (!data.career_text || data.career_text.trim().length < 100) {
        if (onNeedCareer) {
          onNeedCareer();
        } else {
          setError("Career profile is missing. Go to My Career page to add your experience first.");
        }
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
            section_order: data.section_order || [],
            override_theme_colors: data.brand_colors || null,
            target_role: data.target_role || "", // [PSA5-ayd.1.1.2]
            target_company: data.target_company || "", // [PSA5-ayd.1.1.2]
          }),
        });
        const result = await resp.json();
        if (!resp.ok) {
          setError(friendlyError(result.error, "Failed to start job"));
          return;
        }
        update({ job_id: result.job_id });
        cleanupFn = subscribeToJob(result.job_id);
      } catch {
        setError("Network error. Please try again.");
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

            // Gate detection: worker pauses by setting status=awaiting_user_input.
            // Editable gates (3) get an optional notes textarea; read-only (5) just Continue.
            const EDITABLE_GATES = ["gate_contact", "gate_strategy_review", "gate_final_critique"];
            if (row.status === "awaiting_user_input" && row.current_gate) {
              const gateName = row.current_gate as string;
              setGate({
                name: gateName,
                artifacts: (row.gate_artifacts as Record<string, unknown>) || {},
                editable: EDITABLE_GATES.includes(gateName),
              });
            } else if (
              row.status === "processing" ||
              row.status === "completed" ||
              row.status === "failed"
            ) {
              // AR-fix: also clear on `failed` (timeout / cancel / worker crash)
              // so the gate overlay doesn't co-exist with the error banner.
              setGate(null);
              setGateNotes("");
            }

            if (row.status === "completed") {
              applyUpdate("done", 100, 999);
              teardown();
              setTimeout(next, 1000);
            } else if (row.status === "failed") {
              setError(friendlyError(row.error_message as string | null, "Generation failed"));
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

          // Gate detection (polling mirror of realtime branch above).
          const EDITABLE_GATES_POLL = ["gate_contact", "gate_strategy_review", "gate_final_critique"];
          if (job.status === "awaiting_user_input" && job.current_gate) {
            setGate({
              name: job.current_gate as string,
              artifacts: (job.gate_artifacts as Record<string, unknown>) || {},
              editable: EDITABLE_GATES_POLL.includes(job.current_gate as string),
            });
          } else if (
            job.status === "processing" ||
            job.status === "completed" ||
            job.status === "failed"
          ) {
            // AR-fix: also clear on `failed` (timeout / cancel / worker crash).
            setGate(null);
            setGateNotes("");
          }

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

  // Stream new bullets in with stagger when draftHtml updates
  useEffect(() => {
    if (!draftHtml) return;
    const bullets = extractBullets(draftHtml);
    const newOnes = bullets.filter((b) => !seenBullets.current.has(b));
    newOnes.forEach((bullet, i) => {
      seenBullets.current.add(bullet);
      setTimeout(() => {
        setStreamedBullets((prev) => [...prev, bullet]);
      }, i * 120);
    });
  }, [draftHtml]);

  const phaseLabel = PHASE_LABELS[phase] || phase;

  const isAlreadyGenerating = error?.toLowerCase().includes("already have a resume");

  const handleGateContinue = async () => {
    if (!data.job_id) return;
    setGateContinuing(true);
    try {
      const edits: Record<string, unknown> = {};
      if (gate?.editable && gateNotes.trim()) {
        edits.notes = gateNotes.trim();
      }
      const resp = await fetch("/api/resume/gate-continue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: data.job_id, edits }),
      });
      if (!resp.ok) {
        const result = await resp.json().catch(() => ({}));
        setError(friendlyError(result.error, "Failed to continue past checkpoint"));
        return;
      }
      // Optimistic: realtime/poll will catch up; clear local gate state now.
      setGate(null);
      setGateNotes("");
    } catch {
      setError("Network error continuing past checkpoint.");
    } finally {
      setGateContinuing(false);
    }
  };

  const handleCancelAndRetry = async () => {
    setCancelling(true);
    try {
      await fetch("/api/resume/cancel", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    } finally {
      setCancelling(false);
      started.current = false;
      setError(null);
      onRetry();
    }
  };

  if (error) {
    return (
      <div className="text-center">
        <div className="mx-auto max-w-md rounded-2xl border border-red-200 bg-red-50 p-10">
          <div className="text-4xl">&#x26A0;&#xFE0F;</div>
          <h2 className="mt-4 text-xl font-semibold text-red-700">Generation Failed</h2>
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <div className="mt-6 flex flex-col items-center gap-3">
            {isAlreadyGenerating && (
              <button
                onClick={handleCancelAndRetry}
                disabled={cancelling}
                className="w-full rounded-[10px] bg-red-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
              >
                {cancelling ? "Cancelling..." : "Cancel Existing & Start Fresh"}
              </button>
            )}
            <div className="flex justify-center gap-3">
              <button
                onClick={onReset}
                className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
              >
                Start Over
              </button>
              {!isAlreadyGenerating && (
                <button
                  onClick={onRetry}
                  className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
                >
                  Try Again
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Context banner: shown when coming from a matched role */}
      {(data.target_role || data.target_company) && (
        <div className="rounded-xl border border-accent/20 bg-accent/5 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-accent">Customizing for</p>
          <p className="mt-0.5 text-base font-bold text-foreground">
            {data.target_role}
            {data.target_role && data.target_company && " · "}
            {data.target_company}
          </p>
        </div>
      )}

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

      {/* Gate overlay: pause-and-review at phase boundaries */}
      {gate && (
        <div className="rounded-xl border border-accent/40 bg-accent/5 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-accent">
            {gate.editable ? "Review & continue" : "Checkpoint"}
          </p>
          <h3 className="mt-1 text-base font-bold text-foreground">
            {(gate.artifacts.label as string) || gate.name}
          </h3>
          {gate.artifacts.description ? (
            <p className="mt-1 text-sm text-muted">{gate.artifacts.description as string}</p>
          ) : null}
          <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-xs">
            {Object.entries(gate.artifacts)
              .filter(([k]) => !["label", "description"].includes(k))
              .slice(0, 8)
              .map(([k, v]) => {
                // AR-fix R2: render ALL value types, not just primitives.
                // Worker emits arrays (jd_keywords, companies, section_order)
                // and objects (bullet_budget) — those must surface, not drop.
                let display: string;
                if (v === null || v === undefined) {
                  display = "—";
                } else if (
                  typeof v === "string" ||
                  typeof v === "number" ||
                  typeof v === "boolean"
                ) {
                  display = String(v);
                } else if (Array.isArray(v)) {
                  if (v.length === 0) {
                    display = "—";
                  } else if (
                    v.every(
                      (item) =>
                        typeof item === "string" ||
                        typeof item === "number" ||
                        typeof item === "boolean"
                    )
                  ) {
                    display = v.join(", ");
                  } else {
                    display = `${v.length} item${v.length === 1 ? "" : "s"}`;
                  }
                } else if (typeof v === "object") {
                  const entries = Object.entries(v as Record<string, unknown>).slice(0, 5);
                  display =
                    entries.length === 0
                      ? "—"
                      : entries
                          .map(
                            ([ek, ev]) =>
                              `${ek}: ${typeof ev === "object" && ev !== null ? "…" : String(ev)}`
                          )
                          .join(", ");
                } else {
                  display = String(v);
                }
                if (display.length > 200) display = display.slice(0, 197) + "…";
                return (
                  <div key={k} className="contents">
                    <dt className="font-medium text-muted">{k}</dt>
                    <dd className="text-foreground">{display}</dd>
                  </div>
                );
              })}
          </dl>
          {gate.editable && (
            <div className="mt-4">
              <label className="block text-xs font-medium text-muted" htmlFor="gate-notes">
                Notes / suggestions (optional)
              </label>
              <textarea
                id="gate-notes"
                value={gateNotes}
                onChange={(e) => setGateNotes(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground"
                placeholder="Anything you want to flag for this stage..."
              />
            </div>
          )}
          <div className="mt-4 flex justify-end">
            <button
              onClick={handleGateContinue}
              disabled={gateContinuing}
              className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:opacity-50"
            >
              {gateContinuing ? "Continuing..." : "Continue"}
            </button>
          </div>
        </div>
      )}

      {/* Preview: streaming bullets during build, full iframe when done */}
      {phase === "done" && draftHtml ? (
        <iframe
          srcDoc={draftHtml}
          className="h-[700px] w-full rounded-lg border border-border bg-white shadow-sm"
          title="Resume Preview"
        />
      ) : streamedBullets.length > 0 ? (
        <div className="h-[700px] overflow-y-auto rounded-lg border border-border bg-surface p-6">
          <p className="mb-4 text-xs font-semibold uppercase tracking-wide text-muted">
            Writing bullets live...
          </p>
          <div className="space-y-2.5">
            {streamedBullets.map((bullet, i) => (
              <BulletItem key={i} text={bullet} />
            ))}
          </div>
        </div>
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
