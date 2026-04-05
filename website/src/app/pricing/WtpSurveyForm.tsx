"use client";

import { useState } from "react";
import { track } from "@/lib/analytics";
import { createClient } from "@/lib/supabase/client";
import Link from "next/link";

const PRICE_OPTIONS = [
  { label: "Under Rs. 99", value: "0-99" },
  { label: "Rs. 100-299", value: "100-299" },
  { label: "Rs. 300-499", value: "300-499" },
  { label: "Rs. 500-999", value: "500-999" },
  { label: "Rs. 1000+", value: "1000+" },
];

const FEATURE_OPTIONS = [
  "Width optimization (95-100% fill)",
  "Brand color matching",
  "Anti-AI writing filter",
  "JD-based bullet scoring",
  "One-page guarantee",
  "Application Q&A",
];

interface WtpSurveyFormProps {
  isLoggedIn: boolean;
  userId: string | null;
  alreadySubmitted: boolean;
}

export function WtpSurveyForm({ isLoggedIn, userId, alreadySubmitted }: WtpSurveyFormProps) {
  const [wouldPay, setWouldPay] = useState<"yes" | "no" | "maybe" | null>(null);
  const [priceRange, setPriceRange] = useState<string | null>(null);
  const [features, setFeatures] = useState<Set<string>>(new Set());
  const [feedback, setFeedback] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const toggleFeature = (f: string) => {
    setFeatures((prev) => {
      const next = new Set(prev);
      if (next.has(f)) next.delete(f);
      else next.add(f);
      return next;
    });
  };

  const canSubmit = wouldPay !== null && (wouldPay === "no" || priceRange !== null);

  const handleSubmit = async () => {
    if (!canSubmit || submitting) return;
    setSubmitting(true);

    try {
      const supabase = createClient();
      await supabase.from("survey_responses").insert({
        user_id: userId,
        would_pay: wouldPay,
        price_range: priceRange ?? "0-99",
        important_features: Array.from(features),
        feedback: feedback || null,
      });

      track({
        event: "survey_submitted",
        properties: {
          would_pay: wouldPay!,
          price_range: priceRange ?? "skipped",
          feature_count: features.size,
          has_feedback: feedback.length > 0,
          is_authenticated: isLoggedIn,
        },
      });
    } catch {
      // Survey is non-critical — don't block the user
    }

    setSubmitted(true);
    setSubmitting(false);
  };

  // Already submitted state
  if (alreadySubmitted) {
    return (
      <div className="mx-auto max-w-2xl text-center">
        <div className="rounded-2xl border border-accent/20 bg-accent/5 p-12">
          <div className="text-4xl">🙏</div>
          <h2 className="mt-4 text-xl font-semibold">Thanks for your feedback!</h2>
          <p className="mt-2 text-sm text-muted">
            You&apos;ve already shared your thoughts. Your input helps us build the right pricing.
          </p>
          <Link
            href={isLoggedIn ? "/dashboard" : "/"}
            className="mt-6 inline-block rounded-full bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
          >
            {isLoggedIn ? "Back to dashboard" : "Back to home"}
          </Link>
        </div>
      </div>
    );
  }

  // Just submitted state
  if (submitted) {
    return (
      <div className="mx-auto max-w-2xl text-center">
        <div className="rounded-2xl border border-accent/20 bg-accent/5 p-12">
          <div className="text-4xl">🎉</div>
          <h2 className="mt-4 text-xl font-semibold">Thank you!</h2>
          <p className="mt-2 text-sm text-muted">
            Your response has been recorded. It directly shapes what we build next.
          </p>
          <Link
            href={isLoggedIn ? "/dashboard" : "/"}
            className="mt-6 inline-block rounded-full bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
          >
            {isLoggedIn ? "Back to dashboard" : "Back to home"}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      {/* Header */}
      <div className="text-center">
        <p className="mb-2 text-sm font-medium uppercase tracking-widest text-accent">
          Help Us Build
        </p>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          What would you pay?
        </h1>
        <p className="mt-4 text-muted">
          You&apos;ve tried Sync. Now help us figure out pricing. Your honest answers shape what we build next.
        </p>
      </div>

      {/* Survey form */}
      <div className="mt-10 space-y-10">
        {/* Q1: Would you pay? */}
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
            1. Would you pay for a tool like Sync?
          </h2>
          <div className="mt-4 flex gap-3">
            {(["yes", "maybe", "no"] as const).map((option) => (
              <button
                key={option}
                onClick={() => {
                  setWouldPay(option);
                  if (option === "no") setPriceRange(null);
                }}
                className={`flex-1 rounded-xl border py-3 text-sm font-medium transition-all ${
                  wouldPay === option
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-border bg-surface text-muted hover:border-accent/30"
                }`}
              >
                {option === "yes" ? "Yes" : option === "maybe" ? "Maybe" : "No"}
              </button>
            ))}
          </div>
        </div>

        {/* Q2: Price range (conditional) */}
        {wouldPay && wouldPay !== "no" && (
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
              2. How much would you pay per resume?
            </h2>
            <div className="mt-4 flex flex-wrap gap-3">
              {PRICE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setPriceRange(opt.value)}
                  className={`rounded-full border px-4 py-2 text-sm font-medium transition-all ${
                    priceRange === opt.value
                      ? "border-accent bg-accent/10 text-accent"
                      : "border-border bg-surface text-muted hover:border-accent/30"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Q3: Features */}
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
            {wouldPay && wouldPay !== "no" ? "3" : "2"}. What features matter most to you?
          </h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {FEATURE_OPTIONS.map((f) => (
              <button
                key={f}
                onClick={() => toggleFeature(f)}
                className={`rounded-xl border px-4 py-3 text-left text-sm transition-all ${
                  features.has(f)
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-border bg-surface text-muted hover:border-accent/30"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Q4: Open feedback */}
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
            {wouldPay && wouldPay !== "no" ? "4" : "3"}. Anything else you&apos;d like to share?
          </h2>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Optional — but we read every response"
            className="mt-4 w-full resize-none rounded-xl border border-border bg-surface p-4 text-sm text-foreground placeholder-muted transition-colors focus:border-accent/50 focus:outline-none"
            rows={3}
          />
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!canSubmit || submitting}
          className="w-full rounded-full bg-cta py-3.5 text-sm font-semibold text-white transition-all hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? (
            <span className="flex items-center justify-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Submitting...
            </span>
          ) : (
            "Submit feedback"
          )}
        </button>
      </div>
    </div>
  );
}
