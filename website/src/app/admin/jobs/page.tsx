"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

interface Job {
  id: string;
  title: string;
  company_name: string;
  location: string | null;
  source_type: string | null;
  experience_level: string | null;
  work_type: string | null;
  employment_type: string | null;
  industry: string | null;
  company_stage: string | null;
  department: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  skills_required: string[] | null;
  reporting_to: string | null;
  enrichment_status: string | null;
  liveness_status: string | null;
  job_url: string;
  apply_url: string | null;
  discovered_at: string;
}

const PAGE_SIZE = 50;

const SOURCE_LABELS: Record<string, string> = {
  ats: "ATS",
  api_wellfound: "Wellfound",
  api_adzuna: "Adzuna",
  api_iimjobs: "iimjobs",
  api_remotive: "Remotive",
  api_jsearch: "JSearch",
  api_serpapi: "SerpAPI",
  manual_csv: "CSV Import",
};

const EXP_LABELS: Record<string, string> = {
  early: "0–3 yrs",
  mid: "4–6 yrs",
  senior: "6–10 yrs",
  executive: "10–15 yrs",
  cxo: "15+ yrs",
};

const ENRICH_COLORS: Record<string, string> = {
  done: "bg-green-50 text-green-700",
  pending: "bg-amber-50 text-amber-700",
  skipped: "bg-[#F1F5F9] text-muted",
};

const LIVENESS_COLORS: Record<string, string> = {
  active: "bg-green-50 text-green-700",
  expired: "bg-red-50 text-red-600",
  unknown: "bg-[#F1F5F9] text-muted",
};

