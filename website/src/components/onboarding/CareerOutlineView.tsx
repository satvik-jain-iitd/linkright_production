"use client";

// Wave 2 / Screen 04 — Resume upload review + first-person narration.
// Design handoff: specs/design-handoff-2026-04-18/ → screens-build.jsx Screen04.
//
// Shape:
//   ┌─ step indicator (1 Resume · 2 Profile · 3 Preferences · 4 First match) ─┐
//   │ eyebrow + headline + sub                                                │
//   │ [file-chip: filename · size · parsed in Ns]   [swap resume]             │
//   │ ┌──────────── OUTLINE ────────────┬──────── YOUR STORY ─────────────┐   │
//   │ │ Experience (company+role+chips) │ Paragraph per role, border-left │   │
//   │ │ Education · Skills              │ bold lead, editable via toggle  │   │
//   │ └─────────────────────────────────┴─────────────────────────────────┘   │
//   │ [explainer]                                    [Save and continue →]    │
//   └──────────────────────────────────────────────────────────────────────────┘

import { useState, useMemo } from "react";

export interface ParsedProject {
  title: string;
  one_liner: string;
  key_achievements: string[];
}

export interface ParsedExperience {
  company: string;
  role: string;
  start_date?: string;
  end_date?: string;
  bullets: string[];
  projects?: ParsedProject[];
}

export interface ParsedEducation {
  institution: string;
  degree: string;
  year: string;
}

export interface IndependentProject {
  title: string;
  one_liner: string;
  key_achievements: string[];
}

export interface CareerOutlineData {
  experiences: ParsedExperience[];
  education: ParsedEducation[];
  skills: string[];
  certifications: string[];
  career_summary_first_person: string;
  projects?: IndependentProject[];
}

export interface FileMeta {
  filename: string;
  sizeKB: number;
  parsedSec?: number;
}

interface Props {
  data: CareerOutlineData;
  onChange: (data: CareerOutlineData) => void;
  fileMeta?: FileMeta;
  onSwap?: () => void;
  onContinue?: () => void;
  onSkip?: () => void;
  continueLabel?: string;
  busy?: boolean;
  streamingNarration?: boolean;
}

const STEPS = [
  { n: 1, label: "Resume" },
  { n: 2, label: "Profile" },
  { n: 3, label: "Preferences" },
  { n: 4, label: "First match" },
] as const;

