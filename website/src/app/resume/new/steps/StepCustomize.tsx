"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WizardData } from "../WizardShell";

/* ─── Brand Colors types ─────────────────────────────────────────────────── */

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

/* ─── Enrich types ───────────────────────────────────────────────────────── */

interface GapQuestion {
  req_id: string;
  question: string;
}

interface AnswerStatus {
  status: "idle" | "saving" | "added" | "duplicate" | "error";
  message?: string;
}

interface ScoredChunk {
  chunk: string;
  chunk_index: number;
  score: number;
}

/* ─── Props ──────────────────────────────────────────────────────────────── */

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

/* ─── Brand Colors constants & helpers ───────────────────────────────────── */

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

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  StepCustomize — Brand Colors + Enrich Q&A combined                       */
/* ═══════════════════════════════════════════════════════════════════════════ */

export function StepCustomize({ data, update, next, back }: Props) {
  /* ─── Brand Colors state ──────────────────────────────────────────────── */

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
  const [colorSearching, setColorSearching] = useState(false);
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

  /* ─── Enrich state ────────────────────────────────────────────────────── */

  const hasGaps = (data.jd_analysis?.gaps?.length ?? 0) > 0;

  // Gap-filling mode
  const [gapQuestions, setGapQuestions] = useState<GapQuestion[]>([]);
  const [gapAnswers, setGapAnswers] = useState<Record<string, string>>({});
  const [answerStatuses, setAnswerStatuses] = useState<Record<string, AnswerStatus>>({});
  const [loadingGapQuestions, setLoadingGapQuestions] = useState(hasGaps);
  const [gapQuestionsError, setGapQuestionsError] = useState<string | null>(null);
  const [toastMessages, setToastMessages] = useState<string[]>([]);

  // Standard enrich mode
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(!hasGaps);
  const [error, setError] = useState<string | null>(null);
  const [autoFilled, setAutoFilled] = useState<Set<number>>(new Set());
  const [searching, setSearching] = useState<Set<number>>(new Set());
  const [scoredChunks, setScoredChunks] = useState<Record<number, ScoredChunk[]>>({});
  const [expandedVectors, setExpandedVectors] = useState<Set<number>>(new Set());

  const enrichStarted = useRef(false);
  const gapStarted = useRef(false);

  /* ─── Brand Colors effects ────────────────────────────────────────────── */

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

  /* ─── Brand Colors handlers ───────────────────────────────────────────── */

  const searchCachedColors = useCallback(async (q: string) => {
    if (q.length < 2) {
      setSearchResults([]);
      return;
    }
    setColorSearching(true);
    try {
      const resp = await fetch(`/api/brand-colors/search?q=${encodeURIComponent(q)}`);
      if (!resp.ok) return;
      const data = await resp.json();
      setSearchResults(data.results || []);
      if ((data.results || []).length > 0) setShowDropdown(true);
    } catch {
      // Best-effort
    } finally {
      setColorSearching(false);
    }
  }, []);

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => searchCachedColors(value), 300);
  };

  const applyColors = (newColors: BrandColors) => {
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
        setBrandFetchError("Couldn't find colors for this domain. Try entering the full domain like 'company.com', or upload a CSS file instead.");
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

  /* ─── Enrich effects ──────────────────────────────────────────────────── */

  // Gap questions fetch
  useEffect(() => {
    if (!hasGaps || gapStarted.current) return;
    gapStarted.current = true;

    const gaps = data.jd_analysis!.gaps;
    fetch("/api/enrich/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gaps,
        model_provider: data.model_provider,
        model_id: data.model_id,
        api_key: data.api_key,
      }),
    })
      .then((r) => r.json())
      .then((result) => {
        if (result.questions) setGapQuestions(result.questions);
        else setGapQuestionsError("Could not generate gap questions");
      })
      .catch(() => setGapQuestionsError("Network error generating gap questions"))
      .finally(() => setLoadingGapQuestions(false));
  }, [hasGaps]);

  // Standard Q&A fetch
  useEffect(() => {
    if (enrichStarted.current) return;
    enrichStarted.current = true;

    if (data.qa_answers && data.qa_answers.length > 0) {
      const qs = data.qa_answers.map((qa) => qa.question);
      const ans: Record<number, string> = {};
      data.qa_answers.forEach((qa, i) => { ans[i] = qa.answer; });
      setQuestions(qs);
      setAnswers(ans);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    const generate = async () => {
      try {
        const resp = await fetch("/api/resume/questions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            jd_text: data.jd_text,
            career_text: data.career_text,
            model_provider: data.model_provider,
            model_id: data.model_id,
            api_key: data.api_key,
          }),
          signal: controller.signal,
        });
        const result = await resp.json();
        if (!resp.ok) {
          setError(result.error || "Failed to generate questions");
          return;
        }
        const qs = result.questions || [];
        setQuestions(qs);
        if (qs.length > 0) autoFillFromProfile(qs);
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") {
          setError("Question generation timed out — you can skip this step");
        } else {
          setError("Network error — please try again");
        }
      } finally {
        clearTimeout(timeout);
        setLoading(false);
      }
    };

    generate();
  }, []);

  /* ─── Enrich handlers ─────────────────────────────────────────────────── */

  const autoFillFromProfile = async (qs: string[]) => {
    setSearching(new Set(qs.map((_, i) => i)));
    try {
      const results = await Promise.allSettled(
        qs.map((q) =>
          fetch("/api/career/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: q, include_scores: true }),
          }).then((r) => r.json())
        )
      );
      const newAnswers: Record<number, string> = {};
      const filled = new Set<number>();
      const newScored: Record<number, ScoredChunk[]> = {};
      results.forEach((r, i) => {
        if (r.status === "fulfilled" && r.value.chunks?.length > 0) {
          newAnswers[i] = r.value.chunks.join("\n\n");
          filled.add(i);
          if (r.value.scored?.length > 0) {
            newScored[i] = r.value.scored;
          }
        }
      });
      setAnswers((prev) => ({ ...prev, ...newAnswers }));
      setAutoFilled(filled);
      setScoredChunks((prev) => ({ ...prev, ...newScored }));
    } catch {
      // Best-effort
    } finally {
      setSearching(new Set());
    }
  };

  const showToast = (msg: string) => {
    setToastMessages((prev) => [...prev, msg]);
    setTimeout(() => {
      setToastMessages((prev) => prev.filter((m) => m !== msg));
    }, 4000);
  };

  const submitGapAnswer = async (reqId: string) => {
    const answer = gapAnswers[reqId]?.trim();
    if (!answer || answer.length < 10) return;

    setAnswerStatuses((prev) => ({ ...prev, [reqId]: { status: "saving" } }));
    try {
      const resp = await fetch("/api/enrich/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answer,
          model_provider: data.model_provider,
          model_id: data.model_id,
          api_key: data.api_key,
        }),
      });
      const result = await resp.json();
      if (!resp.ok) {
        setAnswerStatuses((prev) => ({
          ...prev,
          [reqId]: { status: "error", message: result.error || "Failed to save" },
        }));
        return;
      }
      setAnswerStatuses((prev) => ({
        ...prev,
        [reqId]: { status: result.status, message: result.message },
      }));
      if (result.status === "added") {
        showToast(`Career profile enriched: ${result.summary || "New experience added"}`);
      } else if (result.status === "duplicate") {
        showToast("Already in your profile — skipped.");
      }
    } catch {
      setAnswerStatuses((prev) => ({
        ...prev,
        [reqId]: { status: "error", message: "Network error" },
      }));
    }
  };

  /* ─── Combined Continue handler ───────────────────────────────────────── */

  const colorsValid =
    isValidHex(colors.brand_primary) &&
    isValidHex(colors.brand_secondary) &&
    (colors.brand_tertiary === null || isValidHex(colors.brand_tertiary)) &&
    (colors.brand_quaternary === null || isValidHex(colors.brand_quaternary));

  const handleContinue = () => {
    // Collect Q&A answers
    const qa_answers = questions
      .map((q, i) => ({
        question: q,
        answer: (answers[i] || "").trim(),
      }))
      .filter((qa) => qa.answer.length > 0);

    // Save both brand_colors + qa_answers in a single update
    update({ brand_colors: colors, qa_answers });

    // Persist user-verified colors to cache (fire-and-forget)
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

  const handleSkip = () => {
    // Save brand colors but skip Q&A
    update({ brand_colors: colors, qa_answers: [] });

    // Persist colors cache
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

  /* ─── Derived values ──────────────────────────────────────────────────── */

  const colorList = [colors.brand_primary, colors.brand_secondary, colors.brand_tertiary, colors.brand_quaternary];
  const answeredCount = Object.values(answers).filter((a) => a.trim().length > 0).length;

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
        {ratio.toFixed(1)}:1 {pass ? "\u2713" : "\u2717"}
      </span>
    );
  };

  /* ═══════════════════════════════════════════════════════════════════════ */
  /*  Render                                                                */
  /* ═══════════════════════════════════════════════════════════════════════ */

  return (
    <div>
      {/* Toasts */}
      {toastMessages.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
          {toastMessages.map((msg, i) => (
            <div
              key={i}
              className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800 shadow-lg"
            >
              {"\u2713"} {msg}
            </div>
          ))}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/*  SECTION 1 — Brand Colors                                          */}
      {/* ════════════════════════════════════════════════════════════════════ */}

      <h2 className="text-2xl font-bold">Customize</h2>
      <p className="mt-2 text-sm text-muted">
        Set brand colors and answer profile questions{data.target_company ? <> for{" "}<span className="font-medium text-foreground">{data.target_company}</span></> : ""}.
      </p>

      <div className="mt-8 rounded-2xl border border-border bg-surface/50 p-6">
        <h3 className="text-lg font-semibold">Brand Colors</h3>
        <p className="mt-1 text-sm text-muted">
          Review and edit before generating your resume.
        </p>

        {/* Company search dropdown */}
        <div className="mt-6" ref={searchRef}>
          <label htmlFor="company-color-search" className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
            Search cached company colors
          </label>
          <div className="relative">
            <input
              id="company-color-search"
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
              placeholder="Type a company name to find cached colors..."
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-accent/50 focus:outline-none"
            />
            {colorSearching && (
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
                  aria-label={`${label} color picker`}
                  className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                />
              </div>
              <div className="min-w-0 flex-1">
                <label htmlFor={`hex-${key}`} className="flex items-center text-xs font-medium text-muted">
                  {label}
                  <ContrastBadge hex={colors[key]} />
                </label>
                <input
                  id={`hex-${key}`}
                  type="text"
                  value={hexInputs[key]}
                  onChange={(e) => handleColorChange(key, e.target.value)}
                  maxLength={7}
                  aria-required="true"
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
                  {"\u00D7"}
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
                    aria-label={`${label} color picker`}
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <label htmlFor={`hex-${key}`} className="flex items-center text-xs font-medium text-muted">
                    {label}
                    <ContrastBadge hex={colors[key] as string} />
                  </label>
                  <input
                    id={`hex-${key}`}
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
          <label htmlFor="brand-file-upload" className="mb-2 block text-xs font-semibold uppercase tracking-wide text-muted">
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
                Extracting colors...
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
                  Drop CSS/HTML file here or <span className="text-accent underline">click to browse</span>
                </p>
                <p className="text-xs text-muted/60">.css, .html, .txt, .zip accepted</p>
              </>
            )}
          </div>
          <input
            id="brand-file-upload"
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
          <label htmlFor="brandfetch-domain" className="mb-2 block text-xs font-semibold uppercase tracking-wide text-muted">
            Look up brand colors
          </label>
          <div className="flex gap-2">
            <div className="flex-1">
              <input
                id="brandfetch-domain"
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
              aria-disabled={brandFetching || !domainQuery.trim()}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/80 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {brandFetching ? (
                <span className="flex items-center gap-1.5">
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Looking up...
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
      </div>

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/*  DIVIDER                                                           */}
      {/* ════════════════════════════════════════════════════════════════════ */}

      <div className="my-10 border-t border-border" />

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/*  SECTION 2 — Resume Q&A                                            */}
      {/* ════════════════════════════════════════════════════════════════════ */}

      <div className="rounded-2xl border border-border bg-surface/50 p-6">
        <h3 className="text-lg font-semibold">Resume Q&A</h3>
        <p className="mt-1 text-sm text-muted">
          {hasGaps
            ? "Answer gap-filling questions to strengthen your match, then review auto-generated bullets."
            : "Answer these questions to help the AI write stronger, more targeted bullets."}
        </p>

        {/* ── Gap-filling section ─────────────────────────────────────────── */}
        {hasGaps && (
          <div className="mt-6">
            <div className="mb-4 flex items-center gap-2">
              <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
                {data.jd_analysis!.gaps.length} gaps detected
              </span>
              <span className="text-sm text-muted">
                These requirements were not found in your career profile.
              </span>
            </div>

            {loadingGapQuestions ? (
              <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-5">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
                <span className="text-sm text-muted">Generating gap-filling questions...</span>
              </div>
            ) : gapQuestionsError ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                {gapQuestionsError}
              </div>
            ) : (
              <div className="space-y-4">
                {gapQuestions.map((gq) => {
                  const status = answerStatuses[gq.req_id];
                  const gap = data.jd_analysis!.gaps.find((g) => g.req_id === gq.req_id);
                  const isSaved = status?.status === "added" || status?.status === "duplicate";
                  return (
                    <div
                      key={gq.req_id}
                      className={`rounded-xl border p-5 transition-colors ${
                        isSaved ? "border-green-200 bg-green-50" : "border-border bg-surface"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          {gap && (
                            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted">
                              <span className="rounded bg-red-100 px-1.5 py-0.5 text-red-600">GAP</span>
                              {gap.text}
                            </p>
                          )}
                          <label htmlFor={`gap-answer-${gq.req_id}`} className="text-sm font-medium text-foreground">
                            {gq.question}
                          </label>
                        </div>
                        {isSaved && (
                          <span className="flex-shrink-0 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
                            {status?.status === "duplicate" ? "Already captured" : "Saved"}
                          </span>
                        )}
                      </div>
                      {!isSaved && (
                        <>
                          <textarea
                            id={`gap-answer-${gq.req_id}`}
                            value={gapAnswers[gq.req_id] || ""}
                            onChange={(e) =>
                              setGapAnswers((prev) => ({ ...prev, [gq.req_id]: e.target.value }))
                            }
                            placeholder="Describe a specific example with measurable outcomes..."
                            className="mt-3 w-full resize-none rounded-lg border border-border bg-background p-3 text-sm text-foreground placeholder-muted focus:border-accent/50 focus:outline-none"
                            rows={3}
                            disabled={status?.status === "saving"}
                            aria-disabled={status?.status === "saving"}
                            aria-required="true"
                          />
                          <div className="mt-2 flex items-center justify-between">
                            {status?.status === "error" && (
                              <p className="text-xs text-red-600">{status.message}</p>
                            )}
                            <div className="ml-auto">
                              <button
                                onClick={() => submitGapAnswer(gq.req_id)}
                                disabled={
                                  status?.status === "saving" ||
                                  !gapAnswers[gq.req_id]?.trim() ||
                                  (gapAnswers[gq.req_id]?.trim().length ?? 0) < 10
                                }
                                aria-disabled={
                                  status?.status === "saving" ||
                                  !gapAnswers[gq.req_id]?.trim() ||
                                  (gapAnswers[gq.req_id]?.trim().length ?? 0) < 10
                                }
                                className="rounded-lg bg-accent px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
                              >
                                {status?.status === "saving" ? "Saving..." : "Save to Profile"}
                              </button>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ── Standard Q&A section ────────────────────────────────────────── */}
        <div className={hasGaps ? "mt-8 border-t border-border pt-8" : "mt-6"}>
          {hasGaps && (
            <h4 className="mb-4 text-base font-semibold">Additional Profile Questions</h4>
          )}

          {loading ? (
            <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-5">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
              <span className="text-sm text-muted">Generating profile questions...</span>
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-5">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          ) : (
            <div className="space-y-6">
              {questions.map((q, i) => (
                <div key={i} className="rounded-xl border border-border bg-surface p-5">
                  <div className="flex items-center justify-between">
                    <label htmlFor={`qa-answer-${i}`} className="text-sm font-medium text-foreground">
                      {i + 1}. {q}
                    </label>
                    {searching.has(i) && (
                      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
                    )}
                    {autoFilled.has(i) && !searching.has(i) && (
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                          Auto-filled from profile
                        </span>
                        {scoredChunks[i] && (
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedVectors((prev) => {
                                const n = new Set(prev);
                                n.has(i) ? n.delete(i) : n.add(i);
                                return n;
                              })
                            }
                            className="rounded-full border border-border bg-background px-2 py-0.5 text-xs text-muted transition-colors hover:border-accent/40 hover:text-accent"
                          >
                            {expandedVectors.has(i) ? "Hide sources" : `View sources (${scoredChunks[i].length})`}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                  <textarea
                    id={`qa-answer-${i}`}
                    value={answers[i] || ""}
                    onChange={(e) => {
                      setAnswers((prev) => ({ ...prev, [i]: e.target.value }));
                      setAutoFilled((prev) => {
                        const n = new Set(prev);
                        n.delete(i);
                        return n;
                      });
                    }}
                    placeholder={searching.has(i) ? "Searching your profile..." : "Your answer (optional)..."}
                    className="mt-3 w-full resize-none rounded-lg border border-border bg-background p-3 text-sm text-foreground placeholder-muted transition-colors focus:border-accent/50 focus:outline-none"
                    rows={3}
                  />

                  {/* Contributing vectors panel */}
                  {expandedVectors.has(i) && scoredChunks[i] && (
                    <div className="mt-3 overflow-hidden rounded-lg border border-border">
                      <div className="border-b border-border bg-background px-3 py-2">
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                          Contributing career chunks
                        </p>
                      </div>
                      <div className="divide-y divide-border">
                        {scoredChunks[i].map((sc, j) => (
                          <div key={j} className="px-3 py-2.5">
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className="text-xs text-muted">Chunk #{sc.chunk_index}</span>
                              <span
                                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                                  sc.score >= 70
                                    ? "bg-green-100 text-green-700"
                                    : sc.score >= 40
                                    ? "bg-amber-100 text-amber-700"
                                    : "bg-red-100 text-red-600"
                                }`}
                              >
                                {sc.score}% match
                              </span>
                            </div>
                            <p className="text-xs text-muted line-clamp-3">{sc.chunk}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {!hasGaps && questions.length > 0 && (
          <p className="mt-4 text-xs text-muted">
            {answeredCount}/{questions.length} answered
          </p>
        )}
      </div>

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/*  Footer — Back / Skip / Continue                                   */}
      {/* ════════════════════════════════════════════════════════════════════ */}

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={back}
          className="text-sm text-muted transition-colors hover:text-foreground"
        >
          &larr; Back
        </button>
        <div className="flex gap-3">
          <button
            onClick={handleSkip}
            className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
          >
            Skip Q&A
          </button>
          <button
            onClick={handleContinue}
            disabled={!colorsValid}
            aria-disabled={!colorsValid}
            className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
          >
            Generate Resume
          </button>
        </div>
      </div>
    </div>
  );
}
