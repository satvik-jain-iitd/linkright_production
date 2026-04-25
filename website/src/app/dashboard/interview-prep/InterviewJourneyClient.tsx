"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

// ─── Types ─────────────────────────────────────────────────────────────────

interface JourneyStage {
  stage_id: string;
  name: string;
  description: string;
  typical_duration_mins: number;
  drill_types: string[];
  is_optional: boolean;
}

interface JourneyTemplate {
  role_bucket: string;
  display_name: string;
  stages: JourneyStage[];
}

interface Application {
  id: string;
  role: string;
  company: string;
  journey_bucket: string | null;
  journey_stage_index: number;
}

// ─── Drill definitions ─────────────────────────────────────────────────────

const DRILLS: Record<
  string,
  { title: string; blurb: string; href: string; available: boolean }
> = {
  coach: {
    title: "Interview Coach",
    blurb: "Real-time voice mock interview with our AI recruiter.",
    href: "/dashboard/interview-prep/coach",
    available: true,
  },
  telephonic: {
    title: "Telephonic Screen",
    blurb: "The 20-minute recruiter call, practiced and tightened.",
    href: "/dashboard/interview-prep/coach",
    available: true,
  },
  behavioural: {
    title: "Behavioural",
    blurb: "Your stories, sharpened. Pulled from your diary + resume.",
    href: "#",
    available: false,
  },
  leadership: {
    title: "Leadership Questions",
    blurb: "Ownership, influence, difficult decisions — practiced.",
    href: "#",
    available: false,
  },
  past_experience: {
    title: "Past Experience Deep-dive",
    blurb: "Walk through your biggest roles with structured probing.",
    href: "#",
    available: false,
  },
  product_sense: {
    title: "Product Sense",
    blurb: "Frame, prioritise, design. Tailored to your target roles.",
    href: "#",
    available: false,
  },
  case: {
    title: "Case Study",
    blurb: "Consulting-style market size and profitability cases.",
    href: "#",
    available: false,
  },
  technical: {
    title: "Technical / Coding",
    blurb: "Mid-level DSA + API design at your current level.",
    href: "#",
    available: false,
  },
  system_design: {
    title: "System Design",
    blurb: "Whiteboard walkthroughs with real-time critique.",
    href: "#",
    available: false,
  },
  sql: {
    title: "SQL",
    blurb: "Window functions, joins, query optimisation.",
    href: "#",
    available: false,
  },
  growth: {
    title: "Growth & Metrics",
    blurb: "Funnel diagnosis, experiment design, activation.",
    href: "#",
    available: false,
  },
};

// ─── Bucket selector (when no application) ────────────────────────────────

const BUCKETS = [
  { bucket: "product_manager", label: "Product Manager" },
  { bucket: "software_engineer", label: "Software Engineer" },
  { bucket: "data_scientist", label: "Data Scientist / ML" },
  { bucket: "ux_designer", label: "UX / Product Designer" },
  { bucket: "growth_marketing", label: "Growth / Marketing" },
  { bucket: "business_analyst", label: "Business Analyst" },
  { bucket: "engineering_manager", label: "Engineering Manager" },
  { bucket: "general", label: "Other / General" },
];

// ─── Main component ────────────────────────────────────────────────────────

