"use client";

// Wave 2 / Screen 05 — Profile highlights grid.
// Design handoff: specs/design-handoff-2026-04-18/ → screens-build.jsx Screen05.
//
// Reads career_nuggets via /api/nuggets/list + /api/nuggets/status.
// Each card clickable → opens HighlightFollowUpModal (Screen 06).
// "Continue to find jobs" → /onboarding/preferences (then /onboarding/find).
// "Skip" → /onboarding/preferences.
// "Upload a career file" → /dashboard/profile (future bulk upload surface).

import { useCallback, useEffect, useState } from "react";
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
      groups.set(key, { key, company: n.company ?? "", role: n.role ?? "", items: [], latestDate: "" });
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
  return [...groups.values()].sort((a, b) => b.latestDate.localeCompare(a.latestDate));
}

type NuggetStatus = {
  total_extracted: number;
  total_embedded: number;
  embed_queued: number;
  ready: boolean;
};

const STEPS = [
  { n: 1, label: "Resume", state: "done" },
  { n: 2, label: "Profile", state: "active" },
  { n: 3, label: "Preferences", state: "todo" },
  { n: 4, label: "Broadcast", state: "todo" },
  { n: 5, label: "First match", state: "todo" },
] as const;

// v2 design rule: highlight cards are monochrome. The page eyebrow already
// signals the memory pillar (purple) — cards shouldn't compete. A single
// neutral source chip reads as "provenance label", not "decorative colour".
const SOURCE_CHIP_CLS =
  "bg-[#EDF2F7] text-[#4A5568]";

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
  return firstSentence.length > 90 ? firstSentence.slice(0, 87) + "…" : firstSentence;
}

function shortDescription(n: Nugget): string {
  const t = (n.answer || "").trim();
  const rest = t.split(/[.!?](\s|$)/).slice(1).join(" ").trim();
  if (!rest) return "";
  return rest.length > 140 ? rest.slice(0, 137) + "…" : rest;
}

