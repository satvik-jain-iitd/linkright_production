"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WizardData } from "../WizardShell";

interface BrandColors {
  brand_primary: string;
  brand_secondary: string;
  brand_tertiary: string | null;
  brand_quaternary: string | null;
}

interface CachedCompany {
  id: string;
  company_name: string;
  domain: string;
  logo_url: string | null;
  brand_primary: string;
  brand_secondary: string;
  brand_tertiary: string | null;
  brand_quaternary: string | null;
}

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

const REQUIRED_LABELS = [
  { key: "brand_primary" as const, label: "Primary" },
  { key: "brand_secondary" as const, label: "Secondary" },
];

const OPTIONAL_LABELS = [
  { key: "brand_tertiary" as const, label: "Tertiary" },
  { key: "brand_quaternary" as const, label: "Quaternary" },
];

const DEFAULT_COLORS: BrandColors = {
  brand_primary: "#1B2A4A",
  brand_secondary: "#2563EB",
  brand_tertiary: "#6B7280",
  brand_quaternary: "#FFFFFF",
};

function isValidHex(v: string | null): v is string {
  if (!v) return false;
  return /^#[0-9A-Fa-f]{6}$/.test(v);
}

function hexToRgbArr(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function relativeLuminance(hex: string): number {
  const [r, g, b] = hexToRgbArr(hex).map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastVsWhite(hex: string): number {
  const L = relativeLuminance(hex);
  return 1.05 / (L + 0.05);
}

function buildStepGradient(colorList: (string | null)[]): string {
  const valid = colorList.filter(isValidHex);
  if (valid.length === 0) return "transparent";
  const pct = 100 / valid.length;
  return (
    "linear-gradient(to right, " +
    valid
      .map(
        (c, i) =>
          `${c} ${Math.round(i * pct)}%, ${c} ${Math.round((i + 1) * pct)}%`
      )
      .join(", ") +
    ")"
  );
}

export function StepBrandColors({ data, update, next, back }: Props) {
  const existing = data.brand_colors;
  const [colors, setColors] = useState<BrandColors>(
    existing
      ? {
          brand_primary: existing.brand_primary,
          brand_secondary: existing.brand_secondary,
          brand_tertiary: existing.brand_tertiary ?? null,
          brand_quaternary: existing.brand_quaternary ?? null,
        }
      : { ...DEFAULT_COLORS }
  );
  const [hexInputs, setHexInputs] = useState<Record<string, string>>({
    brand_primary: existing?.brand_primary ?? DEFAULT_COLORS.brand_primary,
    brand_secondary: existing?.brand_secondary ?? DEFAULT_COLORS.brand_secondary,
    brand_tertiary: existing?.brand_tertiary ?? DEFAULT_COLORS.brand_tertiary!,
    brand_quaternary: existing?.brand_quaternary ?? DEFAULT_COLORS.brand_quaternary!,
  });
  const [lowContrastWarning, setLowContrastWarning] = useState(false);

  // Company search state
  const [searchQuery, setSearchQuery] = useState(data.target_company || "");
  const [searchResults, setSearchResults] = useState<CachedCompany[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ZIP/CSS upload state
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // BrandFetch lookup state
  const [domainQuery, setDomainQuery] = useState("");
  const [brandFetchStatus, setBrandFetchStatus] = useState<string | null>(null);
  const [brandFetchError, setBrandFetchError] = useState<string | null>(null);
  const [brandFetching, setBrandFetching] = useState(false);

  useEffect(() => {
    if (isValidHex(colors.brand_primary)) {
      setLowContrastWarning(contrastVsWhite(colors.brand_primary) < 4.5);
    }
  }, [colors.brand_primary]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const searchCachedColors = useCallback(async (q: string) => {
    if (q.length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const resp = await fetch(`/api/brand-colors/search?q=${encodeURIComponent(q)}`);
      if (!resp.ok) return;
      const data = await resp.json();
      setSearchResults(data.results || []);
      if ((data.results || []).length > 0) setShowDropdown(true);
    } catch {
      // Best-effort
    } finally {
      setSearching(false);
    }
  }, []);

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => searchCachedColors(value), 300);
  };

  const applyColors = (newColors: BrandColors, label?: string) => {
    setColors(newColors);
    setHexInputs({
      brand_primary: newColors.brand_primary,
      brand_secondary: newColors.brand_secondary,
      brand_tertiary: newColors.brand_tertiary ?? DEFAULT_COLORS.brand_tertiary!,
      brand_quaternary: newColors.brand_quaternary ?? DEFAULT_COLORS.brand_quaternary!,
    });
  };

  const applyFromCache = (company: CachedCompany) => {
    applyColors({
      brand_primary: company.brand_primary,
      brand_secondary: company.brand_secondary,
      brand_tertiary: company.brand_tertiary,
      brand_quaternary: company.brand_quaternary,
    });
    setShowDropdown(false);
  };

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

  const handleRemove = (key: "brand_tertiary" | "brand_quaternary") => {
    setColors((prev) => ({ ...prev, [key]: null }));
  };

  // ZIP/CSS file upload handler
  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setUploadStatus(null);
    setUploadError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const resp = await fetch("/api/brand-colors/extract", {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.error || "Upload failed");
      }
      const result = await resp.json();
      applyColors({
        brand_primary: result.brand_primary,
        brand_secondary: result.brand_secondary,
        brand_tertiary: result.brand_tertiary,
        brand_quaternary: result.brand_quaternary,
      });
      if (result.colors_found > 0) {
        setUploadStatus(`Found ${result.colors_found} color${result.colors_found === 1 ? "" : "s"} in file`);
      } else {
        setUploadStatus("Using defaults — no brand colors found in file");
      }
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
  };

  // BrandFetch domain lookup
  const handleBrandFetchLookup = async () => {
    if (!domainQuery.trim()) return;
    setBrandFetching(true);
    setBrandFetchStatus(null);
    setBrandFetchError(null);
    const q = domainQuery.trim().includes(".") ? domainQuery.trim() : `${domainQuery.trim()}.com`;
    try {
      const resp = await fetch(
        `/api/brand-colors/brandfetch?domain=${encodeURIComponent(q)}`
      );
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.error || "Lookup failed");
      }
      const result = await resp.json();
      if (!result.colors) {
        setBrandFetchError("BrandFetch couldn't find colors. Try uploading a CSS/HTML file above, or enter hex codes manually below.");
        return;
      }
      setColors((prev) => ({
        ...prev,
        brand_primary: result.brand_primary,
        brand_secondary: result.brand_secondary,
      }));
      setHexInputs((prev) => ({
        ...prev,
        brand_primary: result.brand_primary,
        brand_secondary: result.brand_secondary,
      }));
      setBrandFetchStatus(`Colors from ${q}`);
    } catch (e: unknown) {
      setBrandFetchError(e instanceof Error ? e.message : "Lookup failed");
    } finally {
      setBrandFetching(false);
    }
  };

  const handleNext = () => {
    update({ brand_colors: colors });
    // Persist user-verified colors to cache
    fetch("/api/brand-colors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: data.target_company,
        ...colors,
        source: "user_verified",
      }),
    }).catch(() => {});
    next();
  };

  const allValid =
    isValidHex(colors.brand_primary) &&
    isValidHex(colors.brand_secondary) &&
    (colors.brand_tertiary === null || isValidHex(colors.brand_tertiary)) &&
    (colors.brand_quaternary === null || isValidHex(colors.brand_quaternary));

  const colorList = [colors.brand_primary, colors.brand_secondary, colors.brand_tertiary, colors.brand_quaternary];

  const ContrastBadge = ({ hex }: { hex: string }) => {
    if (!isValidHex(hex)) return null;
    const ratio = contrastVsWhite(hex);
    const pass = ratio >= 4.5;
    return (
      <span
        className={`ml-1 rounded px-1.5 py-0.5 font-mono text-xs ${
          pass ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
        }`}
      >
        {ratio.toFixed(1)}:1 {pass ? "✓" : "✗"}
      </span>
    );
  };

  return (
    <div>
      <h2 className="text-2xl font-bold">Brand Colors</h2>
      <p className="mt-2 text-sm text-muted">
        Set brand colors for{" "}
        <span className="font-medium text-foreground">{data.target_company}</span>.
        Review and edit before generating your resume.
      </p>

      {/* Company search dropdown */}
      <div className="mt-6" ref={searchRef}>
        <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
          Search cached company colors
        </label>
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
            placeholder="Type a company name to find cached colors..."
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-accent/50 focus:outline-none"
          />
          {searching && (
            <div className="absolute right-3 top-2.5 h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
          )}
          {showDropdown && searchResults.length > 0 && (
            <div className="absolute z-50 mt-1 w-full overflow-hidden rounded-xl border border-border bg-surface shadow-lg">
              {searchResults.map((company) => (
                <button
                  key={company.id}
                  type="button"
                  onClick={() => applyFromCache(company)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-background"
                >
                  {company.logo_url ? (
                    <img
                      src={company.logo_url}
                      alt={company.company_name}
                      className="h-8 w-8 flex-shrink-0 rounded object-contain"
                    />
                  ) : (
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded bg-border text-xs font-bold text-muted">
                      {company.company_name.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{company.company_name}</p>
                    <p className="text-xs text-muted">{company.domain}</p>
                  </div>
                  <div className="flex gap-1">
                    {[company.brand_primary, company.brand_secondary, company.brand_tertiary, company.brand_quaternary]
                      .filter(Boolean)
                      .map((c, i) => (
                        <div
                          key={i}
                          className="h-5 w-5 rounded-full border border-border"
                          style={{ background: c! }}
                        />
                      ))}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {lowContrastWarning && (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Primary color has low contrast against white ({contrastVsWhite(colors.brand_primary).toFixed(1)}:1). Text may be hard to read — consider a darker shade.
        </div>
      )}

      {/* Identity horizon preview */}
      <div className="mt-8">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
          Preview — Identity Stripe
        </p>
        <div className="flex h-3 w-full overflow-hidden rounded-full shadow-sm">
          {colorList.filter(isValidHex).map((c, i) => (
            <div key={i} className="flex-1" style={{ background: c }} />
          ))}
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
          style={{ background: buildStepGradient(colorList) }}
        />
      </div>

      {/* Default palette label + color preview row */}
      <div className="mt-6">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
          Default professional colors — upload brand assets below for an accurate match
        </p>
        <div className="flex gap-2">
          {colorList.map((c, i) => (
            <div
              key={i}
              title={c ?? "none"}
              className="h-6 w-6 rounded border border-border shadow-sm"
              style={{ background: isValidHex(c) ? c : "#e5e7eb" }}
            />
          ))}
        </div>
      </div>

      {/* Required color pickers */}
      <div className="mt-4 grid grid-cols-2 gap-4">
        {REQUIRED_LABELS.map(({ key, label }) => (
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
              <p className="flex items-center text-xs font-medium text-muted">
                {label}
                <ContrastBadge hex={colors[key]} />
              </p>
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

      {/* Optional color pickers — removable */}
      <div className="mt-4 grid grid-cols-2 gap-4">
        {OPTIONAL_LABELS.map(({ key, label }) =>
          colors[key] === null ? null : (
            <div
              key={key}
              className="relative flex items-center gap-3 rounded-xl border border-border bg-surface p-4"
            >
              <button
                type="button"
                onClick={() => handleRemove(key)}
                className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-border text-xs text-muted transition-colors hover:bg-red-100 hover:text-red-600"
                title={`Remove ${label}`}
              >
                ×
              </button>
              <div className="relative flex-shrink-0">
                <div
                  className="h-10 w-10 cursor-pointer rounded-lg border border-border shadow-sm"
                  style={{ background: colors[key] as string }}
                />
                <input
                  type="color"
                  value={colors[key] as string}
                  onChange={(e) => handlePickerChange(key, e.target.value)}
                  className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                />
              </div>
              <div className="min-w-0 flex-1">
                <p className="flex items-center text-xs font-medium text-muted">
                  {label}
                  <ContrastBadge hex={colors[key] as string} />
                </p>
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
          )
        )}
      </div>

      {/* ZIP / CSS file upload */}
      <div className="mt-8">
        <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-muted">
          Upload brand assets (CSS/HTML file)
        </label>
        <div
          className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-surface px-6 py-6 text-center transition-colors hover:border-accent/40 hover:bg-background"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? (
            <div className="flex items-center gap-2 text-sm text-muted">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
              Extracting colors…
            </div>
          ) : (
            <>
              <svg
                className="h-6 w-6 text-muted"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.5}
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                />
              </svg>
              <p className="text-sm text-muted">
                Drop a CSS or HTML file here to extract brand colors (<span className="text-accent underline">click to browse</span>)
              </p>
              <p className="text-xs text-muted/60">Re-upload to try a different file &middot; .css, .html, .txt accepted</p>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".css,.html,.txt,.zip"
          className="hidden"
          onChange={handleFileInputChange}
        />
        {uploadStatus && (
          <p className="mt-2 text-xs font-medium text-green-700">{uploadStatus}</p>
        )}
        {uploadError && (
          <p className="mt-2 text-xs font-medium text-red-600">{uploadError}</p>
        )}
      </div>

      {/* BrandFetch domain lookup */}
      <div className="mt-6">
        <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-muted">
          Look up brand colors
        </label>
        <div className="flex gap-2">
          <div className="flex-1">
            <input
              type="text"
              value={domainQuery}
              onChange={(e) => setDomainQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleBrandFetchLookup()}
              placeholder="e.g. stripe.com"
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-accent/50 focus:outline-none"
            />
            <p className="mt-1 text-xs text-muted">Enter full domain (e.g. highlevel.com, stripe.com)</p>
          </div>
          <button
            type="button"
            onClick={handleBrandFetchLookup}
            disabled={brandFetching || !domainQuery.trim()}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/80 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {brandFetching ? (
              <span className="flex items-center gap-1.5">
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Looking up…
              </span>
            ) : (
              "Look up"
            )}
          </button>
        </div>
        {brandFetchStatus && (
          <p className="mt-2 text-xs font-medium text-green-700">{brandFetchStatus}</p>
        )}
        {brandFetchError && (
          <p className="mt-2 text-xs font-medium text-red-600">{brandFetchError}</p>
        )}
      </div>

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={back}
          className="text-sm text-muted transition-colors hover:text-foreground"
        >
          ← Back
        </button>
        <button
          onClick={handleNext}
          disabled={!allValid}
          className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          Looks good → Next
        </button>
      </div>
    </div>
  );
}
