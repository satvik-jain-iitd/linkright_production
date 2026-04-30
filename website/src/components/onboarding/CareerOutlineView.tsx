"use client";

// Wave 2 / Screen 04 — Resume upload review + first-person narration.
// Design handoff: specs/design-handoff-2026-04-18/ → screens-build.jsx Screen04.
//
// LOCK/UNLOCK MODEL (v5 — Bug 14 compact redesign):
//   - Checkbox-style inline toggle (☐/☑) replaces the prominent Lock/Unlock button.
//   - Cards are collapsible: first card auto-expanded, rest collapsed by default.
//   - Collapsed view: heading + 2-line preview + inline [☐][Edit][Delete].
//   - "Read more" / "Show less" toggles full body text.
//   - Lock logic unchanged: locked cards enrich on Save via /api/onboarding/stories/lock.
//
// Shape:
//   ┌─ step indicator (1 Resume · 2 Profile · 3 Preferences · 4 Broadcast · 5 First match) ─┐
//   │ eyebrow + headline + sub                                                │
//   │ [file-chip: filename · size · parsed in Ns]   [swap resume]             │
//   │ ┌──────────── OUTLINE ────────────┬──────── YOUR STORY ─────────────┐   │
//   │ │ Experience (company+role+chips) │ Collapsible cards, checkbox lock │   │
//   │ │ Education · Skills              │                                  │   │
//   │ └─────────────────────────────────┴─────────────────────────────────┘   │
//   │ [explainer]                        [Save and continue → (≥1 locked)]   │
//   └──────────────────────────────────────────────────────────────────────────┘

import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { track } from "@/lib/analytics";

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

// Per-card enrichment state
type CardStatus = "idle" | "enriching" | "ready" | "stale";

interface CardState {
  locked: boolean;
  status: CardStatus;
  // Enriched metadata from /api/onboarding/enrich-chunk
  enrichedMeta: { importance: string; tags: string[]; leadership: string } | null;
  // DB chunk_id after first save (null before first upload)
  chunkId: string | null;
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
  { n: 4, label: "Broadcast" },
  { n: 5, label: "First match" },
] as const;

// Truncate body text to approximately 2 lines (~100 chars)
function truncatePreview(body: string, maxChars = 110): string {
  const flat = body
    .split(/\n+/)
    .filter(Boolean)
    .map((l) => l.replace(/^[-*•]\s*/, ""))
    .join(" ");
  if (flat.length <= maxChars) return flat;
  return flat.slice(0, maxChars).replace(/\s+\S*$/, "") + "…";
}