export function ProfileHighlightsView() {
  const router = useRouter();
  const [nuggets, setNuggets] = useState<Nugget[]>([]);
  const [status, setStatus] = useState<NuggetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeNugget, setActiveNugget] = useState<Nugget | null>(null);
  const [editor, setEditor] = useState<
    { mode: "create"; existing: null } | { mode: "edit"; existing: EditableNugget } | null
  >(null);
  const [profileReadyToast, setProfileReadyToast] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<
    { ids: string[]; label: string } | null
  >(null);
  const [deleting, setDeleting] = useState(false);

  const loadNuggets = useCallback(async () => {
    try {
      const [listRes, statusRes] = await Promise.all([
        fetch("/api/nuggets/list?limit=48", { cache: "no-store" }),
        fetch("/api/nuggets/status", { cache: "no-store" }),
      ]);
      const listJson = listRes.ok ? await listRes.json() : { nuggets: [] };
      const statusJson = statusRes.ok ? await statusRes.json() : null;
      setNuggets(listJson.nuggets ?? []);
      setStatus(statusJson);
      setError("");
    } catch {
      setError("Couldn't load your profile. Try refreshing.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNuggets();
  }, [loadNuggets]);

  // One-time status fetch on mount so polling starts even if loadNuggets is slow.
  useEffect(() => {
    fetch("/api/nuggets/status", { cache: "no-store" })
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => {});
  }, []);

  // Poll embedding status until fully embedded (max ~3 min).
  // Also re-fetches nuggets on every tick so the list auto-updates without a hard refresh.
  useEffect(() => {
    if (status?.ready) {
      setProfileReadyToast(true);
      loadNuggets();
      return;
    }
    if (!status) return;
    const id = setInterval(async () => {
      const res = await fetch("/api/nuggets/status", { cache: "no-store" });
      if (res.ok) {
        const json: NuggetStatus = await res.json();
        setStatus(json);
        if (json.total_extracted > 0) {
          loadNuggets();
        }
        if (json.ready) {
          setProfileReadyToast(true);
          track({ event: "profile_fully_processed", properties: {} });
          clearInterval(id);
        }
      }
    }, 6000);
    const stop = setTimeout(() => clearInterval(id), 3 * 60 * 1000);
    return () => {
      clearInterval(id);
      clearTimeout(stop);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.ready]);

  const total = status?.total_extracted ?? nuggets.length;
  const embedded = status?.total_embedded ?? nuggets.filter((n) => n.is_embedded).length;
  const processedPct = total > 0 ? Math.min(100, Math.round((embedded / total) * 100)) : 0;

  const goToPreferences = () => router.push("/onboarding/preferences");

  const confirmDelete = (ids: string[], label: string) =>
    setDeleteConfirm({ ids, label });

  const executeDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    await Promise.all(
      deleteConfirm.ids.map((id) =>
        fetch(`/api/nuggets/${id}`, { method: "DELETE" }),
      ),
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
          onClick={goToPreferences}
          className="text-xs text-muted transition hover:text-foreground"
        >
          Skip — I&apos;ll add later
        </button>
      </div>

      {/* Headline + primary CTA */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-xl">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-tertiary-700">
            Your profile
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground">
            Here&apos;s what stood out from your resume.
          </h1>
          <p className="mt-1 text-sm text-muted">
            Click any card to add more depth. The more we know, the better every match gets.
          </p>
        </div>
        <div className="text-right">
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setEditor({ mode: "create", existing: null })}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-4 py-2.5 text-sm font-semibold text-foreground transition hover:border-tertiary-500 hover:text-tertiary-700"
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
              onClick={goToPreferences}
              className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
            >
              Continue to find jobs
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
            </button>
          </div>
          <p className="mt-2 text-xs text-muted">You can always come back to this.</p>
        </div>
      </div>

      {/* Progress strip — s05a: only while still embedding */}
      {!status?.ready && (
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
                width: 8, height: 8, borderRadius: "50%", background: "#8B5CF6",
                animation: "pulse 1s ease-in-out infinite", display: "inline-block",
              }}
            />
            Getting your profile ready
          </span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-tertiary-500/15">
            <div
              className="h-full rounded-full bg-tertiary-500 transition-all"
              style={{ width: `${processedPct}%` }}
            />
          </div>
          <span className="text-xs text-muted">
            {embedded} of {total ? `~${total}` : "?"} highlights found
          </span>
          <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
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
            We haven&apos;t extracted any highlights yet. Try uploading your resume again — or
            paste a richer version.
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
                  <button
                    type="button"
                    onClick={() =>
                      confirmDelete(
                        group.items.map((i) => i.id),
                        `${[group.company, group.role].filter(Boolean).join(" · ")} (${group.items.length} highlight${group.items.length === 1 ? "" : "s"})`,
                      )
                    }
                    className="text-[11px] text-muted transition hover:text-red-500"
                  >
                    Delete group
                  </button>
                </div>
              )}
              <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
                {group.items.map((n) => (
                  <div
                    key={n.id}
                    className="group relative rounded-2xl border border-border bg-white p-4 text-left transition hover:border-accent hover:shadow-md"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className={`rounded-[10px] px-2.5 py-0.5 text-[11px] font-medium ${SOURCE_CHIP_CLS}`}>
                        {sourceLabel(n)}
                      </span>
                      <div className="flex items-center gap-1.5 opacity-0 transition group-hover:opacity-100">
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
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            confirmDelete(
                              [n.id],
                              shortTitle(n) || "this highlight",
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
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveNugget(n)}
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
                      <div className="mt-3 text-[11px] font-semibold text-tertiary-700 opacity-0 transition group-hover:opacity-100">
                        Add depth →
                      </div>
                    </button>
                  </div>
                ))}
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
            <h3 className="text-sm font-semibold text-foreground">Delete highlight{deleteConfirm.ids.length > 1 ? "s" : ""}?</h3>
            <p className="mt-2 text-xs text-muted">
              <span className="font-medium text-foreground">{deleteConfirm.label}</span>
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
          existing={editor.existing}
          onClose={(saved) => {
            setEditor(null);
            if (saved) loadNuggets();
          }}
        />
      )}

      {/* Toast */}
      {profileReadyToast && (
        <div className="fixed bottom-6 left-6 z-40 flex max-w-sm items-center gap-3 rounded-xl border bg-white p-3.5 shadow-lg"
             style={{ borderColor: "rgba(139, 92, 246, 0.3)" }}>
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
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
