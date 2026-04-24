"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
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
import { StepLayout } from "./steps/StepLayout";
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
  section_order?: string[];
}

interface SubStep {
  label: string;
  done: boolean;
}

const STEP_LABELS = [
  "Job Details",     // [WIZARD-STREAMLINE] includes JD Analysis inline
  "Customize",       // [WIZARD-STREAMLINE] Brand Colors + Enrich merged
  "Layout",
  "Build",
  "Review",
];

// [WIZARD-STREAMLINE] Bumped from v7 → v9 due to step index change (6 steps → 4 steps)
const STORAGE_KEY = "linkright_wizard_v9";

// [BYOK-REMOVED] Hardcoded provider/model — no user selection
const model_provider = "groq";
const model_id = "llama-3.3-70b-versatile";

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
  brand_colors: {
    brand_primary: "#1B2A4A",
    brand_secondary: "#2563EB",
    brand_tertiary: "#6B7280",
    brand_quaternary: "#FFFFFF",
  },
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

export function WizardShell({ userId, jobId, retryJdText, discoveryCompany, discoveryRole, isFirstResume }: { userId: string; jobId?: string; retryJdText?: string; discoveryCompany?: string; discoveryRole?: string; isFirstResume?: boolean }) {
  // Discovery fast-path: pre-filled company + JD means we skip Job Details + Customize.
  // Clear any prior saved session so old state doesn't interfere.
  const isFastPath = !!(discoveryCompany && retryJdText);
  if (isFastPath && typeof window !== "undefined") {
    sessionStorage.removeItem(STORAGE_KEY);
  }
  const saved = !isFastPath && typeof window !== "undefined" ? loadSaved() : null;

  // 5 steps: JobDetails=0, Customize=1, Layout=2, Build=3, Review=4
  // Fast-path (discovery with pre-filled JD+company+role): jump directly to Build (step 3)
  // First-time resume with no discovery: show step 0 only, then jump to Build
  const initialStep = jobId
    ? 4
    : isFastPath
      ? 3
      : saved?.data?.job_id
        ? saved.step >= 3
          ? saved.step
          : 3
        : (saved?.step ?? 0);

  const router = useRouter();
  const [step, setStep] = useState(initialStep);
  const initialData: WizardData = saved?.data ?? { ...EMPTY_DATA };
  if (retryJdText && !jobId) {
    initialData.jd_text = retryJdText;
  }
  if (discoveryCompany && !saved?.data) {
    initialData.target_company = discoveryCompany;
  }
  if (discoveryRole && !saved?.data) {
    initialData.target_role = discoveryRole;
  }
  const [data, setData] = useState<WizardData>(initialData);
  const [retryKey, setRetryKey] = useState(0);
  const [buildSubSteps, setBuildSubSteps] = useState<SubStep[]>([]);

  // If jobId query param provided, restore completed job into wizard at StepReview
  useEffect(() => {
    if (!jobId) return;
    // Already loaded this job in session — just jump to review
    const current = loadSaved();
    if (current?.data?.job_id === jobId) {
      setStep(4);
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
      setStep(4);
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
    setStep((s) => {
      // First-time resume: from step 0 (Job Details) skip directly to Build (step 3)
      if (isFirstResume && s === 0) return 3;
      return Math.min(s + 1, STEP_LABELS.length - 1);
    });
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
  const stepDefs = STEP_LABELS.map((label, i) => ({
    label,
    subSteps: i === 3 ? buildSubSteps : undefined,
  }));

  // Review is step 4 (last step) — gets full-width layout
  const isReview = step === 4;

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
        {!isFastPath && (
          <VerticalStepper
            steps={stepDefs}
            currentStep={step}
            onStepClick={(i) => { if (i < step) setStep(i); }}
          />
        )}

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-10">
          <div className={isReview ? "w-full" : "mx-auto max-w-3xl"}>
            {step === 0 && (
              <StepJobDetails data={data} update={update} next={next} />
            )}
            {step === 1 && (
              <StepCustomize data={data} update={update} next={next} back={back} />
            )}
            {step === 2 && (
              <StepLayout data={data} update={update} next={next} back={back} />
            )}
            {step === 3 && (
              <StepBuild
                key={retryKey}
                data={data}
                update={update}
                next={next}
                onReset={reset}
                onRetry={retry}
                onSubSteps={setBuildSubSteps}
                onNeedCareer={() => router.push("/my-career?from=build")}
              />
            )}
            {step === 4 && <StepReview data={data} onNewResume={reset} />}
          </div>
        </main>
      </div>
    </>
  );
}
