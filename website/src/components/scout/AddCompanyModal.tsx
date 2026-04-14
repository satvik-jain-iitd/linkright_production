"use client";

import { useState } from "react";

interface AddCompanyModalProps {
  onClose: () => void;
  onAdded: () => void;
}

const ATS_OPTIONS = [
  { value: "", label: "Select ATS platform" },
  { value: "greenhouse", label: "Greenhouse" },
  { value: "lever", label: "Lever" },
  { value: "ashby", label: "Ashby" },
  { value: "smartrecruiters", label: "SmartRecruiters" },
  { value: "workable", label: "Workable" },
  { value: "recruitee", label: "Recruitee" },
  { value: "bamboohr", label: "BambooHR" },
  { value: "workday", label: "Workday" },
  { value: "icims", label: "iCIMS" },
];

export function AddCompanyModal({ onClose, onAdded }: AddCompanyModalProps) {
  const [companyName, setCompanyName] = useState("");
  const [companySlug, setCompanySlug] = useState("");
  const [atsProvider, setAtsProvider] = useState("");
  const [careersUrl, setCareersUrl] = useState("");
  const [positiveKw, setPositiveKw] = useState("");
  const [negativeKw, setNegativeKw] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const res = await fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: companyName.trim(),
        company_slug: companySlug.trim(),
        ats_provider: atsProvider || null,
        careers_url: careersUrl.trim() || null,
        positive_keywords: positiveKw
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean),
        negative_keywords: negativeKw
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean),
      }),
    });

    if (res.ok) {
      onAdded();
    } else {
      const data = await res.json();
      setError(data.error || "Failed to add company");
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div data-testid="add-company-modal" className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-foreground">Add Company</h2>
          <button onClick={onClose} className="text-muted hover:text-foreground">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground">Company Name *</label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="e.g., Stripe"
              required
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground">Company Slug *</label>
            <input
              type="text"
              value={companySlug}
              onChange={(e) => setCompanySlug(e.target.value)}
              placeholder="e.g., stripe (used in ATS URL)"
              required
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground">ATS Platform</label>
            <select
              value={atsProvider}
              onChange={(e) => setAtsProvider(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
            >
              {ATS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground">Careers URL</label>
            <input
              type="url"
              value={careersUrl}
              onChange={(e) => setCareersUrl(e.target.value)}
              placeholder="https://stripe.com/jobs"
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground">
              Include Keywords <span className="text-muted font-normal">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={positiveKw}
              onChange={(e) => setPositiveKw(e.target.value)}
              placeholder="product manager, strategy, growth"
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground">
              Exclude Keywords <span className="text-muted font-normal">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={negativeKw}
              onChange={(e) => setNegativeKw(e.target.value)}
              placeholder="intern, junior, contract"
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm text-muted transition-colors hover:text-foreground"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-cta px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:opacity-50"
            >
              {submitting ? "Adding..." : "Add Company"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
