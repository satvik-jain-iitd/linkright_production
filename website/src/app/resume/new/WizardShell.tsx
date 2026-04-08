"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { VerticalStepper } from "@/components/VerticalStepper";
import { StepJobDetails } from "./steps/StepJobDetails";
// [WIZARD-STREAMLINE] StepJDAnalysis merged into StepJobDetails — import kept for type only
// [WIZARD-STREAMLINE] import { StepJDAnalysis } from "./steps/StepJDAnalysis";
// [WIZARD-STREAMLINE] StepBrandColors + StepEnrich merged into StepCustomize
// import { StepBrandColors } from "./steps/StepBrandColors";
// import { StepEnrich } from "./steps/StepEnrich";
import { StepCustomize } from "./steps/StepCustomize";
import { StepBuild } from "./steps/StepBuild";
import { StepReview } from "./steps/StepReview";
import type { JDAnalysisResult } from "./steps/StepJobDetails";

export interface WizardData {
  jd_text: string;
  career_text: string;
  model_provider: string;
  model_id: string;
  api_key: string;
  job_id: string | null;
  qa_answers: { question: string; answer: string }[];
  target_company: string;
  target_role: string;
  brand_colors: {
    brand_primary: string;
    brand_secondary: string;
    brand_tertiary: string | null;
    brand_quaternary: string | null;
  } | null;
  jd_analysis: JDAnalysisResult | null;
}

interface SubStep {
  label: string;
  done: boolean;
}

const STEP_LABELS = [
  "Job Details",     // [WIZARD-STREAMLINE] includes JD Analysis inline
  "Customize",       // [WIZARD-STREAMLINE] Brand Colors + Enrich merged
  "Build",
  "Review",
];

// [WIZARD-STREAMLINE] Bumped from v7 → v9 due to step index change (6 steps → 4 steps)
const STORAGE_KEY = "linkright_wizard_v9";

// [BYOK-REMOVED] Hardcoded provider/model — no user selection
const model_provider = "groq";
const model_id = "llama-3.1-8b-instant";

const EMPTY_DATA: WizardData = {
  jd_text: "",
  career_text: "",
  model_provider,   // [BYOK-REMOVED] hardcoded, was user-selectable
  model_id,         // [BYOK-REMOVED] hardcoded, was user-selectable
  api_key: "",      // [BYOK-REMOVED] no longer used, kept for interface compat
  job_id: null,
  qa_answers: [],
  target_company: "",
  target_role: "",
  brand_colors: null,
  jd_analysis: null,
};

