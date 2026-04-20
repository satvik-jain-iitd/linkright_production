"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChatMessage, type Message } from "./ChatMessage";
import { ConfirmDenyButtons } from "./ConfirmDenyButtons";
import { StepLifeOS } from "./StepLifeOS";
import { ConfidenceProgressBar } from "@/components/ConfidenceProgressBar";
import { CareerGraph, type CytoElement } from "@/components/CareerGraph";
import {
  CareerOutlineView,
  type CareerOutlineData,
  type ParsedExperience,
  type ParsedEducation,
} from "@/components/onboarding/CareerOutlineView";
import { createClient as createBrowserSupabase } from "@/lib/supabase/client";

// ── Types ──────────────────────────────────────────────────────────────────

// [BYOK-REMOVED] type Step = 1 | 2 | 3 | 4 | 5;
type Step = 1 | 2 | 3 | 4;

const ROLE_OPTIONS = [
  "Product Manager",
  "Software Engineer",
  "Data Analyst",
  "UX Designer",
  "Marketing",
  "Finance",
  "Operations",
  "Other",
];

// [BYOK-REMOVED] const PROVIDER_MODEL_MAP: Record<string, string> = {
// [BYOK-REMOVED]   groq:        "llama-3.1-8b-instant",
// [BYOK-REMOVED]   cerebras:    "llama3.1-8b",
// [BYOK-REMOVED]   sambanova:   "Meta-Llama-3.1-8B-Instruct",
// [BYOK-REMOVED]   siliconflow: "Qwen/Qwen3-8B",
// [BYOK-REMOVED]   openrouter:  "meta-llama/llama-3.2-3b-instruct:free",
// [BYOK-REMOVED]   gemini:      "gemini-1.5-flash-8b",
// [BYOK-REMOVED] };

interface Education {
  institution: string;
  degree: string;
  year: string;
}

interface ConversationTurn {
  userAnswer: string;
  paraphrase: string;
  confirmed: boolean;
}

// ── Silent Enrichment Types + Helpers ────────────────────────────────────────

interface EnrichedChunkUpload {
  text: string;
  metadata: Record<string, unknown>;
}