function fmt(date: string) {
  return new Date(date).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function ExpandedRow({ job }: { job: Job }) {
  return (
    <tr>
      <td colSpan={8} className="bg-[#FAFBFC] px-6 py-4 border-b border-border">
        <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3 lg:grid-cols-4">
          {job.industry && (
            <div><p className="text-[11px] uppercase tracking-wide text-muted font-medium">Industry</p><p className="text-foreground mt-0.5">{job.industry}</p></div>
          )}
          {job.department && (
            <div><p className="text-[11px] uppercase tracking-wide text-muted font-medium">Department</p><p className="text-foreground mt-0.5">{job.department}</p></div>
          )}
          {job.company_stage && (
            <div><p className="text-[11px] uppercase tracking-wide text-muted font-medium">Company stage</p><p className="text-foreground mt-0.5">{job.company_stage}</p></div>
          )}
          {job.employment_type && (
            <div><p className="text-[11px] uppercase tracking-wide text-muted font-medium">Employment</p><p className="text-foreground mt-0.5">{job.employment_type.replace("_", " ")}</p></div>
          )}
          {job.reporting_to && (
            <div><p className="text-[11px] uppercase tracking-wide text-muted font-medium">Reports to</p><p className="text-foreground mt-0.5">{job.reporting_to}</p></div>
          )}
          {(job.salary_min || job.salary_max) && (
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted font-medium">Salary</p>
              <p className="text-foreground mt-0.5">
                {job.salary_currency} {job.salary_min?.toLocaleString()}
                {job.salary_max ? `–${job.salary_max.toLocaleString()}` : ""}
              </p>
            </div>
          )}
          {job.location && (
            <div><p className="text-[11px] uppercase tracking-wide text-muted font-medium">Location</p><p className="text-foreground mt-0.5">{job.location}</p></div>
          )}
          {job.apply_url && (
            <div><p className="text-[11px] uppercase tracking-wide text-muted font-medium">Apply URL</p>
              <a href={job.apply_url} target="_blank" rel="noreferrer" className="text-accent hover:underline mt-0.5 block truncate max-w-[200px]">Open ↗</a>
            </div>
          )}
          {job.skills_required && job.skills_required.length > 0 && (
            <div className="col-span-2">
              <p className="text-[11px] uppercase tracking-wide text-muted font-medium">Skills required</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {job.skills_required.slice(0, 12).map((s) => (
                  <span key={s} className="rounded-[6px] bg-accent/10 px-2 py-0.5 text-[11px] text-accent">{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="mt-3 flex gap-3">
          <a href={job.job_url} target="_blank" rel="noreferrer"
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface">
            View posting ↗
          </a>
        </div>
      </td>
    </tr>
  );
}

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [expLevel, setExpLevel] = useState("");
  const [enrichStatus, setEnrichStatus] = useState("");
  const [livenessStatus, setLivenessStatus] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (sourceType) params.set("source_type", sourceType);
    if (expLevel) params.set("experience_level", expLevel);
    if (enrichStatus) params.set("enrichment_status", enrichStatus);
    if (livenessStatus) params.set("liveness_status", livenessStatus);
    params.set("limit", String(PAGE_SIZE));
    params.set("offset", String(page * PAGE_SIZE));

    const r = await fetch(`/api/admin/jobs?${params}`);
    const d = await r.json();
    setJobs(d.jobs || []);
    setTotal(d.total || 0);
    setLoading(false);
  }, [q, sourceType, expLevel, enrichStatus, livenessStatus, page]);

  useEffect(() => { load(); }, [load]);

  function applyFilter() {
    setPage(0);
    load();
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Jobs</h1>
          <p className="text-sm text-muted mt-1">
            {total.toLocaleString()} global jobs captured
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-5 flex flex-wrap gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && applyFilter()}
          placeholder="Search title or company…"
          className="rounded-[10px] border border-border px-3 py-2 text-sm focus:outline-none focus:border-accent w-56"
        />
        <select value={sourceType} onChange={(e) => { setSourceType(e.target.value); setPage(0); }}
          className="rounded-[10px] border border-border px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent bg-white">
          <option value="">All sources</option>
          {Object.entries(SOURCE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select value={expLevel} onChange={(e) => { setExpLevel(e.target.value); setPage(0); }}
          className="rounded-[10px] border border-border px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent bg-white">
          <option value="">All levels</option>
          {Object.entries(EXP_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select value={enrichStatus} onChange={(e) => { setEnrichStatus(e.target.value); setPage(0); }}
          className="rounded-[10px] border border-border px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent bg-white">
          <option value="">All enrichment</option>
          <option value="pending">Pending</option>
          <option value="done">Done</option>
          <option value="skipped">Skipped</option>
        </select>
        <select value={livenessStatus} onChange={(e) => { setLivenessStatus(e.target.value); setPage(0); }}
          className="rounded-[10px] border border-border px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent bg-white">
          <option value="">All liveness</option>
          <option value="unknown">Unknown</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
        </select>
      </div>

      {/* Table */}
      <div className="rounded-[20px] border border-border bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-[#FAFBFC]">
              <th className="text-left px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Title</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Company</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Source</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Level</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Work type</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Enrichment</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Liveness</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Found</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-12 text-center text-sm text-muted">Loading…</td></tr>
            ) : jobs.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-12 text-center text-sm text-muted">No jobs found</td></tr>
            ) : jobs.map((job) => (
              <>
                <tr
                  key={job.id}
                  onClick={() => setExpandedId(expandedId === job.id ? null : job.id)}
                  className="border-b border-border last:border-0 hover:bg-[#FAFBFC] cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-foreground max-w-[220px]">
                    <span className="line-clamp-2 leading-snug">{job.title}</span>
                  </td>
                  <td className="px-4 py-3 text-muted max-w-[140px] truncate">{job.company_name}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-[6px] bg-[#F1F5F9] px-2 py-0.5 text-[11px] font-medium text-foreground">
                      {SOURCE_LABELS[job.source_type || ""] || job.source_type || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted text-[12px]">
                    {job.experience_level ? EXP_LABELS[job.experience_level] || job.experience_level : "—"}
                  </td>
                  <td className="px-4 py-3 text-muted text-[12px]">{job.work_type || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-[6px] px-2 py-0.5 text-[11px] font-medium ${ENRICH_COLORS[job.enrichment_status || ""] || "bg-[#F1F5F9] text-muted"}`}>
                      {job.enrichment_status || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-[6px] px-2 py-0.5 text-[11px] font-medium ${LIVENESS_COLORS[job.liveness_status || ""] || "bg-[#F1F5F9] text-muted"}`}>
                      {job.liveness_status || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted text-[12px] whitespace-nowrap">{fmt(job.discovered_at)}</td>
                </tr>
                {expandedId === job.id && <ExpandedRow key={`${job.id}-expanded`} job={job} />}
              </>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm text-muted">
          <span>{(page * PAGE_SIZE + 1).toLocaleString()}–{Math.min((page + 1) * PAGE_SIZE, total).toLocaleString()} of {total.toLocaleString()}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium disabled:opacity-40 hover:bg-surface"
            >
              ← Prev
            </button>
            <span className="px-2 py-1.5 text-xs">Page {page + 1} of {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium disabled:opacity-40 hover:bg-surface"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