function loadSaved(): { step: number; data: WizardData } | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function WizardShell({ userId, jobId }: { userId: string; jobId?: string }) {
  const saved = typeof window !== "undefined" ? loadSaved() : null;

  // [WIZARD-STREAMLINE] 4 steps: JobDetails=0, Customize=1, Build=2, Review=3
  // If jobId param present, go straight to Review (step 3)
  // If saved job_id and was on Build/Review, resume there
  const initialStep = jobId
    ? 3
    : saved?.data?.job_id
      ? saved.step >= 2
        ? saved.step
        : 2
      : (saved?.step ?? 0);

  const [step, setStep] = useState(initialStep);
  const [data, setData] = useState<WizardData>(saved?.data ?? { ...EMPTY_DATA });
  const [retryKey, setRetryKey] = useState(0);
  const [buildSubSteps, setBuildSubSteps] = useState<SubStep[]>([]);

  // If jobId query param provided, restore completed job into wizard at StepReview
  useEffect(() => {
    if (!jobId) return;
    // Already loaded this job in session — just jump to review
    // [WIZARD-STREAMLINE] Review is now step 3 (4 steps total)
    const current = loadSaved();
    if (current?.data?.job_id === jobId) {
      setStep(3);
      return;
    }
    async function restoreJob() {
      const res = await fetch(`/api/resume/${jobId}`);
      if (!res.ok) return;
      const job = await res.json();
      setData((prev) => ({
        ...prev,
        job_id: job.id,
        jd_text: job.jd_text || "",
        career_text: job.career_text || "",
        model_provider: job.model_provider || prev.model_provider,
        model_id: job.model_id || prev.model_id,
        target_company: job.target_company || "",
      }));
      setStep(3);
    }
    restoreJob();
  }, [jobId]);

  // Load settings from user_settings (career_text only — model is hardcoded now)
  useEffect(() => {
    async function loadSettings() {
      try {
        const resp = await fetch("/api/user/settings");
        if (!resp.ok) return;
        const settings = await resp.json();

        // [BYOK-REMOVED] API key fetching from user_api_keys disabled — server manages keys
        /* [BYOK-REMOVED]
        const provider = settings.model_provider || "groq";

        // Fetch primary key from user_api_keys for this provider
        let primaryKeyId = "";
        try {
          const keysResp = await fetch(`/api/user/keys?provider=${encodeURIComponent(provider)}`);
          if (keysResp.ok) {
            const { keys } = await keysResp.json();
            const activeKey = (keys || []).find((k: { is_active: boolean }) => k.is_active);
            if (activeKey) primaryKeyId = activeKey.id;
          }
        } catch {
          // Keys endpoint not available — fall back to settings
        }
        */

        setData((prev) => ({
          ...prev,
          career_text: prev.career_text || settings.career_text || "",
          // [BYOK-REMOVED] model_provider and model_id no longer loaded from settings — hardcoded
          // model_provider: prev.model_provider || provider,
          // model_id: prev.model_id || settings.model_id || "llama-3.1-8b-instant",
          // api_key: prev.api_key || primaryKeyId || settings.api_key || "",
        }));
      } catch {
        // Settings not available yet — user will configure inline
      }
    }
    loadSettings();
  }, []);

  // Auto-save to sessionStorage on every change
  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ step, data }));
  }, [step, data]);

  const update = useCallback(
    (fields: Partial<WizardData>) =>
      setData((prev) => ({ ...prev, ...fields })),
    []
  );

  const stepping = useRef(false);
  const next = () => {
    if (stepping.current) return;
    stepping.current = true;
    setStep((s) => Math.min(s + 1, STEP_LABELS.length - 1));
    setTimeout(() => { stepping.current = false; }, 300);
  };
  const back = () => setStep((s) => Math.max(s - 1, 0));

  const reset = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    setStep(0);
    setData({ ...EMPTY_DATA });
    setRetryKey((k) => k + 1);
  };

  const retry = () => {
    setData((prev) => ({ ...prev, job_id: null }));
    setRetryKey((k) => k + 1);
  };

  // Build step definitions for VerticalStepper
  // [WIZARD-STREAMLINE] Build is step 2 in 4-step wizard
  const stepDefs = STEP_LABELS.map((label, i) => ({
    label,
    subSteps: i === 2 ? buildSubSteps : undefined,
  }));

  // [WIZARD-STREAMLINE] Review is step 3 (last step) — gets full-width layout
  const isReview = step === 3;

  return (
    <>
      {/* Navbar */}
      <AppNav user={null} variant="minimal" />
      {
      // [NAV-REDESIGN] <nav className="border-b border-border bg-surface/80 backdrop-blur-xl">
      // [NAV-REDESIGN]   <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
      // [NAV-REDESIGN]     <Link href="/dashboard" className="text-lg font-bold tracking-tight">
      // [NAV-REDESIGN]       Link<span className="text-accent">Right</span>
      // [NAV-REDESIGN]     </Link>
      // [NAV-REDESIGN]     <Link
      // [NAV-REDESIGN]       href="/dashboard"
      // [NAV-REDESIGN]       className="text-sm text-muted transition-colors hover:text-foreground"
      // [NAV-REDESIGN]     >
      // [NAV-REDESIGN]       &larr; Dashboard
      // [NAV-REDESIGN]     </Link>
      // [NAV-REDESIGN]   </div>
      // [NAV-REDESIGN] </nav>
      }

      {/* Sidebar + Content layout */}
      <div className="flex flex-col lg:flex-row min-h-[calc(100vh-3.5rem)]">
        <VerticalStepper steps={stepDefs} currentStep={step} />

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-10">
          <div className={isReview ? "w-full" : "mx-auto max-w-3xl"}>
            {step === 0 && (
              <StepJobDetails data={data} update={update} next={next} />
            )}
            {step === 1 && (
              <StepCustomize data={data} update={update} next={next} back={back} />
            )}
            {/* [WIZARD-STREAMLINE] StepBrandColors + StepEnrich replaced by StepCustomize above */}
            {step === 2 && (
              <StepBuild
                key={retryKey}
                data={data}
                update={update}
                next={next}
                onReset={reset}
                onRetry={retry}
                onSubSteps={setBuildSubSteps}
              />
            )}
            {step === 3 && <StepReview data={data} onNewResume={reset} />}
          </div>
        </main>
      </div>
    </>
  );
}