function parseNarrationChunks(narration: string): { heading: string; text: string }[] {
  if (!narration || !/^## /m.test(narration)) return [];
  const chunks: { heading: string; text: string }[] = [];
  const roleSections = narration.split(/(?=^## )/m).filter((s) => s.trim());
  for (const roleSection of roleSections) {
    const lines = roleSection.trimStart().split("\n");
    const roleHeader = lines[0].trim();
    const parts = roleSection.split(/(?=^### )/m);
    const initiativeParts = parts.filter((p) => p.trimStart().startsWith("### "));
    if (initiativeParts.length === 0) {
      chunks.push({ heading: roleHeader, text: roleSection.trim() });
      continue;
    }
    for (const part of initiativeParts) {
      const partLines = part.trimStart().split("\n");
      const heading = partLines[0].trim().replace(/^### /, "");
      const body = partLines.slice(1).join("\n").trim();
      if (!body) continue;
      chunks.push({ heading, text: `${roleHeader}\n\n${partLines.join("\n").trim()}` });
    }
  }
  return chunks;
}

function extractChunkMeta(chunk: { heading: string; text: string }): Record<string, unknown> {
  const roleMatch = chunk.text.match(/^## ([^—–]+)[—–]\s*([^(\n]+)/m);
  return {
    company: roleMatch ? roleMatch[1].trim() : "",
    role: roleMatch ? roleMatch[2].trim() : "",
    initiative: chunk.heading,
  };
}

function buildCareerContext(experiences: ParsedExperience[]): string {
  if (!experiences?.length) return "";
  const current = experiences[0];
  const prev = experiences.slice(1, 3).map((e) => e.company).filter(Boolean);
  let ctx = `${current.role} at ${current.company}`;
  if (prev.length > 0) ctx += `, prev ${prev.join(", ")}`;
  return ctx;
}

async function enrichNarrationChunks(
  narration: string,
  careerContext: string
): Promise<EnrichedChunkUpload[]> {
  const chunks = parseNarrationChunks(narration);
  if (chunks.length === 0) return [];
  const results = await Promise.all(
    chunks.map(async (chunk) => {
      const base = extractChunkMeta(chunk);
      try {
        const res = await fetch("/api/onboarding/enrich-chunk", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ chunk_text: chunk.text, career_context: careerContext }),
        });
        const data = res.ok ? await res.json() : {};
        return { text: chunk.text, metadata: { ...base, ...data } };
      } catch {
        return { text: chunk.text, metadata: base };
      }
    })
  );
  return results;
}

// On Save: diff final chunks against pre-enriched state — re-enrich only changed chunks
async function buildFinalChunks(
  finalChunks: { heading: string; text: string }[],
  cached: EnrichedChunkUpload[],
  careerContext: string
): Promise<EnrichedChunkUpload[]> {
  const cachedByText = new Map(cached.map((c) => [c.text, c.metadata]));
  return Promise.all(
    finalChunks.map(async (chunk) => {
      const existing = cachedByText.get(chunk.text);
      if (existing) return { text: chunk.text, metadata: existing };
      const base = extractChunkMeta(chunk);
      try {
        const res = await fetch("/api/onboarding/enrich-chunk", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ chunk_text: chunk.text, career_context: careerContext }),
        });
        const data = res.ok ? await res.json() : {};
        return { text: chunk.text, metadata: { ...base, ...data } };
      } catch {
        return { text: chunk.text, metadata: base };
      }
    })
  );
}

// ── Step 1: Welcome + Target Roles ────────────────────────────────────────

function StepWelcome({
  selectedRoles,
  onRolesChange,
  onNext,
}: {
  selectedRoles: string[];
  onRolesChange: (roles: string[]) => void;
  onNext: () => void;
}) {
  const toggle = (role: string) => {
    onRolesChange(
      selectedRoles.includes(role)
        ? selectedRoles.filter((r) => r !== role)
        : [...selectedRoles, role]
    );
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Welcome to LinkRight
        </h1>
        <p className="mt-2 text-muted">
          What kind of roles are you targeting?
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        {ROLE_OPTIONS.map((role) => {
          const selected = selectedRoles.includes(role);
          return (
            <button
              key={role}
              onClick={() => toggle(role)}
              className={`rounded-full px-4 py-2 text-sm font-medium border transition-colors ${
                selected
                  ? "bg-primary-500 border-primary-500 text-white"
                  : "bg-surface border-border text-foreground hover:border-primary-400 hover:text-primary-600"
              }`}
            >
              {role}
            </button>
          );
        })}
      </div>

      <button
        onClick={onNext}
        disabled={selectedRoles.length === 0}
        className="w-full rounded-xl bg-primary-500 px-6 py-3 text-base font-semibold text-white hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Get Started
      </button>
    </div>
  );
}

// [BYOK-REMOVED] ── Step 2: API Key Setup (entire component removed) ─────────
// [BYOK-REMOVED] StepApiKey component was here — users no longer manage API keys.
// [BYOK-REMOVED] See git history for the full component if needed.

// ── Step 3: Career Basics Form ────────────────────────────────────────────

function StepCareerBasics({
  onNext,
  onSkip,
  onBack,
}: {
  onNext: () => void;
  onSkip: () => void;
  onBack?: () => void;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");

  // Pre-fill name and email from auth user metadata
  useEffect(() => {
    fetch("/api/onboarding/status")
      .then((r) => r.json())
      .then((data) => {
        if (data.user_name && !fullName) setFullName(data.user_name);
        if (data.user_email && !email) setEmail(data.user_email);
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [phone, setPhone] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [education, setEducation] = useState<Education[]>([
    { institution: "", degree: "", year: "" },
  ]);
  const [skillInput, setSkillInput] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [certifications, setCertifications] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Resume upload / paste state
  const [uploadMode, setUploadMode] = useState<"none" | "paste" | "file">("none");
  const [resumePasteText, setResumePasteText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState("");
  const [parsed, setParsed] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Wave 2 Sub-phase 2A: outline-view holds the structured companies tree.
  // Populated from parse-resume; narration streamed separately via narrate-career.
  const [outline, setOutline] = useState<CareerOutlineData | null>(null);
  const [streamingNarration, setStreamingNarration] = useState(false);

  // S04 design: show file metadata chip inside CareerOutlineView.
  const [fileMeta, setFileMeta] = useState<{ filename: string; sizeKB: number; parsedSec?: number } | null>(null);

  // Enriched chunk metadata — populated silently after narration stream completes.
  // Keys are ### heading strings (used for diff when user edits).
  const [enrichedChunks, setEnrichedChunks] = useState<EnrichedChunkUpload[]>([]);

  const startNarrationStream = async (experiences: ParsedExperience[], projects?: Array<{ title?: string; one_liner?: string; key_achievements?: string[] }>) => {
    if (!experiences || experiences.length === 0) return;
    setStreamingNarration(true);
    try {
      const resp = await fetch("/api/onboarding/narrate-career", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ experiences, projects: projects ?? [] }),
      });
      if (!resp.ok || !resp.body) return;
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        const text = accumulated;
        setOutline((prev) => prev ? { ...prev, career_summary_first_person: text } : null);
      }
      // Silently enrich initiative chunks while user reads — stored in state only
      if (accumulated.trim()) {
        const careerContext = buildCareerContext(experiences);
        enrichNarrationChunks(accumulated, careerContext).then(setEnrichedChunks).catch(() => {});
      }
    } catch (err) {
      console.warn("[narrate-career] Streaming failed:", err);
    } finally {
      setStreamingNarration(false);
    }
  };

  const handleSwapResume = () => {
    setOutline(null);
    setFileMeta(null);
    setParsed(false);
    setStreamingNarration(false);
    setUploadMode("file");
  };

  const applyParsed = (data: Record<string, unknown>) => {
    if (typeof data.full_name === "string" && data.full_name && !fullName) setFullName(data.full_name);
    // Never overwrite email — the signup email is the account-of-record.
    // If parsed resume contains a different email it stays as part of the resume content only.
    if (typeof data.phone === "string" && data.phone && !phone) setPhone(data.phone);
    if (typeof data.linkedin === "string" && data.linkedin && !linkedin) setLinkedin(data.linkedin);
    if (Array.isArray(data.education) && data.education.length > 0) {
      const edu = (data.education as Array<{ institution?: string; degree?: string; year?: string }>).map((e) => ({
        institution: e.institution ?? "",
        degree: e.degree ?? "",
        year: e.year ?? "",
      }));
      setEducation(edu.length > 0 ? edu : [{ institution: "", degree: "", year: "" }]);
    }
    if (Array.isArray(data.skills) && data.skills.length > 0) {
      setSkills(data.skills.filter((s): s is string => typeof s === "string"));
    }
    if (Array.isArray(data.certifications) && data.certifications.length > 0) {
      setCertifications((data.certifications as string[]).join("\n"));
    }

    // Build the structured outline for CareerOutlineView. If the parser didn't
    // emit a projects[] for an experience, we leave it empty — the view
    // falls back to raw bullets. If career_summary_first_person is empty,
    // CareerOutlineView just shows a placeholder — acceptable graceful degrade.
    const experiences: ParsedExperience[] = Array.isArray(data.experiences)
      ? (data.experiences as Array<Record<string, unknown>>).map((e) => ({
          company: String(e.company ?? ""),
          role: String(e.role ?? ""),
          start_date: typeof e.start_date === "string" ? e.start_date : "",
          end_date: typeof e.end_date === "string" ? e.end_date : "",
          bullets: Array.isArray(e.bullets) ? (e.bullets as string[]).filter((b) => typeof b === "string") : [],
          projects: Array.isArray(e.projects)
            ? (e.projects as Array<Record<string, unknown>>).map((p) => ({
                title: String(p.title ?? ""),
                one_liner: String(p.one_liner ?? ""),
                key_achievements: Array.isArray(p.key_achievements)
                  ? (p.key_achievements as string[]).filter((a) => typeof a === "string")
                  : [],
              }))
            : [],
        }))
      : [];

    const educationArr: ParsedEducation[] = Array.isArray(data.education)
      ? (data.education as Array<Record<string, unknown>>).map((e) => ({
          institution: String(e.institution ?? ""),
          degree: String(e.degree ?? ""),
          year: String(e.year ?? ""),
        }))
      : [];

    const topLevelProjects = Array.isArray(data.projects)
      ? (data.projects as Array<Record<string, unknown>>).map((p) => ({
          title: String(p.title ?? ""),
          one_liner: String(p.one_liner ?? ""),
          key_achievements: Array.isArray(p.key_achievements)
            ? (p.key_achievements as string[]).filter((a) => typeof a === "string")
            : [],
        }))
      : [];

    setOutline({
      experiences,
      education: educationArr,
      skills: Array.isArray(data.skills) ? (data.skills as string[]).filter((s) => typeof s === "string") : [],
      certifications: Array.isArray(data.certifications)
        ? (data.certifications as string[]).filter((c) => typeof c === "string")
        : [],
      projects: topLevelProjects,
      career_summary_first_person: "",
    });

    setParsed(true);
    setUploadMode("none");
  };

  const handleParsePaste = async () => {
    if (!resumePasteText.trim()) return;
    setParsing(true);
    setParseError("");
    try {
      const res = await fetch("/api/onboarding/parse-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: resumePasteText.trim(),
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();
      if (res.ok && data.parsed) {
        applyParsed(data.parsed);
        startNarrationStream(data.parsed.experiences as ParsedExperience[], data.parsed.projects as Array<{ title?: string; one_liner?: string; key_achievements?: string[] }> | undefined);
      } else {
        setParseError(data.error ?? "Could not parse resume. Please fill in manually.");
      }
    } catch {
      setParseError("Network error. Please try again.");
    } finally {
      setParsing(false);
    }
  };

  // PDF/DOCX file upload re-enabled via `unpdf` (replaces unreliable pdf-parse).
  const handleParseFile = async (file: File) => {
    if (file.size > 2 * 1024 * 1024) {
      setParseError("File too large (max 2 MB). Please paste your resume text instead.");
      setUploadMode("paste");
      return;
    }
    setParsing(true);
    setParseError("");
    const startedAt = performance.now();
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/onboarding/parse-resume", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok && data.parsed) {
        applyParsed(data.parsed);
        startNarrationStream(data.parsed.experiences as ParsedExperience[], data.parsed.projects as Array<{ title?: string; one_liner?: string; key_achievements?: string[] }> | undefined);
        setFileMeta({
          filename: file.name,
          sizeKB: file.size / 1024,
          parsedSec: (performance.now() - startedAt) / 1000,
        });
      } else {
        setParseError(data.error ?? "Could not parse file. Please paste your resume text instead.");
        setUploadMode("paste");
      }
    } catch {
      setParseError("Network error. Please try again.");
    } finally {
      setParsing(false);
    }
  };

  const addEducation = () => {
    setEducation([...education, { institution: "", degree: "", year: "" }]);
  };

  const updateEducation = (
    idx: number,
    field: keyof Education,
    value: string
  ) => {
    setEducation(
      education.map((e, i) => (i === idx ? { ...e, [field]: value } : e))
    );
  };

  const removeEducation = (idx: number) => {
    setEducation(education.filter((_, i) => i !== idx));
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "," || e.key === "Enter") {
      e.preventDefault();
      const trimmed = skillInput.trim().replace(/,$/, "");
      if (trimmed && !skills.includes(trimmed)) {
        setSkills([...skills, trimmed]);
      }
      setSkillInput("");
    }
  };

  const removeSkill = (skill: string) => {
    setSkills(skills.filter((s) => s !== skill));
  };

  const handleSave = async () => {
    // v2: full name no longer required — parsing pulls it from the resume;
    // user can edit from /dashboard/profile later if it's wrong.
    if (!parsed || !outline || outline.experiences.length === 0) {
      setError("Upload or paste a resume first, then continue.");
      return;
    }
    setSaving(true);
    setError("");

    const educationLines = education
      .filter((e) => e.institution || e.degree)
      .map((e) => `- ${e.degree} at ${e.institution}${e.year ? ` (${e.year})` : ""}`)
      .join("\n");

    const certLines = certifications
      .split("\n")
      .filter(Boolean)
      .map((c) => `- ${c.trim()}`)
      .join("\n");

    // F-18: the pasted resume usually already contains Name / Email / Phone /
    // LinkedIn / Skills / Education — prepending profileSummary verbatim
    // caused visible duplication ("Email: x@y.com" appeared in both the
    // summary AND the resume text). Dedupe per line: drop profile lines
    // whose value substring is already in the pasted resume.
    const resumeLower = resumePasteText.toLowerCase();
    const notAlreadyInResume = (line: string): boolean => {
      if (!resumePasteText) return true;
      const value = line.replace(/^[a-z ]+:\s*/i, "").trim();
      if (value.length < 4) return true; // too short to dedupe reliably
      // Multi-line blocks (Education, Certifications) — test first content line
      const firstValueLine = value.split("\n").find((l) => l.trim().length >= 4) ?? value;
      return !resumeLower.includes(firstValueLine.toLowerCase());
    };

    const profileSummary = [
      fullName && `Name: ${fullName}`,
      email && `Email: ${email}`,
      phone && `Phone: ${phone}`,
      linkedin && `LinkedIn: ${linkedin}`,
      educationLines && `Education:\n${educationLines}`,
      skills.length > 0 && `Skills: ${skills.join(", ")}`,
      certLines && `Certifications:\n${certLines}`,
    ]
      .filter((l): l is string => Boolean(l))
      .filter(notAlreadyInResume)
      .join("\n");

    // Use streaming narration (## Role / ### Initiative format) as career_text when available.
    // It already contains all career information in a semantically rich, chunkable format.
    // Fallback: flatten structured experiences + raw paste for users who skipped narration.
    const firstPersonText = (outline?.career_summary_first_person ?? "").trim();
    const structuredExperienceText = outline
      ? outline.experiences
          .map((exp) => {
            const header = [exp.company, exp.role, [exp.start_date, exp.end_date].filter(Boolean).join(" – ")]
              .filter(Boolean)
              .join(" · ");
            const projectLines = (exp.projects ?? [])
              .map((p) => {
                const bullets = p.key_achievements.map((a) => `  • ${a}`).join("\n");
                return `  ${p.title}: ${p.one_liner}${bullets ? "\n" + bullets : ""}`;
              })
              .join("\n");
            const bulletLines = exp.bullets.length > 0 && (exp.projects ?? []).length === 0
              ? exp.bullets.map((b) => `  • ${b}`).join("\n")
              : "";
            return [header, projectLines, bulletLines].filter(Boolean).join("\n");
          })
          .join("\n\n")
      : "";

    const careerText = firstPersonText
      ? firstPersonText
      : [structuredExperienceText, profileSummary, resumePasteText.trim()]
          .filter((chunk) => chunk && chunk.length > 0)
          .join("\n\n");

    try {
      const supabase = createBrowserSupabase();
      const { error: metaError } = await supabase.auth.updateUser({
        data: { full_name: fullName.trim() },
      });
      if (metaError) {
        console.warn("[onboarding] full_name metadata update failed:", metaError.message);
      }

      if (careerText.trim().length >= 200) {
        // Build final enriched chunks: diff against silently pre-enriched state.
        // Chunks whose text hasn't changed reuse cached metadata; changed or new
        // chunks are enriched synchronously here before upload.
        const finalChunks = parseNarrationChunks(careerText);
        let chunksToUpload: EnrichedChunkUpload[] | undefined;
        if (finalChunks.length > 0) {
          const careerContext = buildCareerContext(outline?.experiences ?? []);
          chunksToUpload = await buildFinalChunks(finalChunks, enrichedChunks, careerContext);
        }

        const uploadRes = await fetch("/api/career/upload", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            career_text: careerText,
            ...(chunksToUpload?.length ? { enriched_chunks: chunksToUpload } : {}),
          }),
        });
        if (!uploadRes.ok) {
          const data = await uploadRes.json().catch(() => ({}));
          setError(data.error ?? "Failed to save career details. Please try again.");
          return;
        }
      }

      onNext();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const inputClass =
    "w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary-500";

  // v2 design: Step 2 is the Screen 04 upload+outline UX. No more manual
  // fields — CareerOutlineView shows everything extractable from the resume.
  // If the parser missed something, the user edits it inline in the outline.
  return (
    <div className="space-y-6 max-w-[1200px] mx-auto">
      {!parsed && (
        <div className="max-w-2xl">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-accent">
            Step 1 · this is the only required input
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground">
            Drop your resume.
          </h1>
          <p className="mt-1 text-sm text-muted">
            PDF, DOCX, or paste the text. We read it, build your profile, and
            route you to matching roles.
          </p>
        </div>
      )}

      {/* Upload surface — shown until parsed */}
      {!parsed && uploadMode === "none" && (
        <div className="rounded-2xl border-2 border-dashed border-border bg-surface p-10 text-center">
          <div className="flex flex-wrap justify-center gap-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="rounded-full bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
            >
              Upload PDF / DOCX / TXT
            </button>
            <button
              onClick={() => setUploadMode("paste")}
              className="rounded-full border border-border bg-white px-6 py-3 text-sm font-semibold text-foreground transition hover:border-accent"
            >
              Paste resume text
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt,.text,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleParseFile(file);
                e.target.value = "";
              }}
            />
          </div>
          {parsing && (
            <p className="mt-4 text-sm text-accent animate-pulse">
              Parsing your resume…
            </p>
          )}
          {parseError && (
            <p className="mt-4 text-sm text-red-600">{parseError}</p>
          )}
        </div>
      )}

      {uploadMode === "paste" && !parsed && (
        <div className="rounded-2xl border border-accent/30 bg-accent/5 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-accent">
              Paste your resume text
            </p>
            <button
              onClick={() => { setUploadMode("none"); setParseError(""); }}
              className="text-xs text-muted hover:text-foreground transition-colors"
            >
              Cancel
            </button>
          </div>
          <textarea
            value={resumePasteText}
            onChange={(e) => setResumePasteText(e.target.value)}
            placeholder="Paste every section — plain text, as much as you have."
            rows={12}
            className="w-full rounded-lg border border-border bg-white px-3 py-2.5 text-sm text-foreground placeholder:text-muted resize-y focus:outline-none focus:ring-2 focus:ring-accent"
          />
          {parseError && (
            <p className="text-sm text-red-600">{parseError}</p>
          )}
          <button
            onClick={handleParsePaste}
            disabled={!resumePasteText.trim() || parsing}
            className="w-full rounded-full bg-cta px-4 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {parsing ? "Parsing…" : "Parse resume →"}
          </button>
        </div>
      )}

      {/* Parsed outline + first-person narration (CareerOutlineView) */}
      {parsed && outline && outline.experiences.length > 0 && (
        <CareerOutlineView
          data={outline}
          onChange={setOutline}
          fileMeta={fileMeta ?? undefined}
          onSwap={handleSwapResume}
          streamingNarration={streamingNarration}
        />
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {parsed && (
        <div className="flex items-center justify-between gap-3 border-t border-border pt-6">
          <p className="text-xs text-muted">
            We&apos;ll keep processing in the background. You can continue now.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-full bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save and continue →"}
            </button>
            <button
              onClick={onSkip}
              className="rounded-full border border-border bg-white px-4 py-3 text-sm font-medium text-muted transition hover:border-accent hover:text-accent"
            >
              Skip
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Step 4: TruthEngine Conversation ─────────────────────────────────────

function StepConversation({
  selectedRoles,
  // [BYOK-REMOVED] modelProvider,
  // [BYOK-REMOVED] modelId,
  // [BYOK-REMOVED] apiKey,
  onDone,
}: {
  selectedRoles: string[];
  // [BYOK-REMOVED] modelProvider: string;
  // [BYOK-REMOVED] modelId: string;
  // [BYOK-REMOVED] apiKey: string;
  onDone: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [nuggetCount, setNuggetCount] = useState(0);
  const [conversationHistory, setConversationHistory] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const [pendingConfirm, setPendingConfirm] = useState<{
    paraphrase: string;
    userAnswer: string;
  } | null>(null);
  const [waitingForConfirm, setWaitingForConfirm] = useState(false);
  const [showDoneConfirm, setShowDoneConfirm] = useState(false);
  const [finalStats, setFinalStats] = useState<{
    nugget_count: number;
    confidence: number;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const addMessage = (role: "system" | "user", content: string): Message => {
    const msg: Message = { id: crypto.randomUUID(), role, content };
    setMessages((prev) => [...prev, msg]);
    return msg;
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, pendingConfirm]);

  // Fetch initial question on mount
  useEffect(() => {
    let mounted = true;
    async function fetchFirstQuestion() {
      setSending(true);
      try {
        const res = await fetch("/api/onboarding/question", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target_roles: selectedRoles,
            conversation_history: [],
            confirmed_nuggets: [],
            // [BYOK-REMOVED] model_provider: modelProvider,
            // [BYOK-REMOVED] model_id: modelId,
            // [BYOK-REMOVED] api_key: apiKey,
          }),
        });
        const data = await res.json();
        if (mounted && data.question) {
          addMessage("system", data.question);
        } else if (mounted) {
          addMessage("system", "Tell me about your most recent work experience.");
        }
      } catch {
        if (mounted) {
          addMessage("system", "Tell me about your most recent work experience.");
        }
      } finally {
        if (mounted) setSending(false);
      }
    }
    fetchFirstQuestion();
    return () => { mounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchNextQuestion = async (
    updatedHistory: Array<{ role: string; content: string }>,
    confirmedCount: number
  ) => {
    setSending(true);
    try {
      const res = await fetch("/api/onboarding/question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_roles: selectedRoles,
          conversation_history: updatedHistory,
          confirmed_nuggets: Array(confirmedCount).fill(""),
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();
      if (data.question) {
        addMessage("system", data.question);
      }
    } catch {
      addMessage("system", "What other achievements or projects would you like to highlight?");
    } finally {
      setSending(false);
    }
  };

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || sending || waitingForConfirm) return;

    setInputText("");
    addMessage("user", text);

    const newHistory = [
      ...conversationHistory,
      { role: "user", content: text },
    ];
    setConversationHistory(newHistory);

    // Fetch paraphrase via confirm route with a preview (just use the question flow for paraphrase)
    setSending(true);
    setWaitingForConfirm(true);
    try {
      const res = await fetch("/api/onboarding/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_answer: text,
          action: "confirm",
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();

      if (res.ok && data.paraphrase) {
        addMessage("system", data.paraphrase);
        // We already confirmed and created the nugget in this flow
        const newCount = nuggetCount + 1;
        setNuggetCount(newCount);
        setWaitingForConfirm(false);

        const updatedHistory = [
          ...newHistory,
          { role: "assistant", content: data.paraphrase },
        ];
        setConversationHistory(updatedHistory);

        addMessage("system", "Saved! ✓");
        await fetchNextQuestion(updatedHistory, newCount);
      } else {
        // Paraphrase extraction failed — ask to rephrase
        addMessage("system", "I had trouble processing that. Could you rephrase or add more details?");
        setWaitingForConfirm(false);
        setSending(false);
      }
    } catch {
      addMessage("system", "Something went wrong. Please try again.");
      setWaitingForConfirm(false);
      setSending(false);
    }
  };

  const handleConfirm = async () => {
    if (!pendingConfirm) return;
    setSending(true);
    try {
      const res = await fetch("/api/onboarding/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_answer: pendingConfirm.userAnswer,
          action: "confirm",
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();

      if (res.ok) {
        const newCount = nuggetCount + 1;
        setNuggetCount(newCount);
        setPendingConfirm(null);
        setWaitingForConfirm(false);

        addMessage("system", "Saved! ✓");

        const updatedHistory = [
          ...conversationHistory,
          { role: "assistant", content: "Confirmed and saved." },
        ];
        setConversationHistory(updatedHistory);

        await fetchNextQuestion(updatedHistory, newCount);
      } else {
        addMessage("system", data.error ?? "Failed to save. Please try again.");
        setSending(false);
      }
    } catch {
      addMessage("system", "Failed to save. Please try again.");
      setSending(false);
    }
  };

  const handleCorrect = async (correctedText: string) => {
    if (!pendingConfirm) return;
    setSending(true);
    try {
      const res = await fetch("/api/onboarding/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_answer: pendingConfirm.userAnswer,
          action: "correct",
          correction: correctedText,
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();

      if (res.ok && data.updated_paraphrase) {
        addMessage("system", data.updated_paraphrase);
        setPendingConfirm({
          paraphrase: data.updated_paraphrase,
          userAnswer: correctedText,
        });
      } else {
        addMessage("system", "Could not update paraphrase. Please confirm or try again.");
      }
    } catch {
      addMessage("system", "Network error. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const handleDone = async () => {
    try {
      const res = await fetch("/api/onboarding/status");
      const data = await res.json();
      setFinalStats({
        nugget_count: data.nugget_count ?? nuggetCount,
        confidence: data.confidence ?? 0,
      });
      setShowDoneConfirm(true);
    } catch {
      setShowDoneConfirm(true);
      setFinalStats({ nugget_count: nuggetCount, confidence: 0 });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (showDoneConfirm && finalStats) {
    return (
      <div className="space-y-6 text-center">
        <div>
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary-100">
            <svg className="h-8 w-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-foreground">
            Great job!
          </h2>
          <p className="mt-2 text-muted">
            You&apos;ve captured{" "}
            <span className="font-semibold text-primary-600">
              {finalStats.nugget_count} career nuggets
            </span>
            .
          </p>
        </div>
        <button
          onClick={onDone}
          className="w-full rounded-xl bg-primary-500 px-6 py-3 text-base font-semibold text-white hover:bg-primary-600 transition-colors"
        >
          Create Your First Resume
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full space-y-4">
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Let&apos;s capture your experience
        </h1>
        <p className="mt-2 text-muted">
          I&apos;ll ask you questions to understand your career. Answer
          naturally — the more detail, the better.
        </p>
      </div>

      {/* Nugget counter */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted">
          <span className="font-semibold text-primary-600">{nuggetCount}</span>{" "}
          nuggets captured
        </span>
        <button
          onClick={handleDone}
          disabled={sending}
          className="text-sm text-muted hover:text-foreground underline transition-colors"
        >
          I&apos;m done
        </button>
      </div>

      {/* Chat window */}
      <div className="flex-1 min-h-[320px] max-h-[420px] overflow-y-auto rounded-xl border border-border bg-background p-4 space-y-1">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {pendingConfirm && (
          <div className="px-1">
            <ConfirmDenyButtons
              originalAnswer={pendingConfirm.userAnswer}
              onConfirm={handleConfirm}
              onCorrect={handleCorrect}
              disabled={sending}
            />
          </div>
        )}
        {sending && !waitingForConfirm && (
          <div className="flex justify-start mb-3">
            <div className="rounded-2xl rounded-tl-sm bg-surface border border-border px-4 py-3">
              <span className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "300ms" }} />
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 items-end">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            waitingForConfirm
              ? "Please confirm or correct the paraphrase above…"
              : "Type your answer… (Enter to send, Shift+Enter for newline)"
          }
          disabled={sending || waitingForConfirm}
          rows={2}
          className="flex-1 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-foreground placeholder:text-muted resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-60"
        />
        <button
          onClick={handleSend}
          disabled={!inputText.trim() || sending || waitingForConfirm}
          className="rounded-xl bg-primary-500 px-4 py-3 text-white hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ── Step 5: Summary / Completion screen ──────────────────────────────────

interface SummaryStats {
  nugget_count: number;
  confidence: number;
  atoms_saved?: number;  // fallback: raw atoms from TruthEngine, even if nuggets not yet processed
  companies?: string[];
  label?: "excellent" | "good" | "fair" | "insufficient";
}

interface GraphData {
  elements: CytoElement[];
  stats: {
    achievements: number;
    experiences: number;
    skills: number;
    companies: { name: string; role: string; count: number }[];
    topSkills: { name: string; count: number }[];
  };
}

function StepSummary({ initialStats, onBack }: { initialStats?: SummaryStats; onBack?: () => void }) {
  const router = useRouter();
  const [stats, setStats] = useState<SummaryStats | null>(initialStats ?? null);
  const [loading, setLoading] = useState(!initialStats);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [graphLoading, setGraphLoading] = useState(true);

  useEffect(() => {
    if (initialStats) return;
    let cancelled = false;
    let pollCount = 0;
    const MAX_POLLS = 12; // 60s max polling (12 × 5s)

    const fetchStats = () => {
      fetch("/api/onboarding/status")
        .then((r) => r.json())
        .then((data) => {
          if (cancelled) return;
          // data.confidence is an object { score, label, nugget_count } — not a number
          const score: number = data.confidence?.score ?? 0;
          const nuggetCount: number = data.confidence?.nugget_count ?? 0;
          // atoms_saved = raw atoms ingested by TruthEngine (always available even if nuggets not yet processed)
          const atomsSaved: number = data.atoms_saved ?? 0;
          const label: SummaryStats["label"] =
            score >= 90 ? "excellent" : score >= 75 ? "good" : score >= 60 ? "fair" : "insufficient";
          setStats({ nugget_count: nuggetCount, confidence: score, label, atoms_saved: atomsSaved });

          // Stop polling once we have nuggets OR atoms (whichever comes first)
          if (nuggetCount > 0 || atomsSaved > 0) cancelled = true;
        })
        .catch(() => {
          if (!cancelled) setStats({ nugget_count: 0, confidence: 0, label: "insufficient" });
        })
        .finally(() => setLoading(false));
    };

    // Fetch immediately on mount
    fetchStats();

    // Poll every 5s to pick up newly created nuggets (async atom→nugget pipeline)
    const interval = setInterval(() => {
      pollCount++;
      if (cancelled || pollCount >= MAX_POLLS) {
        clearInterval(interval);
        return;
      }
      fetchStats();
    }, 5_000);

    return () => { cancelled = true; clearInterval(interval); };
  }, [initialStats]);

  useEffect(() => {
    fetch("/api/profile/career-graph")
      .then((r) => r.json())
      .then((data) => setGraphData(data))
      .catch(() => setGraphData(null))
      .finally(() => setGraphLoading(false));
  }, []);

  const score = stats?.confidence ?? 0;
  const hasGraph = graphData && graphData.elements.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        {(stats?.nugget_count ?? 0) >= 1 && (
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary-100">
            <svg className="h-8 w-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
        <h2 className="text-2xl font-bold text-foreground">
          {(stats?.nugget_count ?? 0) >= 5
            ? "You\u0027re ready!"
            : (stats?.nugget_count ?? 0) >= 1
              ? "Almost there!"
              : "Let\u0027s add some experience first"}
        </h2>
        {hasGraph && (
          <p className="mt-1 text-sm text-muted">
            {graphData.stats.achievements} achievements · {(graphData.stats as { distinct_companies?: number; experiences: number }).distinct_companies ?? graphData.stats.experiences} companies · {graphData.stats.skills} skills
          </p>
        )}
        {onBack && (
          <button
            onClick={onBack}
            className="mt-3 text-xs text-muted hover:text-foreground underline underline-offset-2 transition-colors"
          >
            ← Add more achievements
          </button>
        )}
      </div>

      {/* Career Knowledge Graph */}
      {graphLoading ? (
        <div className="h-[420px] rounded-xl border border-border bg-surface flex items-center justify-center">
          <span className="flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "300ms" }} />
          </span>
        </div>
      ) : hasGraph ? (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted uppercase tracking-wide">Your Career Knowledge Graph</p>
          <CareerGraph elements={graphData.elements} />
        </div>
      ) : null}

      {/* Stats row */}
      {!loading && stats && (
        <div className="space-y-4 text-left">
          {/* If nuggets haven't been processed yet but atoms exist, show atoms count */}
          {stats.nugget_count === 0 && (stats.atoms_saved ?? 0) > 0 ? (
            <div className="rounded-xl border border-primary-200 bg-primary-50 px-4 py-3 space-y-1">
              <p className="text-sm font-semibold text-primary-700">
                {stats.atoms_saved} career highlights collected
              </p>
              <p className="text-xs text-primary-600">
                Your career data is being processed. Nugget scoring will appear shortly.
              </p>
            </div>
          ) : (
            <ConfidenceProgressBar
              score={score}
              label={stats.label}
              nuggetCount={stats.nugget_count}
            />
          )}

          {/* Company + skills breakdown side by side */}
          {hasGraph && (
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
                <p className="text-[10px] font-medium text-muted uppercase tracking-wide">By Company</p>
                {graphData.stats.companies.slice(0, 5).map((c) => (
                  <div key={`${c.name}:${c.role}`} className="flex items-center justify-between">
                    <span className="text-xs text-foreground truncate max-w-[120px]">{c.name}</span>
                    <span className="text-xs text-muted shrink-0">{c.count}</span>
                  </div>
                ))}
              </div>
              <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
                <p className="text-[10px] font-medium text-muted uppercase tracking-wide">Top Skills</p>
                {graphData.stats.topSkills.slice(0, 5).map((s, i) => (
                  <div key={s.name} className="flex items-center justify-between">
                    <span className="text-xs text-foreground truncate max-w-[120px]">
                      {i + 1}. {s.name}
                    </span>
                    <span className="text-xs text-muted shrink-0">{s.count}×</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {score < 60 && (
            <div className="rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-3">
              <p className="text-sm text-yellow-800">
                Consider adding more details for better resume quality. You can always come back and add more experience.
              </p>
            </div>
          )}
        </div>
      )}

      {/* CTA buttons — route into the Wave 2 journey: Profile → Preferences → Find. */}
      <div className="space-y-3">
        <Link
          href="/onboarding/profile"
          className="block w-full rounded-xl bg-primary-500 px-6 py-3 text-center text-base font-semibold text-white hover:bg-primary-600 transition-colors"
        >
          Review your profile
        </Link>
        <Link
          href="/dashboard"
          className="block w-full rounded-xl border border-border px-6 py-3 text-center text-base font-medium text-muted hover:bg-surface-hover transition-colors"
        >
          Skip to dashboard
        </Link>
      </div>
    </div>
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────

// [BYOK-REMOVED] const STEP_LABELS = ["Roles", "API Key", "Profile", "TruthEngine", "Summary"];
const STEP_LABELS = ["Roles", "Profile", "Experience", "Summary"];

function ProgressBar({ step, onStepClick }: { step: Step; onStepClick?: (s: Step) => void }) {
  const totalSteps = 4;
  const currentIndex = Math.min(step - 1, totalSteps - 1);

  return (
    <div className="mb-10">
      <div className="flex justify-between mb-2">
        {STEP_LABELS.map((label, idx) => {
          const isCompleted = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          return (
            <button
              key={label}
              type="button"
              // F-14: previously `disabled={!isCompleted}` made the CURRENT step
              // render as disabled in the a11y tree (the user is on it — it
              // should be marked with aria-current, not disabled). Only unvisited
              // future steps are disabled now.
              disabled={!isCompleted && !isCurrent}
              aria-current={isCurrent ? "step" : undefined}
              onClick={() => isCompleted && onStepClick?.((idx + 1) as Step)}
              className={`text-xs font-medium transition-colors ${
                isCurrent
                  ? "text-primary-600 font-semibold"
                  : isCompleted
                    ? "text-primary-600 hover:text-primary-800 cursor-pointer underline underline-offset-2"
                    : "text-muted cursor-default"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
      <div className="h-1.5 w-full rounded-full bg-border">
        <div
          className="h-1.5 rounded-full bg-primary-500 transition-all duration-300"
          style={{ width: `${(currentIndex / (totalSteps - 1)) * 100}%` }}
        />
      </div>
    </div>
  );
}

// ── Main OnboardingFlow ───────────────────────────────────────────────────

const ROLES_KEY = "lr_selected_roles";

export function OnboardingFlow() {
  // v2 design: first screen post-signup is upload (step 2 = StepCareerBasics),
  // NOT role selection. Step 1 (StepWelcome) is deprecated and skipped for
  // fresh users. Roles can be picked later on the preferences screen.
  const [step, setStep] = useState<Step>(2);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);

  // Restore target roles from localStorage + optionally advance past
  // upload if the user already has career data. Status fetch is
  // non-blocking — UI renders step 2 (upload) immediately, no spinner.
  useEffect(() => {
    const saved = localStorage.getItem(ROLES_KEY);
    if (saved) {
      try { setSelectedRoles(JSON.parse(saved)); } catch { /* ignore */ }
    }

    fetch("/api/onboarding/status")
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data) return;
        if (data.session_complete) {
          setStep(4);
        } else if (data.session_started) {
          setStep(3);
        } else if (data.has_career_data) {
          setStep(3);
        }
        // else: stay on step 2 (upload)
      })
      .catch(() => { /* keep step 2 */ });
  }, []);

  const handleRolesChange = (roles: string[]) => {
    setSelectedRoles(roles);
    localStorage.setItem(ROLES_KEY, JSON.stringify(roles));
    // Persist to database — fire-and-forget (localStorage is fallback for offline)
    fetch("/api/user/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_roles: roles }),
    }).catch(() => { /* silent — localStorage has the data */ });
  };

  return (
    <div>
      {/* ProgressBar removed — CareerOutlineView + Screen-05 page render
          their own step indicators aligned to the v2 design (4-step journey:
          Resume · Profile · Preferences · First match). */}

      {step === 1 && (
        <StepWelcome
          selectedRoles={selectedRoles}
          onRolesChange={handleRolesChange}
          onNext={() => setStep(2)}
        />
      )}

      {step === 2 && (
        <StepCareerBasics
          onNext={() => {
            // v2: after upload + save, route to /onboarding/profile (Screen 05)
            if (typeof window !== "undefined") {
              window.location.href = "/onboarding/profile";
            }
          }}
          onSkip={() => {
            if (typeof window !== "undefined") {
              window.location.href = "/onboarding/profile";
            }
          }}
        />
      )}

      {step === 3 && (
        <StepLifeOS onDone={() => setStep(4)} onBack={() => setStep(2)} />
      )}

      {step === 4 && <StepSummary onBack={() => setStep(3)} />}
    </div>
  );
}
