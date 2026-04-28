"use client";

// Wave 2 / Screen 05 — Profile highlights grid.
// Design handoff: specs/design-handoff-2026-04-18/ → screens-build.jsx Screen05.
//
// LOCK/UNLOCK MODEL (v2):
//   - Each nugget has Lock / Unlock / Delete / Edit actions.
//   - Lock → immediate embed for that nugget only.
//   - Unlock → nugget becomes editable; embedding cleared.
//   - Delete → only when unlocked.
//   - Save and continue → stamps profile_submitted_at, disables all buttons.
//
// STREAMING (Bug 6 fix):
//   - Polls /api/nuggets/list every 4s while extraction is in progress.
//   - New nuggets appear one-by-one as enrich-chunk calls resolve.
//   - No manual refresh needed.

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { track } from "@/lib/analytics";
import { HighlightFollowUpModal } from "./HighlightFollowUpModal";
import {
  HighlightEditorModal,
  type EditableNugget,
} from "./HighlightEditorModal";

type Nugget = {
  id: string;
  answer: string;
  nugget_text?: string | null;
  company?: string | null;
  role?: string | null;
  section_type?: string | null;
  importance?: string | null;
  event_date?: string | null;
  created_at?: string | null;
  is_embedded?: boolean;
  locked_at?: string | null;
  profile_submitted_at?: string | null;
};

type NuggetGroup = {
  key: string;
  company: string;
  role: string;
  items: Nugget[];
  latestDate: string;
};

function groupAndSortNuggets(nuggets: Nugget[]): NuggetGroup[] {
  const groups = new Map<string, NuggetGroup>();
  for (const n of nuggets) {
    const key = `${n.company ?? ""}::${n.role ?? ""}`;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        company: n.company ?? "",
        role: n.role ?? "",
        items: [],
        latestDate: "",
      });
    }
    groups.get(key)!.items.push(n);
  }
  for (const g of groups.values()) {
    g.items.sort((a, b) => {
      const da = a.event_date || a.created_at || "";
      const db = b.event_date || b.created_at || "";
      return db.localeCompare(da);
    });
    g.latestDate = g.items[0]?.event_date || g.items[0]?.created_at || "";
  }
  return [...groups.values()].sort((a, b) =>
    b.latestDate.localeCompare(a.latestDate)
  );
}

type NuggetStatus = {
  total_extracted: number;
  total_locked: number;
  total_embedded: number;
  embed_queued: number;
  ready: boolean;
  profile_ready?: boolean;
};

const STEPS = [
  { n: 1, label: "Resume", state: "done" },
  { n: 2, label: "Profile", state: "active" },
  { n: 3, label: "Preferences", state: "todo" },
  { n: 4, label: "Broadcast", state: "todo" },
  { n: 5, label: "First match", state: "todo" },
] as const;

const SOURCE_CHIP_CLS = "bg-[#EDF2F7] text-[#4A5568]";

function sourceLabel(n: Nugget): string {
  const sec = (n.section_type ?? "").toLowerCase();
  if (n.company) return `from your ${n.company} role`;
  if (sec.includes("education")) return "from your education";
  if (sec.includes("certif")) return "from your certifications";
  if (sec.includes("project")) return "from your projects";
  if (sec.includes("skill")) return "from your skills";
  return "from your resume";
}

function shortTitle(n: Nugget): string {
  const t = (n.nugget_text || n.answer || "").trim();
  const firstSentence = t.split(/[.!?](\s|$)/)[0] ?? t;
  return firstSentence.length > 90
    ? firstSentence.slice(0, 87) + "…"
    : firstSentence;
}

function shortDescription(n: Nugget): string {
  const t = (n.answer || "").trim();
  const rest = t.split(/[.!?](\s|$)/).slice(1).join(" ").trim();
  if (!rest) return "";
  return rest.length > 140 ? rest.slice(0, 137) + "…" : rest;
}

// ------- Lock / Unlock button component -------