export function InterviewJourneyClient({
  initialApp,
}: {
  initialApp: Application | null;
}) {
  const [journey, setJourney] = useState<JourneyTemplate | null>(null);
  const [stageIndex, setStageIndex] = useState(
    initialApp?.journey_stage_index ?? 0
  );
  const [loading, setLoading] = useState(!!initialApp);
  const [advancing, setAdvancing] = useState(false);
  const [manualBucket, setManualBucket] = useState<string | null>(null);
  const stepperRef = useRef<HTMLDivElement>(null);

  // ── Classify against application ──────────────────────────────────────
  useEffect(() => {
    if (!initialApp) return;
    fetch("/api/interview-prep/classify-journey", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ application_id: initialApp.id }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.journey_template) {
          setJourney(data.journey_template);
          setStageIndex(data.current_stage_index ?? 0);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [initialApp?.id]);

  // ── Load template for manual bucket selection ─────────────────────────
  useEffect(() => {
    if (!manualBucket) return;
    setLoading(true);
    fetch("/api/interview-prep/journey-template?bucket=" + manualBucket)
      .then((r) => r.json())
      .then((data) => {
        if (data.journey_template) {
          setJourney(data.journey_template);
          setStageIndex(0);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [manualBucket]);

  // ── Scroll active stage into view ─────────────────────────────────────
  useEffect(() => {
    const el = stepperRef.current?.querySelector(`[data-stage="${stageIndex}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [stageIndex, journey]);

  const advanceStage = async () => {
    if (!journey || stageIndex >= journey.stages.length - 1) return;
    setAdvancing(true);
    if (initialApp) {
      await fetch("/api/interview-prep/classify-journey", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ application_id: initialApp.id }),
      }).catch(() => {});
    }
    setStageIndex((i) => i + 1);
    setAdvancing(false);
  };

  // ── No application + no manual selection → bucket picker ──────────────
  if (!initialApp && !journey) {
    return (
      <main className="mx-auto max-w-[1100px] px-6 py-10">
        <div className="mb-7 max-w-2xl">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-[#4A5D32]">
            Interview prep
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Choose your interview journey
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            No active application found. Pick your role to see your full interview
            roadmap — every stage, in order.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {BUCKETS.map((b) => (
            <button
              key={b.bucket}
              onClick={() => setManualBucket(b.bucket)}
              className="rounded-xl border border-[rgba(107,131,70,0.25)] bg-[#F3F6EA] px-5 py-4 text-left transition hover:border-[#6B8346] hover:bg-[#e8eddb]"
            >
              <span className="text-sm font-semibold text-[#2E3B1E]">{b.label}</span>
            </button>
          ))}
        </div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="mx-auto max-w-[1100px] px-6 py-10">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-border" />
        <div className="mt-6 h-16 animate-pulse rounded-xl bg-border" />
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <div className="h-36 animate-pulse rounded-xl bg-border" />
          <div className="h-36 animate-pulse rounded-xl bg-border" />
        </div>
      </main>
    );
  }

  if (!journey) return null;

  const currentStage = journey.stages[stageIndex];
  const pastStages = journey.stages.slice(0, stageIndex);
  const futureStages = journey.stages.slice(stageIndex + 1);
  const isLastStage = stageIndex === journey.stages.length - 1;

  // Drills for current stage
  const currentDrills = (currentStage.drill_types ?? [])
    .map((key) => ({ key, ...DRILLS[key] }))
    .filter(Boolean);

  const durationLabel =
    currentStage.typical_duration_mins === 0
      ? "Async"
      : currentStage.typical_duration_mins >= 60
      ? `${currentStage.typical_duration_mins / 60}h`
      : `${currentStage.typical_duration_mins} min`;

  return (
    <main className="mx-auto max-w-[1100px] px-6 py-10">
      {/* Header */}
      <div className="mb-7 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-[#4A5D32]">
            Interview prep
          </p>
          <h1 className="mt-1.5 text-3xl font-bold tracking-tight">
            Your interview roadmap
          </h1>
          <p className="mt-1.5 text-sm text-muted">
            {initialApp
              ? `${initialApp.role} at ${initialApp.company} · `
              : ""}
            {journey.display_name} journey
          </p>
        </div>
        <span className="self-start rounded-full border border-[rgba(107,131,70,0.3)] bg-[#F3F6EA] px-3 py-1 text-xs font-semibold text-[#4A5D32] sm:self-auto">
          Stage {stageIndex + 1} of {journey.stages.length}
        </span>
      </div>

      {/* ── Horizontal stepper ── */}
      <div
        ref={stepperRef}
        className="mb-8 flex items-center gap-0 overflow-x-auto rounded-2xl border border-[rgba(107,131,70,0.2)] bg-[#F3F6EA] px-4 py-4 scrollbar-hide"
        style={{ scrollbarWidth: "none" }}
      >
        {journey.stages.map((stage, idx) => {
          const isDone = idx < stageIndex;
          const isCurrent = idx === stageIndex;
          const isFuture = idx > stageIndex;

          return (
            <div
              key={stage.stage_id}
              data-stage={idx}
              className="flex shrink-0 items-center"
            >
              {/* Connector line */}
              {idx > 0 && (
                <div
                  className="mx-1 h-px w-6 shrink-0"
                  style={{
                    background: isDone || isCurrent
                      ? "#6B8346"
                      : "rgba(107,131,70,0.25)",
                  }}
                />
              )}

              {/* Stage pill */}
              <button
                onClick={() => setStageIndex(idx)}
                title={stage.name}
                className="flex shrink-0 flex-col items-center gap-1"
              >
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-full text-[11px] font-bold transition-all"
                  style={
                    isDone
                      ? { background: "#6B8346", color: "#fff" }
                      : isCurrent
                      ? {
                          background: "#6B8346",
                          color: "#fff",
                          boxShadow: "0 0 0 3px rgba(107,131,70,0.25)",
                        }
                      : {
                          background: "rgba(107,131,70,0.15)",
                          color: "#4A5D32",
                          border: "1.5px solid rgba(107,131,70,0.3)",
                        }
                  }
                >
                  {isDone ? (
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : (
                    idx + 1
                  )}
                </div>
                <span
                  className="max-w-[72px] text-center text-[9.5px] font-medium leading-tight"
                  style={{ color: isCurrent ? "#2E3B1E" : "#6B8346", opacity: isFuture ? 0.6 : 1 }}
                >
                  {stage.name.length > 14 ? stage.name.slice(0, 14) + "…" : stage.name}
                </span>
              </button>
            </div>
          );
        })}
      </div>

      {/* ── Current stage header ── */}
      <div className="mb-5 rounded-2xl border border-[rgba(107,131,70,0.3)] bg-[#F3F6EA] px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-[#2E3B1E]">
                {currentStage.name}
              </h2>
              {currentStage.is_optional && (
                <span className="rounded-full bg-gold-100 px-2 py-0.5 text-[10px] font-semibold text-gold-700">
                  Optional
                </span>
              )}
            </div>
            <p className="mt-1 text-sm leading-relaxed text-[#4A5D32]">
              {currentStage.description}
            </p>
          </div>
          {currentStage.typical_duration_mins > 0 && (
            <span className="shrink-0 rounded-lg border border-[rgba(107,131,70,0.25)] bg-white px-2.5 py-1 text-xs font-semibold text-[#4A5D32]">
              {durationLabel}
            </span>
          )}
        </div>
      </div>

      {/* ── Drill cards for current stage ── */}
      {currentDrills.length > 0 ? (
        <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {currentDrills.map((drill) => (
            <div
              key={drill.key}
              className="rounded-2xl p-5"
              style={{
                background: "#F3F6EA",
                border: "1px solid rgba(107,131,70,0.2)",
              }}
            >
              <div
                className="flex h-10 w-10 items-center justify-center rounded-lg"
                style={{ background: "rgba(107,131,70,0.14)", color: "#4A5D32" }}
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.129.164 2.27.294 3.423.39 1.1.092 1.907 1.056 1.907 2.16v4.773l3.423-3.423a1.125 1.125 0 01.8-.33 48.31 48.31 0 005.58-.498c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                </svg>
              </div>
              <h3 className="mt-3 text-[15px] font-semibold" style={{ color: "#2E3B1E" }}>
                {drill.title}
              </h3>
              <p className="mt-1.5 text-[12.5px] leading-relaxed" style={{ color: "#4A5D32" }}>
                {drill.blurb}
              </p>
              <div
                className="mt-4 flex items-center justify-between border-t pt-3"
                style={{ borderColor: "rgba(107,131,70,0.3)", borderTopStyle: "dashed" }}
              >
                {drill.available ? (
                  <Link
                    href={drill.href}
                    className="rounded-[10px] px-2.5 py-1 text-[10px] font-bold text-white transition-transform hover:scale-105"
                    style={{ background: "#4A5D32" }}
                  >
                    Start →
                  </Link>
                ) : (
                  <span className="rounded-[10px] bg-gold-500/15 px-2 py-0.5 text-[10px] font-semibold text-gold-700">
                    Coming soon
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Stages with no drills (reference check, HR, salary negotiation) */
        <div className="mb-6 rounded-xl border border-dashed border-[rgba(107,131,70,0.3)] bg-white p-6 text-center">
          <p className="text-sm font-medium text-[#2E3B1E]">
            {currentStage.stage_id === "reference_check"
              ? "This stage happens off-platform. Prepare your reference list and brief your referees."
              : currentStage.stage_id === "salary_negotiation"
              ? "Prepare your counter-offer. Know your BATNA, market range, and total comp expectations."
              : "This stage happens externally. Prepare and then mark it done to move forward."}
          </p>
          {currentStage.stage_id === "salary_negotiation" && (
            <Link
              href="/dashboard/interview-prep/coach"
              className="mt-4 inline-block rounded-full px-4 py-1.5 text-xs font-semibold text-white"
              style={{ background: "#4A5D32" }}
            >
              Practice negotiation with Coach →
            </Link>
          )}
        </div>
      )}

      {/* ── Mark stage done + future stages ── */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1">
          {futureStages.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted">
                Up next
              </p>
              <div className="space-y-1.5">
                {futureStages.slice(0, 4).map((stage, idx) => (
                  <div
                    key={stage.stage_id}
                    className="flex items-center gap-2.5 opacity-50"
                  >
                    <div className="h-5 w-5 shrink-0 rounded-full border border-[rgba(107,131,70,0.4)] bg-[#F3F6EA]" />
                    <span className="text-sm text-[#4A5D32]">
                      {stage.name}
                      {stage.is_optional && (
                        <span className="ml-1.5 text-[10px] text-muted">(optional)</span>
                      )}
                    </span>
                  </div>
                ))}
                {futureStages.length > 4 && (
                  <p className="pl-7 text-xs text-muted">
                    +{futureStages.length - 4} more stages
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {!isLastStage && (
          <button
            onClick={advanceStage}
            disabled={advancing}
            className="shrink-0 rounded-full px-5 py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
            style={{ background: "#4A5D32" }}
          >
            {advancing ? "Saving…" : "Mark stage done →"}
          </button>
        )}

        {isLastStage && (
          <div className="rounded-2xl border border-[rgba(107,131,70,0.3)] bg-[#F3F6EA] px-5 py-3 text-center">
            <p className="text-sm font-bold text-[#2E3B1E]">
              🎉 Journey complete!
            </p>
            <p className="mt-0.5 text-xs text-[#4A5D32]">
              You&apos;ve walked through every stage.
            </p>
          </div>
        )}
      </div>

      {/* Oracle roundtable tease */}
      <div className="mt-10 flex flex-wrap items-center gap-4 rounded-2xl border border-dashed border-border bg-white p-6">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-purple-500/10 text-purple-700">
          <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold tracking-tight">
              Oracle — multi-persona recruiter roundtable
            </h3>
            <span className="rounded-[10px] bg-gold-500/15 px-2 py-0.5 text-[10px] font-semibold text-gold-700">
              Soon
            </span>
          </div>
          <p className="mt-1 text-sm text-muted">
            Three personas — hiring manager, recruiter, cross-functional partner — grill you in parallel.
          </p>
        </div>
        <button
          type="button"
          disabled
          className="rounded-full border border-border bg-white px-4 py-2 text-xs font-semibold text-muted"
        >
          Notify me
        </button>
      </div>
    </main>
  );
}