export function CareerOutlineView({
  data,
  onChange,
  fileMeta,
  onSwap,
  onContinue,
  onSkip,
  continueLabel,
  busy,
  streamingNarration = false,
}: Props) {
  const narration = data.career_summary_first_person ?? "";
  const [editBuffer, setEditBuffer] = useState<string | null>(null);
  const editing = editBuffer !== null;
  const [editingCardIdx, setEditingCardIdx] = useState<number | null>(null);
  const [editingCardHeading, setEditingCardHeading] = useState("");
  const [editingCardBody, setEditingCardBody] = useState("");

  // Collapsible cards — first card (index 0) auto-expanded for discoverability
  const [expandedCardIdx, setExpandedCardIdx] = useState<number | null>(0);

  const paragraphs = useMemo(
    () =>
      narration
        .split(/\n{2,}/)
        .map((p) => p.trim())
        .filter(Boolean),
    [narration],
  );

  const initiativeCards = useMemo(() => parseInitiativeCards(narration), [narration]);

  // Per-card state keyed by card index
  const [cardStates, setCardStates] = useState<Record<number, CardState>>({});

  // Reset card states when narration changes (new resume upload or streaming completed)
  const prevCardCountRef = useRef(initiativeCards.length);
  const internalMutationRef = useRef(false);
  useEffect(() => {
    if (internalMutationRef.current) {
      internalMutationRef.current = false;
      prevCardCountRef.current = initiativeCards.length;
      return;
    }
    if (initiativeCards.length !== prevCardCountRef.current) {
      prevCardCountRef.current = initiativeCards.length;
      setCardStates({});
      // Re-expand first card when card set changes (e.g. streaming completes)
      setExpandedCardIdx(0);
    }
  }, [initiativeCards.length]);

  const getCardState = useCallback(
    (i: number): CardState => {
      return (
        cardStates[i] ?? {
          locked: false,
          status: "idle" as CardStatus,
          enrichedMeta: null,
          chunkId: null,
        }
      );
    },
    [cardStates],
  );

  const setCardState = useCallback(
    (i: number, patch: Partial<CardState>) => {
      setCardStates((prev) => ({
        ...prev,
        [i]: { ...((prev[i] as CardState) ?? { locked: false, status: "idle" as CardStatus, enrichedMeta: null, chunkId: null }), ...patch },
      }));
    },
    [],
  );

  // How many cards are locked right now
  const lockedCount = useMemo(
    () => Object.values(cardStates).filter((s) => s.locked).length,
    [cardStates],
  );

  const totalCount = initiativeCards.length;

  // Lock a card: optimistic UI only.
  const lockCard = useCallback(
    (i: number) => {
      if (!initiativeCards[i]) return;
      setCardState(i, { locked: true, status: "ready" });
      track({ event: "story_locked", properties: { index: i } });
    },
    [initiativeCards, setCardState],
  );

  // Unlock a card
  const unlockCard = useCallback(
    (i: number) => {
      setCardState(i, { locked: false, status: "stale", enrichedMeta: null });
      track({ event: "story_unlocked", properties: { index: i } });
    },
    [setCardState],
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

  function startCardEdit(i: number) {
    const card = initiativeCards[i];
    if (!card) return;
    setEditingCardIdx(i);
    setEditingCardHeading(card.heading);
    setEditingCardBody(card.body);
    // Expand card being edited
    setExpandedCardIdx(i);
  }

  function cancelCardEdit() {
    setEditingCardIdx(null);
  }

  function commitCardEdit() {
    if (editingCardIdx === null) return;
    internalMutationRef.current = true;
    const updated = replaceCardInNarration(narration, editingCardIdx, editingCardHeading, editingCardBody);
    onChange({ ...data, career_summary_first_person: updated });
    setCardState(editingCardIdx, { locked: false, status: "stale", enrichedMeta: null });
    setEditingCardIdx(null);
  }

  function deleteCard(i: number) {
    const cs = getCardState(i);
    if (cs.locked) return;
    const updated = removeCardFromNarration(narration, i);
    internalMutationRef.current = true;
    onChange({ ...data, career_summary_first_person: updated });
    setCardStates((prev) => {
      const next: Record<number, CardState> = {};
      for (const [k, v] of Object.entries(prev)) {
        const ki = Number(k);
        if (ki < i) next[ki] = v as CardState;
        else if (ki > i) next[ki - 1] = v as CardState;
      }
      return next;
    });
    // Fix expanded idx after deletion
    setExpandedCardIdx((prev) => {
      if (prev === null) return null;
      if (prev === i) return null;
      if (prev > i) return prev - 1;
      return prev;
    });
  }

  // Build enriched chunks array from locked cards for final upload
  function buildLockedChunks(): { heading: string; text: string; meta: Record<string, unknown>; originalIndex: number }[] {
    return initiativeCards
      .map((card, i) => {
        const cs = getCardState(i);
        if (!cs.locked) return null;
        const roleMatch = narration.match(/^## ([^—–\n]+)/m);
        const roleHeader = roleMatch ? roleMatch[0] : "";
        const chunkText = roleHeader
          ? `${roleHeader}\n\n### ${card.heading}\n${card.body}`
          : `### ${card.heading}\n${card.body}`;
        const base = extractChunkMeta(card);
        return {
          heading: card.heading,
          text: chunkText,
          meta: { ...base, ...(cs.enrichedMeta ?? {}) },
          originalIndex: i,
        };
      })
      .filter((c): c is NonNullable<typeof c> => c !== null);
  }

  // Derive continue button label.
  // continueLabel prop is accepted for backward compat but not used in derived logic —
  // the count-based copy is always shown per spec (Bug 14).
  const allLocked = useMemo(
    () => totalCount > 0 && initiativeCards.every((_, i) => getCardState(i).locked),
    [totalCount, initiativeCards, getCardState],
  );

  const derivedContinueLabel = useMemo(() => {
    if (busy) return "Saving…";
    if (totalCount === 0) return "Add at least one story to continue";
    if (lockedCount === 0) return `Lock at least one story to continue (0/${totalCount} ready)`;
    if (lockedCount < totalCount) return `Lock or delete remaining (${lockedCount}/${totalCount} ready)`;
    return `Save and continue (${lockedCount} stor${lockedCount === 1 ? "y" : "ies"} selected)`;
  }, [busy, totalCount, lockedCount]);

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
                    ? "rounded-[10px] bg-accent px-3 py-1.5 font-semibold text-white"
                    : "rounded-[10px] border border-border bg-white px-3 py-1.5 font-medium text-muted"
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
            Skip
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
          Check the stories that are accurate. Edit anything that&apos;s off, then check.
          Checked stories get enriched — the more you select, the sharper everything downstream gets.
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
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
            >
              Swap resume
            </button>
          )}
        </div>
      )}

      {/* Selection progress banner — shown when ≥1 card locked */}
      {lockedCount > 0 && !streamingNarration && (
        <div className="flex items-center gap-3 rounded-xl border border-tertiary-200 bg-tertiary-50 px-4 py-3">
          <svg className="h-4 w-4 shrink-0 text-tertiary-600" fill="currentColor" viewBox="0 0 24 24">
            <path
              fillRule="evenodd"
              d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z"
              clipRule="evenodd"
            />
          </svg>
          <p className="text-xs font-medium text-tertiary-700">
            {lockedCount} of {totalCount} stor{lockedCount === 1 ? "y" : "ies"} selected
          </p>
        </div>
      )}

      {/* Split: outline | narration */}
      <div className="grid gap-5 lg:grid-cols-2 lg:auto-rows-fr">
        {/* ─── OUTLINE ─── */}
        <div className="h-full rounded-2xl border border-border bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Outline</h3>
            <span className="rounded-[10px] border border-border bg-white px-2.5 py-1 text-[11px] font-medium text-muted">
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
                      <div className="flex items-baseline gap-x-2">
                        <input
                          value={exp.role}
                          onChange={(e) =>
                            patchExperience(expIdx, { role: e.target.value })
                          }
                          className="bg-transparent text-sm font-semibold text-foreground focus:outline-none"
                          placeholder="Role"
                        />
                        <input
                          value={exp.company}
                          onChange={(e) =>
                            patchExperience(expIdx, { company: e.target.value })
                          }
                          className="ml-auto bg-transparent text-sm text-muted focus:outline-none text-right"
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
                          {chips.slice(0, 4).map((c, chipI) => (
                            <span
                              key={`${exp.company}-chip-${chipI}`}
                              className="rounded-[10px] bg-primary-500/10 px-2.5 py-0.5 text-[11px] font-medium text-primary-700"
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
                    className="rounded-[10px] bg-[#EDF2F7] px-2.5 py-0.5 text-[11px] font-medium text-[#4A5568]"
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

        {/* ─── FIRST-PERSON NARRATION — COLLAPSIBLE CARDS ─── */}
        <div className="h-full rounded-2xl border border-border bg-gradient-to-b from-[#FDF6F0] to-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                Your story, in your words
              </h3>
              <p className="mt-0.5 text-xs text-muted">
                Check the stories that are right. Edit anything off, then check.
              </p>
            </div>
            {!editing && !streamingNarration && paragraphs.length > 0 && (
              <button
                type="button"
                onClick={startEditing}
                className="text-xs font-semibold text-accent hover:text-accent-hover transition"
              >
                Edit all
              </button>
            )}
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
                  className="rounded-lg border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={commitNarration}
                  className="rounded-lg bg-accent px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-hover"
                >
                  Save narration
                </button>
              </div>
            </div>
          ) : initiativeCards.length > 0 ? (
            <div className="space-y-2">
              {initiativeCards.map((card, i) => {
                const cs = getCardState(i);
                const isEditingThis = editingCardIdx === i;
                const isExpanded = expandedCardIdx === i;
                return (
                  <StoryCard
                    key={i}
                    card={card}
                    index={i}
                    cardState={cs}
                    isEditing={isEditingThis}
                    isExpanded={isExpanded}
                    editingHeading={editingCardHeading}
                    editingBody={editingCardBody}
                    onEditHeadingChange={setEditingCardHeading}
                    onEditBodyChange={setEditingCardBody}
                    onToggleLock={() => cs.locked ? unlockCard(i) : lockCard(i)}
                    onStartEdit={() => startCardEdit(i)}
                    onCancelEdit={cancelCardEdit}
                    onCommitEdit={commitCardEdit}
                    onDelete={() => deleteCard(i)}
                    onToggleExpand={() =>
                      setExpandedCardIdx((prev) => (prev === i ? null : i))
                    }
                  />
                );
              })}
              {streamingNarration && (
                <div className="h-16 animate-pulse rounded-[16px] border border-border bg-white" />
              )}
            </div>
          ) : streamingNarration ? (
            <div className="space-y-2">
              {[1, 2, 3].map((k) => (
                <div
                  key={k}
                  className="h-16 animate-pulse rounded-[16px] border border-border bg-white"
                />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-white/60 p-4 text-center text-xs text-muted">
              <p className="mb-2">
                No narration generated yet. Paste more resume content or write your own.
              </p>
              <button
                type="button"
                onClick={startEditing}
                className="rounded-lg bg-accent px-4 py-1.5 text-xs font-semibold text-white"
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
            {lockedCount > 0
              ? `${lockedCount} stor${lockedCount === 1 ? "y" : "ies"} selected. Save to continue.`
              : "Check at least one story to continue."}
          </p>
          <button
            type="button"
            onClick={() => {
              if (totalCount === 0 || !allLocked) return;
              storeLockedChunks(buildLockedChunks());
              onContinue();
            }}
            disabled={busy || totalCount === 0 || !allLocked}
            title={totalCount === 0 ? "Add a story first" : !allLocked ? "Lock or delete all stories first" : undefined}
            className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-60"
          >
            {derivedContinueLabel}
            {!busy && lockedCount > 0 && (
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
            )}
          </button>
        </div>
      )}
    </div>
  );
}

// ── StoryCard component ───────────────────────────────────────────────────

function StoryCard({
  card,
  index,
  cardState,
  isEditing,
  isExpanded,
  editingHeading,
  editingBody,
  onEditHeadingChange,
  onEditBodyChange,
  onToggleLock,
  onStartEdit,
  onCancelEdit,
  onCommitEdit,
  onDelete,
  onToggleExpand,
}: {
  card: { heading: string; body: string };
  index: number;
  cardState: CardState;
  isEditing: boolean;
  isExpanded: boolean;
  editingHeading: string;
  editingBody: string;
  onEditHeadingChange: (v: string) => void;
  onEditBodyChange: (v: string) => void;
  onToggleLock: () => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onCommitEdit: () => void;
  onDelete: () => void;
  onToggleExpand: () => void;
}) {
  const { locked } = cardState;

  const cardCls = locked
    ? "rounded-[16px] border border-tertiary-200 bg-tertiary-50/40 px-3.5 py-3 transition"
    : "rounded-[16px] border border-border bg-surface px-3.5 py-3 transition";

  if (isEditing) {
    return (
      <div className={cardCls}>
        <div className="space-y-2">
          <input
            value={editingHeading}
            onChange={(e) => onEditHeadingChange(e.target.value)}
            className="w-full rounded-lg border border-border bg-white px-3 py-1.5 text-sm font-semibold text-foreground focus:border-accent focus:outline-none"
            placeholder="Initiative heading"
          />
          <textarea
            value={editingBody}
            onChange={(e) => onEditBodyChange(e.target.value)}
            rows={4}
            className="w-full resize-y rounded-lg border border-border bg-white px-3 py-2 text-xs leading-relaxed text-foreground focus:border-accent focus:outline-none"
            placeholder="Describe this story..."
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onCancelEdit}
              className="rounded-lg border border-border px-3 py-1 text-xs font-semibold text-foreground transition hover:border-accent"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onCommitEdit}
              className="rounded-lg bg-accent px-3 py-1 text-xs font-semibold text-white transition hover:bg-accent-hover"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    );
  }

  const flat = card.body
    .split(/\n+/)
    .filter(Boolean)
    .map((l) => l.replace(/^[-*\u2022]\s*/, ""))
    .join(" ");
  const needsExpansion = flat.length > 110;
  const preview = needsExpansion ? truncatePreview(card.body) : flat;
  const bodyLines = card.body
    .split(/\n+/)
    .filter(Boolean)
    .map((l) => l.replace(/^[-*\u2022]\s*/, ""));

  return (
    <div className={cardCls} data-story-index={index}>
      {/* Header row: heading + inline actions */}
      <div className="flex items-start gap-2">
        {/* Checkbox-style lock toggle */}
        <button
          type="button"
          onClick={onToggleLock}
          aria-label={locked ? "Unlock this story" : "Lock for resume"}
          title={locked ? "Unlock to edit" : "Lock to use this story"}
          className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded transition ${
            locked
              ? "border-0 bg-accent text-white"
              : "border border-muted/40 bg-white hover:border-accent"
          }`}
        >
          {locked && (
            <svg className="h-2.5 w-2.5" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          )}
        </button>

        {/* Heading — clicking expands/collapses */}
        <button
          type="button"
          onClick={onToggleExpand}
          className="flex-1 text-left"
        >
          <h4 className="text-[13px] font-semibold leading-snug text-foreground">
            {card.heading}
          </h4>
          {/* 2-line preview shown only when collapsed */}
          {!isExpanded && (
            <p className="mt-0.5 text-[11px] leading-relaxed text-muted line-clamp-2">
              {preview}
            </p>
          )}
        </button>

        {/* Edit + Delete (small icon buttons) — always visible */}
        <div className="flex shrink-0 items-center gap-1">
          {!locked && (
            <button
              type="button"
              onClick={onStartEdit}
              aria-label="Edit this story"
              title="Edit"
              className="flex h-5 w-5 items-center justify-center rounded text-muted transition hover:text-accent"
            >
              <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" />
              </svg>
            </button>
          )}
          {!locked && (
            <button
              type="button"
              onClick={onDelete}
              aria-label="Delete this story"
              title="Delete"
              className="flex h-5 w-5 items-center justify-center rounded text-muted transition hover:text-red-500"
            >
              <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Expanded: full body + Read more/less affordance */}
      {isExpanded && (
        <div className="mt-2 space-y-1 text-[11px] leading-relaxed text-muted pl-6">
          {bodyLines.map((line, j) => (
            <p key={j}>{line}</p>
          ))}
        </div>
      )}

      {/* Read more / Show less affordance — only if body is long enough to truncate */}
      {needsExpansion && (
        <button
          type="button"
          onClick={onToggleExpand}
          className="mt-1.5 pl-6 text-[11px] font-semibold text-accent transition hover:text-accent-hover"
        >
          {isExpanded ? "Show less" : "Read more"}
        </button>
      )}
    </div>
  );
}

// ── Module-level locked chunks store (avoids prop threading) ─────────────────
// OnboardingFlow reads this before calling /api/career/upload

let _lockedChunksStore: { heading: string; text: string; meta: Record<string, unknown>; originalIndex: number }[] = [];

export function storeLockedChunks(chunks: typeof _lockedChunksStore) {
  _lockedChunksStore = chunks;
}

export function getLockedChunks(): typeof _lockedChunksStore {
  return _lockedChunksStore;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function extractChunkMeta(card: { heading: string; body: string }): Record<string, unknown> {
  return { initiative: card.heading };
}

function parseInitiativeCards(narration: string): { heading: string; body: string }[] {
  if (!narration?.trim()) return [];
  const hasInitiatives = /^### /m.test(narration);
  if (hasInitiatives) {
    const cards: { heading: string; body: string }[] = [];
    const roleSections = narration.split(/(?=^## )/m).filter((s) => s.trim());
    for (const roleSection of roleSections) {
      const parts = roleSection.split(/(?=^### )/m);
      for (const part of parts) {
        const trimmed = part.trimStart();
        if (!trimmed.startsWith("### ")) continue;
        const lines = trimmed.split("\n");
        const heading = lines[0].replace(/^### /, "").trim();
        const body = lines.slice(1).join("\n").trim();
        if (heading && body) cards.push({ heading, body });
      }
    }
    if (cards.length > 0) return cards;
  }
  // Fallback: no ### found — split by ## role sections
  const roleSections = narration.split(/(?=^## )/m).filter((s) => s.trim());
  const cards = roleSections
    .map((section) => {
      const lines = section.split("\n");
      const heading = lines[0].replace(/^## /, "").trim() || "Your story";
      const body = lines.slice(1).join("\n").trim();
      return { heading, body };
    })
    .filter((c) => c.body);
  return cards.length > 0 ? cards : [];
}

function replaceCardInNarration(
  narration: string,
  cardIndex: number,
  newHeading: string,
  newBody: string,
): string {
  const lines = narration.split("\n");
  let count = -1;
  let inTarget = false;
  const out: string[] = [];

  for (const line of lines) {
    if (line.startsWith("### ")) {
      count++;
      if (count === cardIndex) {
        inTarget = true;
        out.push(`### ${newHeading}`);
        newBody.split("\n").forEach((bl) => out.push(bl));
        continue;
      } else if (inTarget) {
        inTarget = false;
      }
    } else if (inTarget && line.startsWith("## ")) {
      inTarget = false;
    }
    if (!inTarget) {
      out.push(line);
    }
  }
  return out.join("\n");
}

function removeCardFromNarration(narration: string, cardIndex: number): string {
  const lines = narration.split("\n");
  let count = -1;
  let inTarget = false;
  const out: string[] = [];

  for (const line of lines) {
    if (line.startsWith("### ")) {
      count++;
      if (count === cardIndex) {
        inTarget = true;
        continue;
      } else if (inTarget) {
        inTarget = false;
      }
    } else if (inTarget && line.startsWith("## ")) {
      inTarget = false;
    }
    if (!inTarget) {
      out.push(line);
    }
  }
  return out.join("\n");
}