function LockButton({
  nugget,
  disabled,
  onLocked,
  onUnlocked,
}: {
  nugget: Nugget;
  disabled: boolean;
  onLocked: (id: string) => void;
  onUnlocked: (id: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const isLocked = !!nugget.locked_at;

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (busy || disabled) return;
    setBusy(true);
    try {
      const res = await fetch("/api/nuggets/lock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: nugget.id,
          action: isLocked ? "unlock" : "lock",
        }),
      });
      if (res.ok) {
        if (isLocked) {
          onUnlocked(nugget.id);
        } else {
          onLocked(nugget.id);
        }
      }
    } finally {
      setBusy(false);
    }
  };

  if (isLocked) {
    return (
      <button
        type="button"
        onClick={handleToggle}
        disabled={busy || disabled}
        className="inline-flex items-center gap-1.5 rounded-lg border border-tertiary-500 bg-tertiary-500/10 px-2.5 py-1 text-xs font-semibold text-tertiary-700 transition hover:bg-tertiary-500/20 disabled:opacity-60"
        title="Click to unlock and edit"
      >
        {busy ? (
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-tertiary-500 border-t-transparent" />
        ) : (
          <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
            <path
              fillRule="evenodd"
              d="M12 1.5a5.25 5.25 0 00-5.25 5.25v3a3 3 0 00-3 3v6.75a3 3 0 003 3h10.5a3 3 0 003-3v-6.75a3 3 0 00-3-3v-3c0-2.9-2.35-5.25-5.25-5.25zm3.75 8.25v-3a3.75 3.75 0 10-7.5 0v3h7.5z"
              clipRule="evenodd"
            />
          </svg>
        )}
        Locked
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleToggle}
      disabled={busy || disabled}
      className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-2.5 py-1 text-xs font-semibold text-foreground transition hover:border-tertiary-500 hover:bg-tertiary-500/10 hover:text-tertiary-700 disabled:opacity-60"
      title="Lock to embed this nugget"
    >
      {busy ? (
        <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-border border-t-foreground" />
      ) : (
        <svg
          className="h-3 w-3"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M13.5 10.5V6.75a4.5 4.5 0 119 0v3.75M3.75 21.75h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H3.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
          />
        </svg>
      )}
      Lock
    </button>
  );
}

