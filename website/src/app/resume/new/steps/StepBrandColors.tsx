"use client";

import { useEffect, useRef, useState } from "react";
import type { WizardData } from "../WizardShell";

interface BrandColors {
  brand_primary: string;
  brand_secondary: string;
  brand_tertiary: string;
  brand_quaternary: string;
}

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

const COLOR_LABELS = [
  { key: "brand_primary", label: "Primary" },
  { key: "brand_secondary", label: "Secondary" },
  { key: "brand_tertiary", label: "Tertiary" },
  { key: "brand_quaternary", label: "Quaternary" },
] as const;

function isValidHex(v: string) {
  return /^#[0-9A-Fa-f]{6}$/.test(v);
}

export function StepBrandColors({ data, update, next, back }: Props) {
  const [colors, setColors] = useState<BrandColors>(
    data.brand_colors || {
      brand_primary: "#1B2A4A",
      brand_secondary: "#93702b",
      brand_tertiary: "#3D5A80",
      brand_quaternary: "#D4B87A",
    }
  );
  const [loading, setLoading] = useState(!data.brand_colors);
  const [error, setError] = useState<string | null>(null);
  const [hexInputs, setHexInputs] = useState<BrandColors>(
    data.brand_colors || {
      brand_primary: "#1B2A4A",
      brand_secondary: "#93702b",
      brand_tertiary: "#3D5A80",
      brand_quaternary: "#D4B87A",
    }
  );
  const fetched = useRef(false);

  const fetchColors = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/resume/brand-colors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: data.target_company,
          jd_text: data.jd_text,
          model_provider: data.model_provider,
          model_id: data.model_id,
          api_key: data.api_key,
        }),
      });
      if (!resp.ok) throw new Error("Failed to extract colors");
      const result = await resp.json();
      const extracted: BrandColors = {
        brand_primary: result.brand_primary,
        brand_secondary: result.brand_secondary,
        brand_tertiary: result.brand_tertiary,
        brand_quaternary: result.brand_quaternary,
      };
      setColors(extracted);
      setHexInputs(extracted);
    } catch {
      setError("Could not auto-extract colors — using defaults. Edit manually below.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (fetched.current || data.brand_colors) return;
    fetched.current = true;
    fetchColors();
  }, []);

  const handleColorChange = (key: keyof BrandColors, value: string) => {
    setHexInputs((prev) => ({ ...prev, [key]: value }));
    if (isValidHex(value)) {
      setColors((prev) => ({ ...prev, [key]: value }));
    }
  };

  const handlePickerChange = (key: keyof BrandColors, value: string) => {
    setColors((prev) => ({ ...prev, [key]: value }));
    setHexInputs((prev) => ({ ...prev, [key]: value }));
  };

  const handleNext = () => {
    update({ brand_colors: colors });
    next();
  };

  const allValid = Object.values(hexInputs).every(isValidHex);

  return (
    <div>
      <h2 className="text-2xl font-bold">Brand Colors</h2>
      <p className="mt-2 text-sm text-muted">
        Colors extracted for{" "}
        <span className="font-medium text-foreground">{data.target_company}</span>.
        Review and edit before generating your resume.
      </p>

      {loading ? (
        <div className="mt-10 flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
          <p className="text-sm text-muted">Extracting brand colors...</p>
        </div>
      ) : (
        <>
          {error && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
              {error}
            </div>
          )}

          {/* Identity horizon preview */}
          <div className="mt-8">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
              Preview — Identity Stripe
            </p>
            <div className="flex h-3 w-full overflow-hidden rounded-full shadow-sm">
              <div className="flex-1" style={{ background: colors.brand_primary }} />
              <div className="flex-1" style={{ background: colors.brand_secondary }} />
              <div className="flex-1" style={{ background: colors.brand_tertiary }} />
              <div className="flex-1" style={{ background: colors.brand_quaternary }} />
            </div>
          </div>

          {/* Section title preview */}
          <div className="mt-4 rounded-xl border border-border bg-surface px-5 py-4">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
              Section title preview
            </p>
            <div
              className="text-sm font-medium"
              style={{ color: colors.brand_primary }}
            >
              Professional Experience
            </div>
            <div
              className="mt-0.5 h-px w-full opacity-70"
              style={{
                background: `linear-gradient(to right, ${colors.brand_primary} 25%, ${colors.brand_secondary} 25%, ${colors.brand_secondary} 50%, ${colors.brand_tertiary} 50%, ${colors.brand_tertiary} 75%, ${colors.brand_quaternary} 75%)`,
              }}
            />
          </div>

          {/* Color pickers */}
          <div className="mt-6 grid grid-cols-2 gap-4">
            {COLOR_LABELS.map(({ key, label }) => (
              <div
                key={key}
                className="flex items-center gap-3 rounded-xl border border-border bg-surface p-4"
              >
                <div className="relative flex-shrink-0">
                  <div
                    className="h-10 w-10 cursor-pointer rounded-lg border border-border shadow-sm"
                    style={{ background: colors[key] }}
                  />
                  <input
                    type="color"
                    value={colors[key]}
                    onChange={(e) => handlePickerChange(key, e.target.value)}
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-muted">{label}</p>
                  <input
                    type="text"
                    value={hexInputs[key]}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    maxLength={7}
                    className={`mt-0.5 w-full rounded-lg border px-2 py-1 font-mono text-sm focus:outline-none ${
                      isValidHex(hexInputs[key])
                        ? "border-border bg-background text-foreground focus:border-accent/50"
                        : "border-red-300 bg-red-50 text-red-600"
                    }`}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex justify-end">
            <button
              onClick={fetchColors}
              className="text-sm text-muted underline-offset-2 transition-colors hover:text-foreground hover:underline"
            >
              Re-extract colors
            </button>
          </div>
        </>
      )}

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={back}
          className="text-sm text-muted transition-colors hover:text-foreground"
        >
          ← Back
        </button>
        <button
          onClick={handleNext}
          disabled={loading || !allValid}
          className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          Looks good → Next
        </button>
      </div>
    </div>
  );
}
