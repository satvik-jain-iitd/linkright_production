"use client";

import { useEffect, useMemo, useState } from "react";
import { detectAtsFromUrl, slugFromCompanyName } from "@/lib/ats-detect";

interface AddCompanyModalProps {
  onClose: () => void;
  onAdded: () => void;
}

const ATS_OPTIONS = [
  { value: "", label: "Auto-detect" },
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
  const [careersUrl, setCareersUrl] = useState("");
  const [positiveKw, setPositiveKw] = useState("");
  const [negativeKw, setNegativeKw] = useState("");
  const [advanced, setAdvanced] = useState(false);
  const [manualSlug, setManualSlug] = useState("");
  const [manualAts, setManualAts] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Run detection on every URL change (cheap, pure function).
  const detection = useMemo(
    () => (careersUrl ? detectAtsFromUrl(careersUrl) : { ats: null, slug: null, confidence: null }),
    [careersUrl],
  );

  // If user hasn't typed a manual slug, derive one from (detection ?? company name).
  const derivedSlug = useMemo(() => {
    if (manualSlug.trim()) return manualSlug.trim();
    if (detection.slug) return detection.slug;
    return slugFromCompanyName(companyName);
  }, [manualSlug, detection.slug, companyName]);

  const effectiveAts = manualAts || detection.ats || "";

  // Auto-open Advanced if auto-detect didn't find an ATS once user typed a URL.
  useEffect(() => {
    if (careersUrl && !detection.ats && !advanced) {
      setAdvanced(true);
    }
  }, [careersUrl, detection.ats, advanced]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim()) {
      setError("Company name is required");
      return;
    }
    if (!derivedSlug) {
      setError("Could not derive a slug — add one under Advanced");
      return;
    }
    setSubmitting(true);
    setError(null);

    const res = await fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: companyName.trim(),
        company_slug: derivedSlug,
        ats_provider: effectiveAts || null,
        careers_url: careersUrl.trim() || null,
        positive_keywords: positiveKw.split(",").map((k) => k.trim()).filter(Boolean),
        negative_keywords: negativeKw.split(",").map((k) => k.trim()).filter(Boolean),
      }),
    });

    if (res.ok) {
      onAdded();
    } else {
      const data = await res.json().catch(() => ({}));
      setError(data.error || "Failed to add company");
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div data-testid="add-company-modal" className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-foreground">Add Company</h2>
          <button onClick={onClose} aria-label="Close" className="text-muted hover:text-foreground">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="mt-2 text-xs text-muted">
          Paste the company&apos;s careers URL — we&apos;ll auto-detect the ATS and slug.
        </p>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground">Company name *</label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="e.g., Credo AI"
              required
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground">Careers URL</label>
            <input
              type="url"
              value={careersUrl}
              onChange={(e) => setCareersUrl(e.target.value)}
              placeholder="https://jobs.lever.co/credo-ai  or  https://boards.greenhouse.io/credoai"
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
            {/* Auto-detect feedback chip */}
            {careersUrl && (
              <div className="mt-2 flex items-center gap-2 text-xs">
                {detection.ats ? (
                  <span className="rounded-full bg-primary-500/10 px-2.5 py-0.5 font-medium text-primary-700">
                    ✓ Detected: {detection.ats}{detection.slug ? ` · ${detection.slug}` : ""}
                  </span>
                ) : (
                  <span className="rounded-full bg-gold-500/10 px-2.5 py-0.5 font-medium text-gold-700">
                    Couldn&apos;t auto-detect ATS — set it below
                  </span>
                )}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => setAdvanced((v) => !v)}
            className="text-xs font-medium text-accent hover:underline"
          >
            {advanced ? "Hide advanced" : "Advanced options"}
          </button>

          {advanced && (
            <div className="space-y-4 rounded-xl border border-border/60 bg-background/40 p-4">
              <div>
                <label className="block text-xs font-medium text-foreground">Slug override</label>
                <input
                  type="text"
                  value={manualSlug}
                  onChange={(e) => setManualSlug(e.target.value)}
                  placeholder={derivedSlug || "e.g., credo-ai"}
                  className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
                />
                <p className="mt-1 text-[11px] text-muted">
                  Currently using: <code className="rounded bg-muted/20 px-1">{derivedSlug || "(none)"}</code>
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground">ATS override</label>
                <select
                  value={manualAts}
                  onChange={(e) => setManualAts(e.target.value)}
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
                <label className="block text-xs font-medium text-foreground">
                  Include keywords <span className="text-muted font-normal">(comma-separated)</span>
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
                <label className="block text-xs font-medium text-foreground">
                  Exclude keywords <span className="text-muted font-normal">(comma-separated)</span>
                </label>
                <input
                  type="text"
                  value={negativeKw}
                  onChange={(e) => setNegativeKw(e.target.value)}
                  placeholder="intern, junior, contract"
                  className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
                />
              </div>
            </div>
          )}

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
              disabled={submitting || !companyName.trim()}
              className="rounded-full bg-cta px-5 py-2 text-sm font-semibold text-white shadow-cta transition-colors hover:bg-cta-hover disabled:opacity-50"
            >
              {submitting ? "Adding…" : "Add Company"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
