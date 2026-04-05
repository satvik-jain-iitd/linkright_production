"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { StepJD } from "./steps/StepJD";
import { StepCareer } from "./steps/StepCareer";
import { StepConfigure } from "./steps/StepConfigure";
import { StepEnrich } from "./steps/StepEnrich";
import { StepGenerate } from "./steps/StepGenerate";
import { StepReview } from "./steps/StepReview";

export interface WizardData {
  jd_text: string;
  career_text: string;
  model_provider: string;
  model_id: string;
  api_key: string;
  job_id: string | null;
  qa_answers: { question: string; answer: string }[];
}

const STEPS = [
  "Paste JD",
  "Career Profile",
  "Configure",
  "Enrich",
  "Generate",
  "Review",
];
const STORAGE_KEY = "linkright_wizard_v2";

const EMPTY_DATA: WizardData = {
  jd_text: "",
  career_text: "",
  model_provider: "openrouter",
  model_id: "meta-llama/llama-3.1-8b-instruct:free",
  api_key: "",
  job_id: null,
  qa_answers: [],
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

  // If there's a saved job_id and it was on Generate or Review, resume there
  const initialStep = saved?.data?.job_id
    ? saved.step >= 4
      ? saved.step
      : 4
    : (saved?.step ?? 0);

  const [step, setStep] = useState(initialStep);
  const [data, setData] = useState<WizardData>(saved?.data ?? { ...EMPTY_DATA });
  const [retryKey, setRetryKey] = useState(0);

  // Auto-save to sessionStorage on every change
  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ step, data }));
  }, [step, data]);

  const update = useCallback(
    (fields: Partial<WizardData>) =>
      setData((prev) => ({ ...prev, ...fields })),
    []
  );

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
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

  return (
    <>
      {/* Navbar */}
      <nav className="border-b border-border bg-surface/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-6">
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

      {/* Step indicator */}
      <div className="mx-auto max-w-4xl px-6 pt-8">
        <div className="flex items-center gap-2">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                  i < step
                    ? "bg-accent text-white"
                    : i === step
                      ? "bg-accent text-white ring-2 ring-accent/30 ring-offset-2"
                      : "bg-border text-muted"
                }`}
              >
                {i < step ? "\u2713" : i + 1}
              </div>
              <span
                className={`hidden text-sm sm:block ${
                  i === step ? "font-medium text-foreground" : "text-muted"
                }`}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div
                  className={`h-px w-6 sm:w-10 ${
                    i < step ? "bg-accent" : "bg-border"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step content */}
      <div className="mx-auto max-w-4xl px-6 py-10">
        {step === 0 && <StepJD data={data} update={update} next={next} />}
        {step === 1 && (
          <StepCareer data={data} update={update} next={next} back={back} />
        )}
        {step === 2 && (
          <StepConfigure data={data} update={update} next={next} back={back} />
        )}
        {step === 3 && (
          <StepEnrich
            data={data}
            update={update}
            next={next}
            back={back}
          />
        )}
        {step === 4 && (
          <StepGenerate
            key={retryKey}
            data={data}
            update={update}
            next={next}
            onReset={reset}
            onRetry={retry}
          />
        )}
        {step === 5 && <StepReview data={data} onNewResume={reset} />}
      </div>
    </>
  );
}