export function CareerOutlineView({
  data,
  onChange,
  fileMeta,
  onSwap,
  onContinue,
  onSkip,
  continueLabel = "Save and continue",
  busy,
  streamingNarration = false,
}: Props) {
  const narration = data.career_summary_first_person ?? "";
  const [editBuffer, setEditBuffer] = useState<string | null>(null);
  const editing = editBuffer !== null;

  const paragraphs = useMemo(
    () =>
      narration
        .split(/\n{2,}/)
        .map((p) => p.trim())
        .filter(Boolean),
    [narration],
  );

  function patchExperience(idx: number, patch: Partial<ParsedExperience>) {
    const next = data.experiences.map((e, i) => (i === idx ? { ...e, ...patch } : e));
    onChange({ ...data, experiences: next });
  }

  function startEditing() {
    setEditBuffer(narration);
  }

  function cancelEditing() {
    setEditBuffer(null);
  }

  function commitNarration() {
    if (editBuffer === null) return;
    onChange({ ...data, career_summary_first_person: editBuffer });
    setEditBuffer(null);
  }

  return (
    <div className="space-y-6">
      {/* Step indicator */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          {STEPS.map((s, i) => (
            <span key={s.n} className="flex items-center gap-2">
              <span
                className={
                  s.n === 1
                    ? "rounded-full bg-accent px-3 py-1.5 font-semibold text-white"
                    : "rounded-full border border-border bg-white px-3 py-1.5 font-medium text-muted"
                }
              >
                {s.n} {s.label}
              </span>
              {i < STEPS.length - 1 && <span className="h-px w-4 bg-border" />}
            </span>
          ))}
        </div>
        {onSkip && (
          <button
            type="button"
            onClick={onSkip}
            className="text-xs text-muted transition hover:text-foreground"
          >
            Skip →
          </button>
        )}
      </div>

      {/* Eyebrow + headline */}
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-accent">
          Step 1 of 4 · this is the only required input
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground">
          Here&apos;s what we understood from your resume.
        </h1>
        <p className="mt-1 text-sm text-muted">
          Edit anything that&apos;s off. The more accurate this is, the sharper everything
          downstream gets.
        </p>
      </div>

      {/* File chip */}
      {fileMeta && (
        <div className="flex items-center justify-between rounded-xl border border-border bg-white px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10 text-accent">
              <svg
                className="h-[18px] w-[18px]"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">{fileMeta.filename}</div>
              <div className="text-xs text-muted">
                {fileMeta.parsedSec ? `Parsed in ${fileMeta.parsedSec.toFixed(1)}s · ` : ""}
                {Math.max(1, Math.round(fileMeta.sizeKB))} KB
              </div>
            </div>
          </div>
          {onSwap && (
            <button
              type="button"
              onClick={onSwap}
              className="rounded-full border border-border px-3 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
            >
              Swap resume
            </button>
          )}
        </div>
      )}

      {/* Split: outline | narration */}
      <div className="grid gap-5 lg:grid-cols-2">
        {/* ─── OUTLINE ─── */}
        <div className="rounded-2xl border border-border bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Outline</h3>
            <span className="rounded-full border border-border bg-white px-2.5 py-1 text-[11px] font-medium text-muted">
              Click any field to edit
            </span>
          </div>

          {data.experiences.length > 0 && (
            <div className="mb-5">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.1em] text-muted">
                Experience
              </p>
              <div className="space-y-2">
                {data.experiences.map((exp, expIdx) => {
                  const chipSource = (exp.projects ?? []).map((p) => p.title).filter(Boolean);
                  const chips =
                    chipSource.length > 0 ? chipSource : exp.bullets.slice(0, 3);
                  return (
                    <div
                      key={`${exp.company}-${expIdx}`}
                      className="rounded-r-lg border-l-2 border-accent bg-accent/5 px-3.5 py-3"
                    >
                      <div className="flex flex-wrap items-baseline gap-x-2">
                        <input
                          value={exp.role}
                          onChange={(e) =>
                            patchExperience(expIdx, { role: e.target.value })
                          }
                          className="min-w-[160px] flex-1 bg-transparent text-sm font-semibold text-foreground focus:outline-none"
                          placeholder="Role"
                        />
                        <span className="text-muted">·</span>
                        <input
                          value={exp.company}
                          onChange={(e) =>
                            patchExperience(expIdx, { company: e.target.value })
                          }
                          className="min-w-[120px] flex-1 bg-transparent text-sm text-muted focus:outline-none"
                          placeholder="Company"
                        />
                      </div>
                      <div className="mt-0.5 text-xs text-muted">
                        <input
                          value={`${exp.start_date ?? ""} — ${exp.end_date ?? ""}`
                            .trim()
                            .replace(/^—\s*/, "")
                            .replace(/\s*—\s*$/, "")}
                          onChange={(e) => {
                            const [start, end] = e.target.value
                              .split("—")
                              .map((s) => s.trim());
                            patchExperience(expIdx, {
                              start_date: start || "",
                              end_date: end || "",
                            });
                          }}
                          className="bg-transparent focus:outline-none"
                          placeholder="Start — End"
                        />
                      </div>
                      {chips.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {chips.slice(0, 4).map((c, i) => (
                            <span
                              key={`${exp.company}-chip-${i}`}
                              className="rounded-full bg-primary-500/10 px-2.5 py-0.5 text-[11px] font-medium text-primary-700"
                            >
                              {c}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {data.education.length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.1em] text-muted">
                Education
              </p>
              <ul className="space-y-1 text-sm text-foreground">
                {data.education.map((e, i) => (
                  <li key={i}>
                    <strong className="font-semibold">{e.degree}</strong>
                    <span className="text-muted"> · {e.institution}</span>
                    {e.year && <span className="text-muted"> · {e.year}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(data.projects ?? []).length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.1em] text-muted">
                Projects
              </p>
              <div className="space-y-2">
                {(data.projects ?? []).map((p, i) => (
                  <div
                    key={`proj-${i}`}
                    className="rounded-r-lg border-l-2 border-primary-400 bg-primary-50/40 px-3.5 py-2.5"
                  >
                    <p className="text-sm font-semibold text-foreground">{p.title}</p>
                    {p.one_liner && (
                      <p className="mt-0.5 text-xs text-muted line-clamp-2">{p.one_liner}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.skills.length > 0 && (
            <div className="mb-2">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.1em] text-muted">
                Skills
              </p>
              <div className="flex flex-wrap gap-1.5">
                {data.skills.slice(0, 24).map((s, i) => (
                  <span
                    key={`skill-${i}`}
                    className="rounded-full bg-[#EDF2F7] px-2.5 py-0.5 text-[11px] font-medium text-[#4A5568]"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {data.certifications.length > 0 && (
            <div>
              <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.1em] text-muted">
                Certifications
              </p>
              <ul className="space-y-0.5 text-xs text-foreground">
                {data.certifications.map((c, i) => (
                  <li key={`cert-${i}`}>• {c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* ─── FIRST-PERSON NARRATION ─── */}
        <div className="rounded-2xl border border-border bg-gradient-to-b from-[#FDF6F0] to-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                Your story, in your words
              </h3>
              <p className="mt-0.5 text-xs text-muted">
                Rewrite anything that doesn&apos;t sound like you.
              </p>
            </div>
            {/* "AI draft" chip removed per v2 copy audit. Purple accent on
                the narration block carries the meaning on its own. */}
          </div>

          {editing ? (
            <div>
              <textarea
                value={editBuffer ?? ""}
                onChange={(e) => setEditBuffer(e.target.value)}
                rows={18}
                className="w-full resize-y rounded-xl border border-border bg-white/80 p-3 text-sm leading-relaxed text-foreground focus:border-accent focus:outline-none"
                placeholder="At Amex, I led a 12-person team redesigning the returns flow…"
              />
              <div className="mt-3 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={cancelEditing}
                  className="rounded-full border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={commitNarration}
                  className="rounded-full bg-accent px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-hover"
                >
                  Save narration
                </button>
              </div>
            </div>
          ) : paragraphs.length > 0 ? (
            <div className="space-y-3 text-sm leading-relaxed text-foreground">
              {paragraphs.map((p, i) => (
                <p
                  key={i}
                  className="border-l-2 border-purple-500/30 pl-3"
                  dangerouslySetInnerHTML={{
                    __html: boldFirstClause(escapeHtml(p)),
                  }}
                />
              ))}
              {streamingNarration && (
                <span className="inline-block h-4 w-0.5 animate-pulse bg-accent align-middle" />
              )}
              <div>
                <button
                  type="button"
                  onClick={streamingNarration ? undefined : startEditing}
                  disabled={streamingNarration}
                  className={`mt-2 text-xs font-semibold ${
                    streamingNarration
                      ? "cursor-not-allowed text-muted"
                      : "text-accent hover:text-accent-hover"
                  }`}
                >
                  {streamingNarration ? "Generating your story…" : "Edit narration →"}
                </button>
              </div>
            </div>
          ) : streamingNarration ? (
            <div className="flex items-center gap-2 text-sm text-muted">
              <span className="inline-block h-4 w-0.5 animate-pulse bg-accent" />
              <span>Writing your story…</span>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-white/60 p-4 text-center text-xs text-muted">
              <p className="mb-2">
                No narration generated yet. Paste more resume content or write your own.
              </p>
              <button
                type="button"
                onClick={startEditing}
                className="rounded-full bg-accent px-4 py-1.5 text-xs font-semibold text-white"
              >
                Write narration
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Bottom row */}
      {onContinue && (
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <p className="text-xs text-muted">
            Backend will keep learning in the background — you don&apos;t need to wait.
          </p>
          <button
            type="button"
            onClick={onContinue}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-full bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-60"
          >
            {busy ? "Saving…" : continueLabel}
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
              />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Bold the lead clause if paragraph starts with "At {Company}," or "Before that at …,".
// Small helper so narration reads like the design without the model emitting markdown.
function boldFirstClause(html: string): string {
  const leadRe = /^(At [^,]+,|Before that at [^,]+,|Earlier at [^,]+,|Previously at [^,]+,|Most recently at [^,]+,)/;
  const m = html.match(leadRe);
  if (m) {
    return `<strong>${m[1]}</strong>${html.slice(m[1].length)}`;
  }
  return html;
}
