// Onboarding screen 3 / dashboard jobs — browse the user's match-ranked openings.
// Default view: accordion grouped by company (best match first).
// Toggle: flat list by jobs (shows match %).

"use client";

import { useCallback, useEffect, useState } from "react";

type Top20Row = {
  id: string;
  rank: number;
  final_score: number;
  reason: string | null;
  resume_job_id: string | null;
  job_discoveries: {
    id: string;
    title: string;
    company_name: string;
    job_url: string;
    discovered_at: string;
    liveness_status: string;
  } | null;
};

type Payload = {
  date_utc: string;
  top20: Top20Row[];
  resume_jobs_by_id: Record<string, { status: string; created_at: string }>;
  daily_resume_usage: { used: number; cap: number; remaining: number };
};

type ViewMode = "accordion" | "list";

export default function JobsPage() {
  const [data, setData] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<ViewMode>("accordion");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    const r = await fetch("/api/recommendations/today");
    const body = await r.json();
    if (!r.ok) setError(body.error ?? "failed");
    else setData(body);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <div className="p-8 max-w-4xl mx-auto text-sm text-muted-foreground">Surfacing your best matches…</div>;
  }
  if (error) {
    return <div className="p-8 max-w-4xl mx-auto text-red-600">{error}</div>;
  }
  if (!data) return null;

  const rows = data.top20.filter((r) => r.job_discoveries);

  // Group by company for accordion mode
  const byCompany = new Map<string, Top20Row[]>();
  for (const r of rows) {
    const key = r.job_discoveries!.company_name;
    if (!byCompany.has(key)) byCompany.set(key, []);
    byCompany.get(key)!.push(r);
  }
  // Company ordering: best rank within company
  const companies = Array.from(byCompany.entries()).sort(
    (a, b) =>
      Math.min(...a[1].map((r) => r.rank)) -
      Math.min(...b[1].map((r) => r.rank)),
  );

  function toggle(co: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(co)) next.delete(co);
      else next.add(co);
      return next;
    });
  }

  async function handleCustomize(row: Top20Row) {
    if (!row.job_discoveries) return;
    // Check embedding status to decide journey
    const r = await fetch("/api/nuggets/status");
    const body = await r.json();
    const ready = body.total_embedded > 0 && body.total_embedded / body.total_extracted >= 0.9;
    if (ready) {
      // Direct path
      window.location.href = `/customize/${row.job_discoveries.id}`;
    } else {
      // Mind-map enrichment path
      window.location.href = `/customize/${row.job_discoveries.id}/enrich`;
    }
  }

  function rowResumeStatus(row: Top20Row): string {
    if (!row.resume_job_id) return "";
    const job = data!.resume_jobs_by_id[row.resume_job_id];
    if (!job) return "";
    return job.status;
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex justify-between items-baseline mb-6">
        <div>
          <h1 className="text-2xl font-bold">Your matches today</h1>
          <p className="text-sm text-muted-foreground">
            {rows.length} openings · {data.daily_resume_usage.remaining}/{data.daily_resume_usage.cap} resume slots left today
          </p>
        </div>
        <div className="flex gap-2 border border-border rounded-lg p-1 text-sm">
          <button
            onClick={() => setMode("accordion")}
            className={`px-3 py-1 rounded ${mode === "accordion" ? "bg-primary text-primary-foreground" : ""}`}
          >
            By company
          </button>
          <button
            onClick={() => setMode("list")}
            className={`px-3 py-1 rounded ${mode === "list" ? "bg-primary text-primary-foreground" : ""}`}
          >
            List
          </button>
        </div>
      </div>

      {rows.length === 0 && (
        <div className="p-8 rounded-xl border border-border text-center">
          <p className="text-sm text-muted-foreground">
            No matches yet. We run the recommender every 5 min — fresh discoveries will appear here soon.
          </p>
        </div>
      )}

      {mode === "accordion" && (
        <div className="space-y-3">
          {companies.map(([coName, coRows]) => {
            const isOpen = expanded.has(coName);
            const bestRank = Math.min(...coRows.map((r) => r.rank));
            const bestScore = Math.max(...coRows.map((r) => r.final_score));
            return (
              <div key={coName} className="rounded-xl border border-border bg-surface overflow-hidden">
                <button
                  onClick={() => toggle(coName)}
                  className="w-full flex justify-between items-center p-4 hover:bg-muted/30"
                >
                  <div className="text-left">
                    <div className="font-semibold">{coName}</div>
                    <div className="text-xs text-muted-foreground">
                      {coRows.length} open {coRows.length === 1 ? "role" : "roles"} · best match #{bestRank} (score {bestScore.toFixed(2)})
                    </div>
                  </div>
                  <div className={`text-xl transition-transform ${isOpen ? "rotate-90" : ""}`}>›</div>
                </button>
                {isOpen && (
                  <div className="border-t border-border divide-y divide-border">
                    {coRows.map((r) => {
                      const d = r.job_discoveries!;
                      const status = rowResumeStatus(r);
                      return (
                        <div key={r.id} className="p-4 flex justify-between items-center">
                          <div className="flex-1 pr-4">
                            <a
                              href={d.job_url}
                              target="_blank"
                              rel="noreferrer"
                              className="font-medium hover:underline"
                            >
                              {d.title}
                            </a>
                            <div className="text-xs text-muted-foreground mt-0.5">
                              #{r.rank} · score {r.final_score.toFixed(2)}
                              {r.reason ? ` · ${r.reason}` : ""}
                            </div>
                          </div>
                          {status ? (
                            <span className="text-xs px-2 py-1 rounded bg-muted text-muted-foreground">
                              {status}
                            </span>
                          ) : (
                            <button
                              onClick={() => handleCustomize(r)}
                              className="text-sm px-3 py-1.5 rounded-lg bg-primary text-primary-foreground"
                            >
                              Customize resume
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {mode === "list" && (
        <div className="rounded-xl border border-border bg-surface overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/50">
              <tr className="text-left">
                <th className="py-2 px-3">#</th>
                <th className="py-2 px-3">Role</th>
                <th className="py-2 px-3">Company</th>
                <th className="py-2 px-3 text-right">Match</th>
                <th className="py-2 px-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const d = r.job_discoveries!;
                const status = rowResumeStatus(r);
                return (
                  <tr key={r.id} className="border-b border-border/50">
                    <td className="py-2 px-3 text-muted-foreground">{r.rank}</td>
                    <td className="py-2 px-3">
                      <a href={d.job_url} target="_blank" rel="noreferrer" className="hover:underline">
                        {d.title}
                      </a>
                    </td>
                    <td className="py-2 px-3">{d.company_name}</td>
                    <td className="py-2 px-3 text-right font-mono">{r.final_score.toFixed(2)}</td>
                    <td className="py-2 px-3">
                      {status ? (
                        <span className="text-xs px-2 py-1 rounded bg-muted text-muted-foreground">
                          {status}
                        </span>
                      ) : (
                        <button
                          onClick={() => handleCustomize(r)}
                          className="text-xs px-2 py-1 rounded bg-primary text-primary-foreground"
                        >
                          Customize
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
