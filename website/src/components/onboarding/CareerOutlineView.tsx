"use client";

// Wave 2 / Screen 04 — Resume upload review + first-person narration.
// Design handoff: specs/design-handoff-2026-04-18/ → screens-build.jsx Screen04.
//
// LOCK/UNLOCK MODEL (v3 — PR #26):
//   - Each initiative card has Lock / Unlock / Edit / Delete actions.
//   - Lock → fires enrich-chunk immediately for that card, marks it enriched.
//   - Unlock → card becomes editable; enrichment cleared.
//   - Edit when unlocked → inline textarea, Save re-queues enrichment.
//   - Delete only when unlocked.
//   - Save & Continue enabled when ≥1 card locked. Calls submit-resume then
//     career/upload, then navigates to Profile step.
//
// Shape:
//   ┌─ step indicator (1 Resume · 2 Profile · 3 Preferences · 4 Broadcast · 5 First match) ─┐
//   │ eyebrow + headline + sub                                                │
//   │ [file-chip: filename · size · parsed in Ns]   [swap resume]             │
//   │ ┌──────────── OUTLINE ────────────┬──────── YOUR STORY ─────────────┐   │
//   │ │ Experience (company+role+chips) │ Lock/unlock cards per initiative │   │
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
  const [editingCardIdx, setEditingCardIdx] = useState<number | null>(null);
  const [editingCardHeading, setEditingCardHeading] = useState("");
  const [editingCardBody, setEditingCardBody] = useState("");

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
  // We only reset if the number of cards changes to avoid thrashing during streaming.
  // internalMutationRef is set to true before internal deleteCard/commitCardEdit actions
  // that change card count — those should NOT reset lock states.
  const prevCardCountRef = useRef(initiativeCards.length);
  const internalMutationRef = useRef(false);
  useEffect(() => {
    if (internalMutationRef.current) {
      // Internal mutation (delete/edit) caused the count change — skip reset
      internalMutationRef.current = false;
      prevCardCountRef.current = initiativeCards.length;
      return;
    }
    if (initiativeCards.length !== prevCardCountRef.current) {
      prevCardCountRef.current = initiativeCards.length;
      setCardStates({});
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

  // Lock a card: fire enrichment, mark locked
  const lockCard = useCallback(
    async (i: number) => {
      const card = initiativeCards[i];
      if (!card) return;
      // Optimistic: mark locked + enriching immediately
      setCardState(i, { locked: true, status: "enriching" });
      track({ event: "story_locked", properties: { index: i } });

      // Build career context from experiences
      const careerContext = buildCareerContext(data.experiences);
      const chunkText = `${card.heading}\n\n${card.body}`;

      try {
        const res = await fetch("/api/onboarding/enrich-chunk", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chunk_text: chunkText,
            career_context: careerContext,
          }),
        });
        const enriched = res.ok ? await res.json() : { importance: "P2", tags: [], leadership: "none" };
        setCardState(i, { locked: true, status: "ready", enrichedMeta: enriched });
      } catch {
        // Enrichment failed — card stays locked but with null meta
        setCardState(i, { locked: true, status: "ready", enrichedMeta: null });
      }
    },
    [initiativeCards, data.experiences, setCardState],
  );

  // Unlock a card: clear enrichment, mark editable
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
  }

  function cancelCardEdit() {
    setEditingCardIdx(null);
  }

  function commitCardEdit() {
    if (editingCardIdx === null) return;
    internalMutationRef.current = true; // prevent useEffect from resetting all card states
    const updated = replaceCardInNarration(narration, editingCardIdx, editingCardHeading, editingCardBody);
    onChange({ ...data, career_summary_first_person: updated });
    // Edit auto-unlocks + marks stale (re-lock required to re-enrich)
    setCardState(editingCardIdx, { locked: false, status: "stale", enrichedMeta: null });
    setEditingCardIdx(null);
  }

  function deleteCard(i: number) {
    const cs = getCardState(i);
    if (cs.locked) return; // shouldn't happen — button hidden when locked
    const updated = removeCardFromNarration(narration, i);
    internalMutationRef.current = true; // prevent useEffect from resetting all card states
    onChange({ ...data, career_summary_first_person: updated });
    // Remove card state
    setCardStates((prev) => {
      const next: Record<number, CardState> = {};
      for (const [k, v] of Object.entries(prev)) {
        const ki = Number(k);
        if (ki < i) next[ki] = v as CardState;
        else if (ki > i) next[ki - 1] = v as CardState; // shift indices down
      }
      return next;
    });
  }

  // Build enriched chunks array from locked cards for final upload
  function buildLockedChunks(): { heading: string; text: string; meta: Record<string, unknown> }[] {
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
        };
      })
      .filter((c): c is NonNullable<typeof c> => c !== null);
  }

  // Exposed via prop so OnboardingFlow can assemble final data
  // (we attach it to the `onContinue` closure below rather than a separate prop)

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
          Lock the stories that are accurate. Edit anything that&apos;s off, then lock.
          Locked stories get enriched immediately — the more you lock, the sharper everything
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
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
            >
              Swap resume
            </button>
          )}
        </div>
      )}

      {/* Lock progress banner — shown when ≥1 card locked */}
      {lockedCount > 0 && !streamingNarration && (
        <div className="flex items-center gap-3 rounded-xl border border-tertiary-200 bg-tertiary-50 px-4 py-3">
          <svg className="h-4 w-4 shrink-0 text-tertiary-600" fill="currentColor" viewBox="0 0 24 24">
            <path
              fillRule="evenodd"
              d="M12 1.5a5.25 5.25 0 00-5.25 5.25v3a3 3 0 00-3 3v6.75a3 3 0 003 3h10.5a3 3 0 003-3v-6.75a3 3 0 00-3-3v-3c0-2.9-2.35-5.25-5.25-5.25zm3.75 8.25v-3a3.75 3.75 0 10-7.5 0v3h7.5z"
              clipRule="evenodd"
            />
          </svg>
          <p className="text-xs font-medium text-tertiary-700">
            {lockedCount} of {initiativeCards.length} stor{lockedCount === 1 ? "y" : "ies"} locked
            {Object.values(cardStates).some((s) => s.locked && s.status === "enriching") && (
              <span className="ml-1 text-tertiary-500">· enriching…</span>
            )}
          </p>
        </div>
      )}

      {/* Split: outline | narration */}
      <div className="grid gap-5 lg:grid-cols-2">
        {/* ─── OUTLINE ─── */}
        <div className="rounded-2xl border border-border bg-white p-6">
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
                          {chips.slice(0, 4).map((c, i) => (
                            <span
                              key={`${exp.company}-chip-${i}`}
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

        {/* ─── FIRST-PERSON NARRATION — LOCK/UNLOCK CARDS ─── */}
        <div className="rounded-2xl border border-border bg-gradient-to-b from-[#FDF6F0] to-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                Your story, in your words
              </h3>
              <p className="mt-0.5 text-xs text-muted">
                Lock the stories that are right. Edit anything off, then re-lock.
              </p>
            </div>
            {!editing && !streamingNarration && paragraphs.length > 0 && (
              <button
                type="button"
                onClick={startEditing}
                className="text-xs font-semibold text-accent hover:text-accent-hover transition"
              >
                Edit all →
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
            <div className="space-y-3">
              {initiativeCards.map((card, i) => {
                const cs = getCardState(i);
                const isEditingThis = editingCardIdx === i;
                return (
                  <StoryCard
                    key={i}
                    card={card}
                    index={i}
                    cardState={cs}
                    isEditing={isEditingThis}
                    editingHeading={editingCardHeading}
                    editingBody={editingCardBody}
                    onEditHeadingChange={setEditingCardHeading}
                    onEditBodyChange={setEditingCardBody}
                    onLock={() => lockCard(i)}
                    onUnlock={() => unlockCard(i)}
                    onStartEdit={() => startCardEdit(i)}
                    onCancelEdit={cancelCardEdit}
                    onCommitEdit={commitCardEdit}
                    onDelete={() => deleteCard(i)}
                  />
                );
              })}
              {streamingNarration && (
                <div className="h-20 animate-pulse rounded-[20px] border border-border bg-white" />
              )}
            </div>
          ) : streamingNarration ? (
            <div className="space-y-3">
              {[1, 2, 3].map((k) => (
                <div
                  key={k}
                  className="h-20 animate-pulse rounded-[20px] border border-border bg-white"
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
              ? `${lockedCount} stor${lockedCount === 1 ? "y" : "ies"} locked and enriched. Save to continue.`
              : "Lock at least one story to continue."}
          </p>
          <button
            type="button"
            onClick={() => {
              if (lockedCount === 0) return;
              // Pass locked chunk metadata back to OnboardingFlow via onContinue
              // We do this by attaching lockedChunks to window state temporarily
              // The cleaner pattern would be a callback prop but to avoid changing
              // the OnboardingFlow interface we store in a module-level ref.
              storeLockedChunks(buildLockedChunks());
              onContinue();
            }}
            disabled={busy || lockedCount === 0}
            title={lockedCount === 0 ? "Lock at least one story first" : undefined}
            className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-60"
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

// ── StoryCard component ───────────────────────────────────────────────────

function StoryCard({
  card,
  index,
  cardState,
  isEditing,
  editingHeading,
  editingBody,
  onEditHeadingChange,
  onEditBodyChange,
  onLock,
  onUnlock,
  onStartEdit,
  onCancelEdit,
  onCommitEdit,
  onDelete,
}: {
  card: { heading: string; body: string };
  index: number;
  cardState: CardState;
  isEditing: boolean;
  editingHeading: string;
  editingBody: string;
  onEditHeadingChange: (v: string) => void;
  onEditBodyChange: (v: string) => void;
  onLock: () => void;
  onUnlock: () => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onCommitEdit: () => void;
  onDelete: () => void;
}) {
  const { locked, status } = cardState;

  const cardCls = locked
    ? "rounded-[20px] border border-tertiary-200 bg-tertiary-50/40 p-4 shadow-sm transition"
    : "rounded-[20px] border border-border bg-surface p-4 shadow-sm transition";

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

  return (
    <div className={cardCls} data-story-index={index}>
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-semibold text-foreground leading-snug">
          {card.heading}
        </h4>
        <div className="flex shrink-0 items-center gap-1.5">
          {/* Status badge */}
          {locked && status === "enriching" && (
            <span className="inline-flex items-center gap-1 rounded-lg bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-medium text-amber-700">
              <span className="inline-block h-2.5 w-2.5 animate-spin rounded-full border-2 border-amber-400 border-t-transparent" />
              Enriching
            </span>
          )}
          {locked && status === "ready" && (
            <span className="inline-flex items-center gap-1 rounded-lg bg-green-50 border border-green-200 px-2 py-0.5 text-[10px] font-semibold text-green-700">
              ✓ Ready
            </span>
          )}
          {/* Edit button — only when unlocked and not in edit mode */}
          {!locked && (
            <button
              type="button"
              onClick={onStartEdit}
              className="rounded-lg border border-border px-2 py-0.5 text-[11px] font-medium text-muted transition hover:border-accent hover:text-accent"
              title="Edit this story"
            >
              ✏
            </button>
          )}
          {/* Delete button — only when unlocked */}
          {!locked && (
            <button
              type="button"
              onClick={onDelete}
              className="rounded-lg border border-border px-2 py-0.5 text-[11px] font-medium text-muted transition hover:border-red-400 hover:text-red-500"
              title="Delete this story"
            >
              ✕
            </button>
          )}
          {/* Lock / Unlock toggle */}
          {locked ? (
            <button
              type="button"
              onClick={onUnlock}
              disabled={status === "enriching"}
              className="inline-flex items-center gap-1.5 rounded-lg border border-tertiary-500 bg-tertiary-500/10 px-2.5 py-1 text-xs font-semibold text-tertiary-700 transition hover:bg-tertiary-500/20 disabled:opacity-60"
              title="Click to unlock and edit"
            >
              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                <path
                  fillRule="evenodd"
                  d="M12 1.5a5.25 5.25 0 00-5.25 5.25v3a3 3 0 00-3 3v6.75a3 3 0 003 3h10.5a3 3 0 003-3v-6.75a3 3 0 00-3-3v-3c0-2.9-2.35-5.25-5.25-5.25zm3.75 8.25v-3a3.75 3.75 0 10-7.5 0v3h7.5z"
                  clipRule="evenodd"
                />
              </svg>
              Locked
            </button>
          ) : (
            <button
              type="button"
              onClick={onLock}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-2.5 py-1 text-xs font-semibold text-foreground transition hover:border-tertiary-500 hover:bg-tertiary-500/10 hover:text-tertiary-700"
              title="Lock to enrich this story"
            >
              <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.5 10.5V6.75a4.5 4.5 0 119 0v3.75M3.75 21.75h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H3.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
                />
              </svg>
              Lock
            </button>
          )}
        </div>
      </div>
      <div className="mt-2 space-y-1.5 text-xs leading-relaxed text-muted">
        {card.body
          .split(/\n+/)
          .filter(Boolean)
          .map((line, j) => (
            <p key={j}>{line.replace(/^[-*•]\s*/, "")}</p>
          ))}
      </div>
      {/* Enrichment tags — shown when ready */}
      {locked && status === "ready" && cardState.enrichedMeta?.tags && cardState.enrichedMeta.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {cardState.enrichedMeta.tags.slice(0, 4).map((tag: string, t: number) => (
            <span key={t} className="rounded-[8px] bg-tertiary-100 px-2 py-0.5 text-[10px] font-medium text-tertiary-700">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Module-level locked chunks store (avoids prop threading) ─────────────────
// OnboardingFlow reads this before calling /api/career/upload

let _lockedChunksStore: { heading: string; text: string; meta: Record<string, unknown> }[] = [];

export function storeLockedChunks(chunks: typeof _lockedChunksStore) {
  _lockedChunksStore = chunks;
}

export function getLockedChunks(): typeof _lockedChunksStore {
  return _lockedChunksStore;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function buildCareerContext(experiences: ParsedExperience[]): string {
  if (!experiences?.length) return "";
  const current = experiences[0];
  const prev = experiences.slice(1, 3).map((e) => e.company).filter(Boolean);
  let ctx = `${current.role} at ${current.company}`;
  if (prev.length > 0) ctx += `, prev ${prev.join(", ")}`;
  return ctx;
}

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
