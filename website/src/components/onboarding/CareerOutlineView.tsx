"use client";

// Wave 2 Sub-phase 2A — the post-parse outline + first-person interpretation
// view. Replaces the flat-form UX with Satvik's two-zone design:
//
//   ┌───────────────────────────────┬──────────────────────────────┐
//   │ OUTLINE (structured, editable)│ FIRST-PERSON INTERPRETATION  │
//   │  • Company                    │  "I'm a PM with 3.5 years…   │
//   │    - Role (dates)             │   I led 18-member team at…   │
//   │      · Project one-liner      │   Here I was…"               │
//   │        · 2-3 key achievements │                              │
//   │  • Education / Certs / Skills │                              │
//   └───────────────────────────────┴──────────────────────────────┘
//
// User edits either side inline. On Save & Continue, the OnboardingFlow
// persists both + fires background categorization + embedding.
//
// Reference: specs/wave-2-journey-2026-04-18.md § Stage 2.

import { useState, useEffect } from "react";

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

export interface CareerOutlineData {
  experiences: ParsedExperience[];
  education: ParsedEducation[];
  skills: string[];
  certifications: string[];
  career_summary_first_person: string;
}

interface Props {
  data: CareerOutlineData;
  onChange: (data: CareerOutlineData) => void;
}