export function ProfileHighlightsView() {
  const router = useRouter();
  const [nuggets, setNuggets] = useState<Nugget[]>([]);
  const [status, setStatus] = useState<NuggetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeNugget, setActiveNugget] = useState<Nugget | null>(null);
  const [editor, setEditor] = useState<
    | { mode: "create"; existing: null }
    | { mode: "edit"; existing: EditableNugget }
    | null
  >(null);
  const [profileReadyToast, setProfileReadyToast] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    ids: string[];
    label: string;
  } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [saving, setSaving] = useState(false);

  // Track known nugget IDs so we can animate new arrivals
  const knownIds = useRef(new Set<string>());

  const loadNuggets = useCallback(async () => {
    try {
      const listRes = await fetch("/api/nuggets/list?limit=48", {
        cache: "no-store",
      });
      const listJson = listRes.ok ? await listRes.json() : { nuggets: [] };
      const incoming: Nugget[] = listJson.nuggets ?? [];

      setNuggets(incoming);

      // Check if profile was already submitted (e.g. user navigated back)
      if (incoming.length > 0 && incoming[0].profile_submitted_at) {
        setSubmitted(true);
      }

      // Track seen ids
      incoming.forEach((n) => knownIds.current.add(n.id));
      setError("");
    } catch {
      setError("Couldn't load your profile. Try refreshing.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/nuggets/status", { cache: "no-store" });
      if (res.ok) {
        const json: NuggetStatus = await res.json();
        setStatus(json);
        return json;
      }
    } catch {
      // ignore — status is best-effort
    }
    return null;
  }, []);

  useEffect(() => {
    Promise.all([loadNuggets(), loadStatus()]);
  }, [loadNuggets, loadStatus]);

  // Streaming poll: re-fetch nugget list every 4s while extraction is
  // still in progress (total_extracted < expected 14, or no nuggets yet).
  // Stops when we have >=14 nuggets OR status shows extraction is done.
  // This surfaces nuggets one-by-one as they resolve (Bug 6 fix).
  useEffect(() => {
    // Don't poll once profile is submitted
    if (submitted) return;

    // Poll both list and status together
    const tick = async () => {
      const [listRes, statusRes] = await Promise.all([
        fetch("/api/nuggets/list?limit=48", { cache: "no-store" }).catch(
          () => null
        ),
        fetch("/api/nuggets/status", { cache: "no-store" }).catch(() => null),
      ]);

      if (listRes?.ok) {
        const json = await listRes.json();
        const incoming: Nugget[] = json.nuggets ?? [];
        if (incoming.length > 0 && incoming[0].profile_submitted_at) {
          setSubmitted(true);
        }
        // Merge incoming nuggets — preserve local optimistic lock state
        setNuggets((prev) => {
          const prevMap = new Map(prev.map((n) => [n.id, n]));
          for (const n of incoming) {
            // Preserve local optimistic locked_at if we set it more recently
            const existing = prevMap.get(n.id);
            if (existing?.locked_at && !n.locked_at) {
              prevMap.set(n.id, { ...n, locked_at: existing.locked_at });
            } else {
              prevMap.set(n.id, n);
            }
          }
          return incoming.map((n) => prevMap.get(n.id) ?? n);
        });
        incoming.forEach((n) => knownIds.current.add(n.id));
      }

      if (statusRes?.ok) {
        const s: NuggetStatus = await statusRes.json();
        setStatus(s);
        if (s.profile_ready ?? s.ready) {
          setProfileReadyToast(true);
          track({ event: "profile_fully_processed", properties: {} });
        }
      }
    };

    // Poll every 4s. Stop after 5 minutes.
    const intervalId = setInterval(tick, 4_000);
    const timeoutId = setTimeout(() => clearInterval(intervalId), 5 * 60_000);
    return () => {
      clearInterval(intervalId);
      clearTimeout(timeoutId);
    };
  }, [submitted]);

  const lockedCount = nuggets.filter((n) => !!n.locked_at).length;
  const total = status?.total_extracted ?? nuggets.length;
  const embedded = status?.total_embedded ?? 0;

  // ---- Optimistic lock/unlock state updates ----
  const handleNuggetLocked = (id: string) => {
    setNuggets((prev) =>
      prev.map((n) =>
        n.id === id ? { ...n, locked_at: new Date().toISOString() } : n
      )
    );
  };

  const handleNuggetUnlocked = (id: string) => {
    setNuggets((prev) =>
      prev.map((n) =>
        n.id === id ? { ...n, locked_at: null, is_embedded: false } : n
      )
    );
  };

  // ---- Save and continue ----
  const handleSaveAndContinue = async () => {
    if (lockedCount === 0 || saving || submitted) return;
    setSaving(true);
    try {
      await fetch("/api/nuggets/submit-profile", { method: "POST" });
      setSubmitted(true);
      track({ event: "career_profile_saved", properties: {} });
      router.push("/onboarding/preferences");
    } catch {
      setSaving(false);
    }
  };

  // ---- Delete ----
  const confirmDelete = (ids: string[], label: string) =>
    setDeleteConfirm({ ids, label });

  const executeDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    await Promise.all(
      deleteConfirm.ids.map((id) =>
        fetch(`/api/nuggets/${id}`, { method: "DELETE" })
      )
    );
    setNuggets((prev) => prev.filter((n) => !deleteConfirm.ids.includes(n.id)));
    setDeleteConfirm(null);
    setDeleting(false);
  };

  return (
    <div className="space-y-6">
      {/* Header: step indicator + skip */}
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div className="flex items-center gap-2 text-xs">
          {STEPS.map((s, i) => (
            <span key={s.n} className="flex items-center gap-2">
              <span
                className={
                  s.state === "active"
                    ? "rounded-[10px] bg-accent px-3 py-1.5 font-semibold text-white"
                    : s.state === "done"
                      ? "rounded-[10px] bg-accent/10 px-3 py-1.5 font-medium text-primary-700"
                      : "rounded-[10px] border border-border bg-white px-3 py-1.5 font-medium text-muted"
                }
              >
                {s.n} {s.state === "done" ? `${s.label} ✓` : s.label}
              </span>
              {i < STEPS.length - 1 && <span className="h-px w-4 bg-border" />}
            </span>
          ))}
        </div>
        <button
          type="button"
          onClick={() => router.push("/onboarding/preferences")}
          className="text-xs text-muted transition hover:text-foreground"
        >
          Skip — I&apos;ll add later
        </button>
      </div>

      {/* Headline */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-xl">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-tertiary-700">
            Your profile
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground">
            Here&apos;s what stood out from your resume.
          </h1>
          <p className="mt-1 text-sm text-muted">
            Lock the highlights that matter most. Locked highlights are
            immediately embedded — unlocked ones are ignored.
          </p>
        </div>
        <div className="text-right">
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setEditor({ mode: "create", existing: null })}
              disabled={submitted}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-4 py-2.5 text-sm font-semibold text-foreground transition hover:border-tertiary-500 hover:text-tertiary-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <svg
                className="h-3.5 w-3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 4.5v15m7.5-7.5h-15"
                />
              </svg>
              Add highlight
            </button>
            <button
              type="button"
              onClick={handleSaveAndContinue}
              disabled={lockedCount === 0 || saving || submitted}
              className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-50"
              title={lockedCount === 0 ? "Lock at least one highlight to continue" : undefined}
            >
              {saving ? (
                <>
                  <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Saving…
                </>
              ) : submitted ? (
                "Saved"
              ) : (
                <>
                  Save and continue
                  {lockedCount > 0 && (
                    <span className="rounded-full bg-white/20 px-1.5 py-0.5 text-xs">
                      {lockedCount}
                    </span>
                  )}
                  <svg
                    className="h-3.5 w-3.5"
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
                </>
              )}
            </button>
          </div>
          <p className="mt-2 text-xs text-muted">
            {submitted
              ? "Profile saved."
              : lockedCount === 0
                ? "Lock at least one highlight to continue."
                : `${lockedCount} highlight${lockedCount === 1 ? "" : "s"} locked.`}
          </p>
        </div>
      </div>

      {/* Progress strip — while extraction is in progress */}
      {!submitted && total > 0 && embedded < total && (
        <div
          className="flex items-center gap-4 rounded-xl border p-3.5"
          style={{
            background: "rgba(139, 92, 246, 0.05)",
            borderColor: "rgba(139, 92, 246, 0.2)",
          }}
        >
          <span className="inline-flex items-center gap-2 text-sm font-semibold text-tertiary-700">
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: "#8B5CF6",
                animation: "pulse 1s ease-in-out infinite",
                display: "inline-block",
              }}
            />
            Getting your profile ready
          </span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-tertiary-500/15">
            <div
              className="h-full rounded-full bg-tertiary-500 transition-all"
              style={{
                width: `${total > 0 ? Math.min(100, Math.round((nuggets.length / Math.max(total, 14)) * 100)) : 0}%`,
              }}
            />
          </div>
          <span className="text-xs text-muted">
            {nuggets.length} of ~{total || 14} highlights found
          </span>
          <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
        </div>
      )}

      {/* Lock hint banner — shown when user hasn't locked anything yet */}
      {!submitted && nuggets.length > 0 && lockedCount === 0 && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <svg
            className="h-4 w-4 shrink-0 text-amber-600"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
          <p className="text-xs text-amber-800">
            <strong>Lock highlights to embed them.</strong> Only locked
            highlights power your job matches. Click Lock on any card below.
          </p>
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-2xl border border-border bg-white"
            />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      ) : nuggets.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center">
          <p className="text-sm text-muted">
            We haven&apos;t extracted any highlights yet. Try uploading your
            resume again — or paste a richer version.
          </p>
          <Link
            href="/onboarding"
            className="mt-3 inline-block rounded-lg bg-cta px-4 py-2 text-xs font-semibold text-white"
          >
            Back to resume upload
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          {groupAndSortNuggets(nuggets).map((group) => (
            <div key={group.key}>
              {(group.company || group.role) && (
                <div className="mb-2.5 flex items-center justify-between">
                  <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted">
                    {[group.company, group.role].filter(Boolean).join(" · ")}
                  </p>
                  {!submitted && (
                    <button
                      type="button"
                      onClick={() =>
                        confirmDelete(
                          group.items
                            .filter((i) => !i.locked_at)
                            .map((i) => i.id),
                          `${[group.company, group.role].filter(Boolean).join(" · ")} (unlocked highlights)`
                        )
                      }
                      disabled={group.items.every((i) => !!i.locked_at)}
                      className="text-[11px] text-muted transition hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      Delete unlocked
                    </button>
                  )}
                </div>
              )}
              <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
                {group.items.map((n) => {
                  const isLocked = !!n.locked_at;
                  return (
                    <div
                      key={n.id}
                      className={`group relative rounded-2xl border bg-white p-4 text-left transition ${
                        isLocked
                          ? "border-tertiary-500/40 shadow-sm"
                          : "border-border hover:border-accent hover:shadow-md"
                      }`}
                    >
                      {/* Top row: source chip + action icons */}
                      <div className="flex items-start justify-between gap-2">
                        <span
                          className={`rounded-[10px] px-2.5 py-0.5 text-[11px] font-medium ${SOURCE_CHIP_CLS}`}
                        >
                          {sourceLabel(n)}
                        </span>
                        <div className="flex items-center gap-1.5">
                          {/* Edit icon — only when unlocked and not submitted */}
                          {!isLocked && !submitted && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditor({
                                  mode: "edit",
                                  existing: {
                                    id: n.id,
                                    nugget_text: n.nugget_text,
                                    answer: n.answer,
                                    company: n.company,
                                    role: n.role,
                                  },
                                });
                              }}
                              aria-label="Edit highlight"
                              className="text-muted transition hover:text-accent"
                            >
                              <svg
                                className="h-4 w-4"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1.5"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
                                />
                              </svg>
                            </button>
                          )}
                          {/* Delete icon — only when unlocked and not submitted */}
                          {!isLocked && !submitted && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                confirmDelete(
                                  [n.id],
                                  shortTitle(n) || "this highlight"
                                );
                              }}
                              aria-label="Delete highlight"
                              className="text-muted transition hover:text-red-500"
                            >
                              <svg
                                className="h-4 w-4"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1.5"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                                />
                              </svg>
                            </button>
                          )}
                          {/* Embedded indicator */}
                          {n.is_embedded && (
                            <span
                              className="inline-block h-2 w-2 rounded-full bg-green-500"
                              title="Embedded"
                            />
                          )}
                        </div>
                      </div>

                      {/* Card body — clicking opens follow-up modal */}
                      <button
                        type="button"
                        onClick={() => !submitted && setActiveNugget(n)}
                        className="block w-full text-left"
                      >
                        <h4 className="mt-2.5 text-sm font-semibold leading-snug text-foreground">
                          {shortTitle(n)}
                        </h4>
                        {shortDescription(n) && (
                          <p className="mt-1.5 text-xs leading-snug text-muted">
                            {shortDescription(n)}
                          </p>
                        )}
                        {!isLocked && !submitted && (
                          <div className="mt-3 text-[11px] font-semibold text-tertiary-700 opacity-0 transition group-hover:opacity-100">
                            Add depth →
                          </div>
                        )}
                      </button>

                      {/* Lock/Unlock button — bottom of card */}
                      <div className="mt-3 flex items-center justify-between">
                        <LockButton
                          nugget={n}
                          disabled={submitted}
                          onLocked={handleNuggetLocked}
                          onUnlocked={handleNuggetUnlocked}
                        />
                        {isLocked && n.is_embedded && (
                          <span className="text-[10px] font-medium text-green-600">
                            Embedded
                          </span>
                        )}
                        {isLocked && !n.is_embedded && (
                          <span className="text-[10px] font-medium text-amber-600">
                            Queued…
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Bulk upload soft CTA */}
      <div className="flex items-center justify-between rounded-xl border border-dashed border-border bg-white px-5 py-4">
        <div>
          <p className="text-sm font-medium text-foreground">
            Have everything written up already?
          </p>
          <p className="mt-0.5 text-xs text-muted">
            Upload a career file — we&apos;ll fold it into your profile.
          </p>
        </div>
        <Link
          href="/dashboard/profile#bulk-upload"
          className="rounded-lg border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
        >
          Upload a file →
        </Link>
      </div>

      {/* Delete confirm dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-sm rounded-2xl border border-border bg-white p-6 shadow-xl">
            <h3 className="text-sm font-semibold text-foreground">
              Delete highlight{deleteConfirm.ids.length > 1 ? "s" : ""}?
            </h3>
            <p className="mt-2 text-xs text-muted">
              <span className="font-medium text-foreground">
                {deleteConfirm.label}
              </span>
              {deleteConfirm.ids.length > 1
                ? ` — all ${deleteConfirm.ids.length} highlights will be permanently deleted.`
                : " will be permanently deleted."}
            </p>
            <div className="mt-5 flex justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setDeleteConfirm(null)}
                disabled={deleting}
                className="rounded-lg border border-border px-4 py-2 text-xs font-semibold text-foreground transition hover:border-accent"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={executeDelete}
                disabled={deleting}
                className="rounded-lg bg-red-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-red-600 disabled:opacity-60"
              >
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Follow-up modal (click card) */}
      {activeNugget && (
        <HighlightFollowUpModal
          nugget={activeNugget}
          onClose={() => {
            setActiveNugget(null);
            loadNuggets();
          }}
        />
      )}

      {/* Edit / Create modal */}
      {editor && (
        <HighlightEditorModal
          mode={editor.mode}
          existing={editor.mode === "edit" ? editor.existing : null}
          onClose={(saved) => {
            setEditor(null);
            if (saved) loadNuggets();
          }}
        />
      )}

      {/* Toast */}
      {profileReadyToast && (
        <div
          className="fixed bottom-6 left-6 z-40 flex max-w-sm items-center gap-3 rounded-xl border bg-white p-3.5 shadow-lg"
          style={{ borderColor: "rgba(139, 92, 246, 0.3)" }}
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-tertiary-500/10 text-tertiary-700">
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold">Your profile is ready</div>
            <div className="text-xs text-muted">
              Your resume and matches will be sharper now.
            </div>
          </div>
          <button
            type="button"
            onClick={() => setProfileReadyToast(false)}
            className="text-muted hover:text-foreground"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
