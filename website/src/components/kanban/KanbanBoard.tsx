"use client";

import { useCallback, useEffect, useState } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from "@dnd-kit/core";
import { KanbanColumnComponent } from "./KanbanColumn";
import { ApplicationCard } from "./ApplicationCard";
import {
  KANBAN_COLUMNS,
  getColumnForStatus,
  getStatusForColumn,
  type Application,
  type JobScoreData,
} from "./types";
import { ScoreBreakdown } from "@/components/ScoreBreakdown";
import { CoverLetterView } from "@/components/CoverLetterView";
import { InterviewPrepView } from "@/components/InterviewPrepView";

function AddApplicationForm({ onCreated, onCancel }: { onCreated: (app: Application) => void; onCancel: () => void }) {
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [jdText, setJdText] = useState("");
  const [jdUrl, setJdUrl] = useState("");
  const [location, setLocation] = useState("");
  const [excitement, setExcitement] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!company.trim() || !role.trim()) { setError("Company and role are required"); return; }
    setSubmitting(true);
    setError("");

    try {
      const res = await fetch("/api/applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company: company.trim(),
          role: role.trim(),
          jd_text: jdText.trim() || null,
          jd_url: jdUrl.trim() || null,
          location: location.trim() || null,
          excitement,
        }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || "Failed to create"); setSubmitting(false); return; }

      // Build a full Application object from the response
      const newApp: Application = {
        id: data.application.id,
        company: data.application.company,
        role: data.application.role,
        status: data.application.status || "not_started",
        jd_text: jdText.trim() || null,
        jd_url: jdUrl.trim() || null,
        location: location.trim() || null,
        salary_range: null,
        excitement,
        notes: null,
        tags: [],
        applied_at: null,
        interview_at: null,
        deadline: null,
        created_at: data.application.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      onCreated(newApp);
    } catch {
      setError("Network error");
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/20" onClick={onCancel} />
      <form onSubmit={handleSubmit} className="relative bg-surface rounded-xl border border-border shadow-xl w-full max-w-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Add Application</h2>

        {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Company *</label>
            <input
              type="text" value={company} onChange={(e) => setCompany(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-accent/30 focus:border-accent outline-none"
              placeholder="e.g., Google"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Role *</label>
            <input
              type="text" value={role} onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-accent/30 focus:border-accent outline-none"
              placeholder="e.g., Senior PM"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Job Description (paste JD for scoring)</label>
          <textarea
            value={jdText} onChange={(e) => setJdText(e.target.value)}
            rows={4}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-accent/30 focus:border-accent outline-none resize-none"
            placeholder="Paste the full job description here..."
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Job URL</label>
            <input
              type="url" value={jdUrl} onChange={(e) => setJdUrl(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-accent/30 focus:border-accent outline-none"
              placeholder="https://..."
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Location</label>
            <input
              type="text" value={location} onChange={(e) => setLocation(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-accent/30 focus:border-accent outline-none"
              placeholder="e.g., Remote, Bangalore"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Excitement (1-5)</label>
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n} type="button" onClick={() => setExcitement(n)}
                className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                  n <= excitement ? "bg-accent text-white" : "bg-gray-100 text-gray-400 hover:bg-gray-200"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onCancel} className="rounded-lg px-4 py-2 text-sm text-muted hover:bg-background transition-colors">
            Cancel
          </button>
          <button
            type="submit" disabled={submitting}
            className="rounded-lg bg-cta px-4 py-2 text-sm font-medium text-white hover:bg-cta-hover transition-colors disabled:opacity-50"
          >
            {submitting ? "Adding..." : "Add Application"}
          </button>
        </div>
      </form>
    </div>
  );
}


export function KanbanBoard() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [scores, setScores] = useState<Record<string, JobScoreData>>({});
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeApp, setActiveApp] = useState<Application | null>(null);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [dragError, setDragError] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  // Fetch applications + scores
  useEffect(() => {
    async function load() {
      try {
        const [appsRes, scoresRes] = await Promise.all([
          fetch("/api/applications"),
          fetch("/api/applications/score"),
        ]);
        const appsData = await appsRes.json();
        const scoresData = await scoresRes.json();

        setApplications(appsData.applications ?? []);

        const scoreMap: Record<string, JobScoreData> = {};
        for (const s of scoresData.scores ?? []) {
          scoreMap[s.application_id] = s;
        }
        setScores(scoreMap);
      } catch (e) {
        console.error("Failed to load applications:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Group applications by column
  const columnApps: Record<string, Application[]> = {};
  for (const col of KANBAN_COLUMNS) {
    columnApps[col.id] = [];
  }
  for (const app of applications) {
    const colId = getColumnForStatus(app.status);
    if (columnApps[colId]) {
      columnApps[colId].push(app);
    }
  }

  // Drag handlers
  const handleDragStart = useCallback((event: DragStartEvent) => {
    const app = applications.find((a) => a.id === event.active.id);
    setActiveApp(app ?? null);
  }, [applications]);

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    setActiveApp(null);
    const { active, over } = event;
    if (!over) return;

    // Determine target column
    const overId = over.id as string;
    let targetColumnId: string | null = null;

    // Check if dropped on a column
    const isColumn = KANBAN_COLUMNS.some((c) => c.id === overId);
    if (isColumn) {
      targetColumnId = overId;
    } else {
      // Dropped on another card — find its column
      const overApp = applications.find((a) => a.id === overId);
      if (overApp) {
        targetColumnId = getColumnForStatus(overApp.status);
      }
    }

    if (!targetColumnId) return;

    const activeApp = applications.find((a) => a.id === active.id);
    if (!activeApp) return;

    const currentColumn = getColumnForStatus(activeApp.status);
    if (currentColumn === targetColumnId) return; // same column, no change

    const newStatus = getStatusForColumn(targetColumnId);

    // Optimistic update
    setApplications((prev) =>
      prev.map((a) => (a.id === active.id ? { ...a, status: newStatus } : a))
    );

    // Update server
    try {
      const res = await fetch("/api/applications", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: active.id, status: newStatus }),
      });
      if (!res.ok) {
        // Revert on failure
        setApplications((prev) =>
          prev.map((a) => (a.id === active.id ? { ...a, status: activeApp.status } : a))
        );
        setDragError("Failed to update status. Please try again.");
        setTimeout(() => setDragError(null), 4000);
      }
    } catch {
      // Revert
      setApplications((prev) =>
        prev.map((a) => (a.id === active.id ? { ...a, status: activeApp.status } : a))
      );
      setDragError("Network error. Please try again.");
      setTimeout(() => setDragError(null), 4000);
    }
  }, [applications]);

  // Score an application
  const handleScore = useCallback(async (appId: string) => {
    try {
      const res = await fetch("/api/applications/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ application_id: appId }),
      });
      const data = await res.json();

      if (data.status === "already_scored") {
        // Refetch score
        const scoreRes = await fetch(`/api/applications/score?application_id=${appId}`);
        const scoreData = await scoreRes.json();
        if (scoreData.score) {
          setScores((prev) => ({ ...prev, [appId]: scoreData.score }));
        }
      } else if (data.status === "scoring") {
        // Poll for result (simple polling, replace with realtime subscription later)
        const pollInterval = setInterval(async () => {
          const scoreRes = await fetch(`/api/applications/score?application_id=${appId}`);
          const scoreData = await scoreRes.json();
          if (scoreData.score) {
            setScores((prev) => ({ ...prev, [appId]: scoreData.score }));
            clearInterval(pollInterval);
          }
        }, 3000);
        // Stop polling after 60s
        setTimeout(() => clearInterval(pollInterval), 60000);
      }
    } catch (e) {
      console.error("Failed to score application:", e);
    }
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-muted">
        Loading applications...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Error toast */}
      {dragError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center justify-between">
          <span>{dragError}</span>
          <button onClick={() => setDragError(null)} className="ml-3 text-red-500 hover:text-red-700">&times;</button>
        </div>
      )}

      {/* Board header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-foreground">Applications</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">{applications.length} total</span>
          <button
            onClick={() => setShowAddForm(true)}
            className="rounded-lg bg-cta px-3 py-1.5 text-sm font-medium text-white hover:bg-cta-hover transition-colors"
          >
            + Add Application
          </button>
        </div>
      </div>

      {/* Add Application Form */}
      {showAddForm && (
        <AddApplicationForm
          onCreated={(app) => {
            setApplications((prev) => [app, ...prev]);
            setShowAddForm(false);
          }}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {/* Board */}
      <div className="flex-1 overflow-x-auto">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 pb-4 min-h-[400px]">
            {KANBAN_COLUMNS.map((col) => (
              <KanbanColumnComponent
                key={col.id}
                column={col}
                applications={columnApps[col.id]}
                scores={scores}
                onScoreApp={handleScore}
                onClickApp={setSelectedApp}
              />
            ))}
          </div>

          <DragOverlay>
            {activeApp && (
              <div className="w-64 opacity-90">
                <ApplicationCard
                  app={activeApp}
                  score={scores[activeApp.id] ?? null}
                />
              </div>
            )}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Detail drawer */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/20"
            onClick={() => setSelectedApp(null)}
          />
          <div className="relative w-full max-w-md bg-surface border-l border-border overflow-y-auto shadow-xl">
            <div className="sticky top-0 bg-surface border-b border-border px-4 py-3 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-foreground">{selectedApp.company}</h2>
                <p className="text-sm text-muted">{selectedApp.role}</p>
              </div>
              <button
                onClick={() => setSelectedApp(null)}
                className="rounded-lg p-1.5 text-muted hover:bg-background transition-colors"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-4 space-y-6">
              {/* Score breakdown */}
              {scores[selectedApp.id] && (
                <ScoreBreakdown score={scores[selectedApp.id]} />
              )}

              {!scores[selectedApp.id] && selectedApp.jd_text && (
                <button
                  onClick={() => {
                    handleScore(selectedApp.id);
                  }}
                  className="w-full rounded-lg bg-accent/10 px-4 py-2.5 text-sm font-medium text-accent hover:bg-accent/20 transition-colors"
                >
                  Score This Job
                </button>
              )}

              {/* Cover Letter */}
              {selectedApp.jd_text && (
                <CoverLetterView
                  applicationId={selectedApp.id}
                  resumeJobId={selectedApp.resume_jobs?.[0]?.id}
                />
              )}

              {/* Interview Prep — show for interview-stage applications */}
              {selectedApp.jd_text && ["screening", "interview"].includes(selectedApp.status) && (
                <InterviewPrepView applicationId={selectedApp.id} />
              )}

              {/* Details */}
              <div className="space-y-3">
                {selectedApp.location && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Location</p>
                    <p className="text-sm text-foreground">{selectedApp.location}</p>
                  </div>
                )}
                {selectedApp.salary_range && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Salary Range</p>
                    <p className="text-sm text-foreground">{selectedApp.salary_range}</p>
                  </div>
                )}
                {selectedApp.deadline && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Deadline</p>
                    <p className="text-sm text-foreground">{new Date(selectedApp.deadline).toLocaleDateString()}</p>
                  </div>
                )}
                {selectedApp.notes && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Notes</p>
                    <p className="text-sm text-foreground whitespace-pre-wrap">{selectedApp.notes}</p>
                  </div>
                )}
              </div>

              {/* Linked resumes */}
              {selectedApp.resume_jobs && selectedApp.resume_jobs.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase mb-2">Linked Resumes</p>
                  <div className="space-y-1.5">
                    {selectedApp.resume_jobs.map((rj) => (
                      <div
                        key={rj.id}
                        className="flex items-center justify-between rounded-lg border border-border p-2 text-sm"
                      >
                        <span className="text-foreground">
                          v{rj.version_number} {rj.is_active_version && "(active)"}
                        </span>
                        <span className={`text-xs ${rj.status === "completed" ? "text-green-600" : "text-muted"}`}>
                          {rj.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tags */}
              {selectedApp.tags.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase mb-1">Tags</p>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedApp.tags.map((tag) => (
                      <span key={tag} className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {applications.length === 0 && (
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <p className="text-lg font-medium text-foreground mb-1">No applications yet</p>
          <p className="text-sm text-muted mb-4">Add your first job application to start tracking</p>
        </div>
      )}
    </div>
  );
}
