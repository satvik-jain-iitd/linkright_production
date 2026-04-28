"use client";

// Wave 2 / Screen 05 — Profile highlights streaming view.
//
// Bug 1 redesign:
//   - NO Lock/Unlock buttons (lock concept moved to story screen).
//   - NO Edit button on individual nuggets.
//   - Pure streaming view: polls /api/nuggets/list?embedded=true every 2s.
//   - Shows ONLY nuggets where embedding IS NOT NULL (is_embedded = true).
//   - Per-nugget: [Delete] + [Add more details] (follow-up modal).
//   - Per-chunk group: [Delete group] via DELETE /api/nuggets/by-chunk/[chunkId].
//   - Continue → /onboarding/preferences. Enabled when embeddedCount >= 1.

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { track } from "@/lib/analytics";
import { HighlightFollowUpModal } from "./HighlightFollowUpModal";

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
  source_chunk_id?: string | null;
};

type NuggetGroup = {
  key: string;      // source_chunk_id if available, else company::role
  chunkId: string | null;
  company: string;
  role: string;
  items: Nugget[];
  latestDate: string;
};

function groupAndSortNuggets(nuggets: Nugget[]): NuggetGroup[] {
  const groups = new Map<string, NuggetGroup>();
  for (const n of nuggets) {
    // Group by source_chunk_id (preferred) or fall back to company::role
    const key = n.source_chunk_id
      ? `chunk::${n.source_chunk_id}`
      : `${n.company ?? ""}::${n.role ?? ""}`;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        chunkId: n.source_chunk_id ?? null,
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
  return [...groups.values()].sort((a, b) => b.latestDate.localeCompare(a.latestDate));
}

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeNugget, setActiveNugget] = useState<Nugget | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<
    { ids: string[]; label: string; chunkId?: string } | null
  >(null);
  const [deleting, setDeleting] = useState(false);
  const [profileReadyToast, setProfileReadyToast] = useState(false);

  // Load embedded-only nuggets
  const loadNuggets = useCallback(async () => {
    try {
      // Only fetch embedded nuggets — pure streaming view
      const listRes = await fetch("/api/nuggets/list?limit=48&embedded=true", {
        cache: "no-store",
      });
      const listJson = listRes.ok ? await listRes.json() : { nuggets: [] };
      setNuggets(listJson.nuggets ?? []);
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

  // Poll every 2s — show new nuggets as they get embedded one-by-one
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const res = await fetch("/api/nuggets/list?limit=48&embedded=true", {
          cache: "no-store",
        });
        if (res.ok) {
          const json = await res.json();
          const incoming: Nugget[] = json.nuggets ?? [];
          setNuggets((prev) => {
            // Detect new arrivals — trigger "ready" toast if count jumped
            if (incoming.length > prev.length && incoming.length >= 1) {
              setProfileReadyToast(true);
              track({ event: "profile_nugget_embedded", properties: { count: incoming.length } });
            }
            return incoming;
          });
        }
      } catch {
        // silent — next tick will retry
      }
    }, 2000);

    // Stop polling after 5 minutes
    const stop = setTimeout(() => clearInterval(id), 5 * 60 * 1000);
    return () => {
      clearInterval(id);
      clearTimeout(stop);
    };
  }, []);

  const embeddedCount = nuggets.length; // list already filtered to embedded=true

  const goToPreferences = () => router.push("/onboarding/preferences");

  // Delete individual nuggets
  const confirmDelete = (ids: string[], label: string, chunkId?: string) =>
    setDeleteConfirm({ ids, label, chunkId });

  const executeDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);

    // Delete group via by-chunk endpoint if chunkId is provided
    if (deleteConfirm.chunkId) {
      await fetch(`/api/nuggets/by-chunk/${deleteConfirm.chunkId}`, {
        method: "DELETE",
      });
      setNuggets((prev) => prev.filter((n) => n.source_chunk_id !== deleteConfirm.chunkId));
    } else {
      // Individual deletes
      await Promise.all(
        deleteConfirm.ids.map((id) =>
          fetch(`/api/nuggets/${id}`, { method: "DELETE" }),
        ),
      );
      setNuggets((prev) => prev.filter((n) => !deleteConfirm.ids.includes(n.id)));
    }

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
            Your highlights are loading in.
          </h1>
          <p className="mt-1 text-sm text-muted">
            Each locked story is being turned into searchable highlights. Click &quot;Add more details&quot; to expand any card.
          </p>
        </div>
        <button
          type="button"
          onClick={goToPreferences}
          disabled={embeddedCount < 1}
          title={embeddedCount < 1 ? "Waiting for your first highlight to load" : undefined}
          className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continue →
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

      {/* Streaming progress strip — shown while embedding is still running */}
      {embeddedCount === 0 && !loading && (
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
            Processing your locked stories…
          </span>
          <span className="text-xs text-muted">highlights appear as they&apos;re ready</span>
          <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
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
            No highlights yet — your locked stories are being processed.
            This usually takes 10–30 seconds.
          </p>
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
                        group.chunkId ?? undefined,
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
                    {/* Source chip */}
                    <span
                      className={`rounded-[10px] px-2.5 py-0.5 text-[11px] font-medium ${SOURCE_CHIP_CLS}`}
                    >
                      {sourceLabel(n)}
                    </span>

                    {/* Title */}
                    <h4 className="mt-2.5 text-sm font-semibold leading-snug text-foreground">
                      {shortTitle(n)}
                    </h4>
                    {shortDescription(n) && (
                      <p className="mt-1.5 text-xs leading-snug text-muted">
                        {shortDescription(n)}
                      </p>
                    )}

                    {/* Actions: Delete + Add more details */}
                    <div className="mt-3 flex items-center justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => setActiveNugget(n)}
                        className="text-[11px] font-semibold text-tertiary-700 transition hover:text-tertiary-600"
                      >
                        Add more details →
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          confirmDelete([n.id], shortTitle(n) || "this highlight");
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
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete confirm dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-sm rounded-2xl border border-border bg-white p-6 shadow-xl">
            <h3 className="text-sm font-semibold text-foreground">
              Delete highlight{deleteConfirm.ids.length > 1 ? "s" : ""}?
            </h3>
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

      {/* Follow-up modal (Add more details) */}
      {activeNugget && (
        <HighlightFollowUpModal
          nugget={activeNugget}
          onClose={() => {
            setActiveNugget(null);
            loadNuggets();
          }}
        />
      )}

      {/* Toast: first highlight appeared */}
      {profileReadyToast && embeddedCount >= 1 && (
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
            <div className="text-sm font-semibold">
              {embeddedCount} highlight{embeddedCount === 1 ? "" : "s"} ready
            </div>
            <div className="text-xs text-muted">More are loading in the background.</div>
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
