"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { VerticalStepper } from "@/components/VerticalStepper";
import { StepJobDetails } from "./steps/StepJobDetails";
import { StepEnrich } from "./steps/StepEnrich";
import { StepBuild } from "./steps/StepBuild";
import { StepReview } from "./steps/StepReview";

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
}

interface SubStep {
  label: string;
  done: boolean;
}

const STEP_LABELS = [
  "Job Details",
  "Enrich",
  "Build",
  "Review",
];

const STORAGE_KEY = "linkright_wizard_v3";

const EMPTY_DATA: WizardData = {
  jd_text: "",
  career_text: "",
  model_provider: "groq",
  model_id: "llama-3.3-70b-versatile",
  api_key: "",
  job_id: null,
  qa_answers: [],
  target_company: "",
  target_role: "",
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

export function WizardShell({ userId }: { userId: string }) {
  const saved = typeof window !== "undefined" ? loadSaved() : null;

  // If there's a saved job_id and it was on Build or Review, resume there
  const initialStep = saved?.data?.job_id
    ? saved.step >= 2
      ? saved.step
      : 2
    : (saved?.step ?? 0);

  const [step, setStep] = useState(initialStep);
  const [data, setData] = useState<WizardData>(saved?.data ?? { ...EMPTY_DATA });
  const [retryKey, setRetryKey] = useState(0);
  const [buildSubSteps, setBuildSubSteps] = useState<SubStep[]>([]);

  // Load settings from user_settings (career_text, api_key, model)
  useEffect(() => {
    async function loadSettings() {
      try {
        const resp = await fetch("/api/user/settings");
        if (!resp.ok) return;
        const settings = await resp.json();
        setData((prev) => ({
          ...prev,
          career_text: prev.career_text || settings.career_text || "",
          model_provider: prev.model_provider || settings.model_provider || "groq",
          model_id: prev.model_id || settings.model_id || "llama-3.3-70b-versatile",
          api_key: prev.api_key || settings.api_key || "",
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
  const stepDefs = STEP_LABELS.map((label, i) => ({
    label,
    subSteps: i === 2 ? buildSubSteps : undefined,
  }));

  return (
    <>
      {/* Navbar */}
      <nav className="border-b border-border bg-surface/80 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <Link href="/dashboard" className="text-lg font-bold tracking-tight">
            Link<span className="text-accent">Right</span>
          </Link>
          <Link
            href="/dashboard"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            &larr; Dashboard
          </Link>
        </div>
      </nav>

      {/* Sidebar + Content layout */}
      <div className="flex flex-col lg:flex-row min-h-[calc(100vh-3.5rem)]">
        <VerticalStepper steps={stepDefs} currentStep={step} />

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-10">
          <div className="mx-auto max-w-3xl">
            {step === 0 && (
              <StepJobDetails data={data} update={update} next={next} />
            )}
            {step === 1 && (
              <StepEnrich
                data={data}
                update={update}
                next={next}
                back={back}
              />
            )}
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