export function CareerOutlineView({ data, onChange }: Props) {
  const [summary, setSummary] = useState(data.career_summary_first_person ?? "");

  // Keep local summary state in sync when the parent reloads data.
  useEffect(() => {
    setSummary(data.career_summary_first_person ?? "");
  }, [data.career_summary_first_person]);

  function patchExperience(idx: number, patch: Partial<ParsedExperience>) {
    const next = data.experiences.map((e, i) => (i === idx ? { ...e, ...patch } : e));
    onChange({ ...data, experiences: next });
  }

  function patchProject(expIdx: number, projIdx: number, patch: Partial<ParsedProject>) {
    const exp = data.experiences[expIdx];
    const nextProjects = (exp.projects ?? []).map((p, i) =>
      i === projIdx ? { ...p, ...patch } : p,
    );
    patchExperience(expIdx, { projects: nextProjects });
  }

  function commitSummary() {
    onChange({ ...data, career_summary_first_person: summary });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
      {/* ─── LEFT: Outline ─────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium uppercase tracking-[0.12em] text-accent">
            Your career, as we read it
          </p>
          <span className="text-xs text-muted">Click any field to edit</span>
        </div>

        {data.experiences.map((exp, expIdx) => (
          <article
            key={`${exp.company}-${expIdx}`}
            className="rounded-2xl border border-border bg-surface p-5 shadow-sm"
          >
            <header className="mb-3">
              <input
                value={exp.company}
                onChange={(e) => patchExperience(expIdx, { company: e.target.value })}
                className="w-full bg-transparent text-lg font-semibold text-foreground focus:outline-none"
                placeholder="Company name"
              />
              <div className="mt-1 flex flex-wrap items-center gap-x-2 text-sm text-muted">
                <input
                  value={exp.role}
                  onChange={(e) => patchExperience(expIdx, { role: e.target.value })}
                  className="flex-1 min-w-[160px] bg-transparent focus:outline-none"
                  placeholder="Role / title"
                />
                <span>·</span>
                <input
                  value={`${exp.start_date ?? ""} – ${exp.end_date ?? ""}`.trim().replace(/^–\s*/, "").replace(/\s*–\s*$/, "")}
                  onChange={(e) => {
                    const [start, end] = e.target.value.split("–").map((s) => s.trim());
                    patchExperience(expIdx, { start_date: start || "", end_date: end || "" });
                  }}
                  className="bg-transparent text-xs focus:outline-none"
                  placeholder="Start – End"
                />
              </div>
            </header>

            {/* Projects */}
            {(exp.projects ?? []).length > 0 ? (
              <ul className="space-y-3">
                {(exp.projects ?? []).map((proj, projIdx) => (
                  <li
                    key={`${exp.company}-${expIdx}-proj-${projIdx}`}
                    className="rounded-xl border border-border/60 bg-background/40 p-3"
                  >
                    <input
                      value={proj.title}
                      onChange={(e) => patchProject(expIdx, projIdx, { title: e.target.value })}
                      className="w-full bg-transparent text-sm font-medium text-foreground focus:outline-none"
                      placeholder="Project title"
                    />
                    <textarea
                      value={proj.one_liner}
                      onChange={(e) => patchProject(expIdx, projIdx, { one_liner: e.target.value })}
                      className="mt-1 w-full resize-none bg-transparent text-xs text-muted focus:outline-none"
                      rows={2}
                      placeholder="One-liner describing scope"
                    />
                    {proj.key_achievements.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {proj.key_achievements.map((ach, achIdx) => (
                          <li key={achIdx} className="flex items-start gap-2 text-xs text-foreground/90">
                            <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-accent" />
                            <input
                              value={ach}
                              onChange={(e) => {
                                const next = proj.key_achievements.map((a, i) =>
                                  i === achIdx ? e.target.value : a,
                                );
                                patchProject(expIdx, projIdx, { key_achievements: next });
                              }}
                              className="flex-1 bg-transparent focus:outline-none"
                            />
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            ) : exp.bullets.length > 0 ? (
              <ul className="space-y-1.5">
                {exp.bullets.slice(0, 4).map((b, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground/90">
                    <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-muted" />
                    <span className="flex-1">{b}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs italic text-muted">No projects or bullets parsed for this role.</p>
            )}
          </article>
        ))}

        {/* Education */}
        {data.education.length > 0 && (
          <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
            <p className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-muted">
              Education
            </p>
            <ul className="space-y-1.5 text-sm text-foreground/90">
              {data.education.map((e, i) => (
                <li key={i} className="flex items-center justify-between gap-3">
                  <span className="flex-1">
                    <strong>{e.degree}</strong> · {e.institution}
                  </span>
                  <span className="text-xs text-muted">{e.year}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Skills + Certs chips */}
        {(data.skills.length > 0 || data.certifications.length > 0) && (
          <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
            {data.skills.length > 0 && (
              <>
                <p className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-muted">
                  Skills
                </p>
                <div className="mb-4 flex flex-wrap gap-2">
                  {data.skills.slice(0, 30).map((s, i) => (
                    <span
                      key={`skill-${i}`}
                      className="rounded-full bg-primary-500/10 px-2.5 py-0.5 text-xs text-primary-700"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </>
            )}
            {data.certifications.length > 0 && (
              <>
                <p className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-muted">
                  Certifications
                </p>
                <ul className="space-y-1 text-xs text-foreground/90">
                  {data.certifications.map((c, i) => (
                    <li key={`cert-${i}`}>• {c}</li>
                  ))}
                </ul>
              </>
            )}
          </section>
        )}
      </div>

      {/* ─── RIGHT: First-person interpretation ─────────────────────── */}
      <aside className="space-y-3 rounded-2xl border border-border bg-[#FDF6F0] p-5 shadow-sm lg:sticky lg:top-4 lg:self-start">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.12em] text-accent">
            How we read your career
          </p>
          <p className="mt-1 text-xs text-muted">
            Written in first person — this is what we understand from your resume.
            Edit anything that sounds wrong before we memorise it.
          </p>
        </div>
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          onBlur={commitSummary}
          className="w-full resize-y rounded-xl border border-border bg-white/70 p-3 text-sm leading-relaxed text-foreground focus:border-accent focus:outline-none"
          rows={14}
          placeholder="I'm a Product Manager with 3.5 years at Amex and Sprinklr. I led …"
        />
        <p className="text-[11px] italic text-muted">
          On Save &amp; Continue, we categorise this into nuggets + start embedding so your
          resume + cover letter + DM can pull from it later.
        </p>
      </aside>
    </div>
  );
}
