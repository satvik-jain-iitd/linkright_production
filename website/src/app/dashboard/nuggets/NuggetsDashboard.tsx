"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

/* ---------- Types ---------- */

interface Summary {
  total: number;
  embedded: number;
  pct_embedded: number;
  retrieval_ready: number;
  pct_ready: number;
}

interface Gaps {
  orphaned_no_company: number;
  missing_role: number;
  missing_event_date: number;
  no_metrics: number;
  too_vague: number;
  high_risk: number;
  medium_risk: number;
}

interface SectionReadiness {
  total: number;
  ready: number;
  pct: number;
}

interface Analytics {
  summary: Summary;
  layers: { A: number; B: number };
  section_types: { type: string; count: number; ready: number }[];
  importance: { level: string; count: number; pct: number }[];
  gaps: Gaps;
  top_companies: { company: string; count: number }[];
  readiness_by_section: Record<string, SectionReadiness>;
}

interface NuggetRow {
  id: string;
  nugget_text: string | null;
  answer: string | null;
  company: string | null;
  role: string | null;
  event_date: string | null;
  section_type: string | null;
  importance: string | null;
  resume_relevance: number | null;
  tags: string[] | null;
  created_at: string;
  primary_layer: string | null;
  life_domain: string | null;
  leadership_signal: string | null;
  is_embedded: boolean;
}

interface Filters {
  section_type: string;
  company: string;
  importance: string;
  search: string;
  embedded: string;
}

/* ---------- Sub-components ---------- */

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: "green" | "yellow" | "red";
}) {
  const colorClasses =
    color === "green"
      ? "border-green-300 bg-green-50 text-green-800"
      : color === "yellow"
        ? "border-amber-300 bg-amber-50 text-amber-800"
        : color === "red"
          ? "border-red-300 bg-red-50 text-red-800"
          : "border-border bg-surface text-foreground";

  return (
    <div className={`rounded-2xl border p-5 ${colorClasses}`}>
      <p className="text-sm font-medium opacity-70">{label}</p>
      <p className="mt-1 text-3xl font-bold">{value}</p>
    </div>
  );
}

function GapsPanel({ gaps }: { gaps: Gaps }) {
  const items = [
    { label: "No company", count: gaps.orphaned_no_company, severity: "red" as const },
    { label: "Missing role", count: gaps.missing_role, severity: "yellow" as const },
    { label: "Missing date", count: gaps.missing_event_date, severity: "yellow" as const },
    { label: "No metrics", count: gaps.no_metrics, severity: "red" as const },
    { label: "Too vague (<50 chars)", count: gaps.too_vague, severity: "yellow" as const },
    { label: "High risk", count: gaps.high_risk, severity: "red" as const },
    { label: "Medium risk", count: gaps.medium_risk, severity: "yellow" as const },
  ];

  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <h2 className="text-base font-semibold text-foreground">Data Gaps</h2>
      <p className="mt-1 text-sm text-muted">Issues that reduce retrieval readiness</p>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex items-center gap-3 rounded-xl border border-border bg-background px-4 py-3"
          >
            <span
              className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                item.severity === "red" ? "bg-red-500" : "bg-amber-400"
              }`}
            />
            <div className="min-w-0">
              <p className="text-xs text-muted">{item.label}</p>
              <p className="text-lg font-semibold text-foreground">{item.count}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReadinessSection({
  readiness,
}: {
  readiness: Record<string, SectionReadiness>;
}) {
  const entries = Object.entries(readiness).sort((a, b) => b[1].total - a[1].total);

  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <h2 className="text-base font-semibold text-foreground">Readiness by Section</h2>
      <p className="mt-1 text-sm text-muted">Percentage of nuggets ready for retrieval per section type</p>
      <div className="mt-4 space-y-3">
        {entries.map(([section, { total, ready, pct }]) => (
          <div key={section}>
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-foreground">{section}</span>
              <span className="text-xs text-muted">
                {ready}/{total} ({pct}%)
              </span>
            </div>
            <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-border">
              <div
                className={`h-full rounded-full transition-all ${
                  pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-amber-400" : "bg-red-400"
                }`}
                style={{ width: `${Math.min(100, pct)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FiltersBar({
  filters,
  onChange,
  analytics,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
  analytics: Analytics;
}) {
  const sectionTypes = analytics.section_types.map((s) => s.type);
  const companies = analytics.top_companies.map((c) => c.company);
  const importanceLevels = analytics.importance.map((i) => i.level);

  const update = (key: keyof Filters, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={filters.section_type}
        onChange={(e) => update("section_type", e.target.value)}
        className="rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-accent/50 focus:outline-none"
      >
        <option value="">All sections</option>
        {sectionTypes.map((st) => (
          <option key={st} value={st}>
            {st}
          </option>
        ))}
      </select>

      <select
        value={filters.company}
        onChange={(e) => update("company", e.target.value)}
        className="rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-accent/50 focus:outline-none"
      >
        <option value="">All companies</option>
        {companies.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <select
        value={filters.importance}
        onChange={(e) => update("importance", e.target.value)}
        className="rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-accent/50 focus:outline-none"
      >
        <option value="">All importance</option>
        {importanceLevels.map((l) => (
          <option key={l} value={l}>
            {l}
          </option>
        ))}
      </select>

      <select
        value={filters.embedded}
        onChange={(e) => update("embedded", e.target.value)}
        className="rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-accent/50 focus:outline-none"
      >
        <option value="">All embed status</option>
        <option value="true">Embedded</option>
        <option value="false">Not embedded</option>
      </select>

      <input
        type="text"
        value={filters.search}
        onChange={(e) => update("search", e.target.value)}
        placeholder="Search answers..."
        className="min-w-0 flex-1 rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground placeholder-muted focus:border-accent/50 focus:outline-none"
      />

      {Object.values(filters).some((v) => v !== "") && (
        <button
          onClick={() =>
            onChange({ section_type: "", company: "", importance: "", search: "", embedded: "" })
          }
          className="rounded-xl border border-border bg-background px-3 py-2 text-sm text-muted hover:text-foreground"
        >
          Clear
        </button>
      )}
    </div>
  );
}

const IMPORTANCE_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-gray-100 text-gray-600",
  unset: "bg-gray-100 text-gray-500",
};

function NuggetsTable({ nuggets }: { nuggets: NuggetRow[] }) {
  if (nuggets.length === 0) {
    return (
      <div className="rounded-2xl border border-border bg-surface p-8 text-center text-sm text-muted">
        No nuggets found matching your filters.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-border">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface text-xs font-semibold uppercase tracking-wide text-muted">
          <tr>
            <th className="px-4 py-3">ID</th>
            <th className="px-4 py-3">Answer</th>
            <th className="px-4 py-3">Company</th>
            <th className="px-4 py-3">Role</th>
            <th className="px-4 py-3">Date</th>
            <th className="px-4 py-3">Importance</th>
            <th className="px-4 py-3">Section</th>
            <th className="px-4 py-3">Emb</th>
            <th className="px-4 py-3">Rel</th>
            <th className="px-4 py-3">Tags</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border bg-background">
          {nuggets.map((n) => (
            <tr key={n.id} className="hover:bg-surface-hover transition-colors">
              <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-muted">
                {n.id.slice(0, 8)}
              </td>
              <td
                className="max-w-xs truncate px-4 py-2.5 text-foreground"
                title={n.answer || ""}
              >
                {(n.answer || "").length > 80
                  ? (n.answer || "").slice(0, 80) + "..."
                  : n.answer || "-"}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 text-foreground">
                {n.company || <span className="text-muted">-</span>}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 text-foreground">
                {n.role || <span className="text-muted">-</span>}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 text-xs text-muted">
                {n.event_date || "-"}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5">
                <span
                  className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${
                    IMPORTANCE_COLORS[n.importance || "unset"] || IMPORTANCE_COLORS.unset
                  }`}
                >
                  {n.importance || "unset"}
                </span>
              </td>
              <td className="whitespace-nowrap px-4 py-2.5">
                <span className="inline-block rounded-md bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                  {n.section_type || "-"}
                </span>
              </td>
              <td className="px-4 py-2.5 text-center">
                {n.is_embedded ? (
                  <span className="text-green-600" title="Embedded">
                    &#10003;
                  </span>
                ) : (
                  <span className="text-muted">-</span>
                )}
              </td>
              <td className="whitespace-nowrap px-4 py-2.5 text-xs text-foreground">
                {n.resume_relevance !== null ? n.resume_relevance.toFixed(2) : "-"}
              </td>
              <td className="max-w-[120px] truncate px-4 py-2.5 text-xs text-muted">
                {n.tags && n.tags.length > 0 ? n.tags.join(", ") : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Pagination({
  page,
  total,
  limit,
  onChange,
}: {
  page: number;
  total: number;
  limit: number;
  onChange: (p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted">
        {total} nugget{total !== 1 ? "s" : ""} total
      </span>
      <div className="flex items-center gap-3">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm text-foreground hover:bg-surface-hover disabled:opacity-30"
        >
          Prev
        </button>
        <span className="text-muted">
          Page {page} of {totalPages}
        </span>
        <button
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
          className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm text-foreground hover:bg-surface-hover disabled:opacity-30"
        >
          Next
        </button>
      </div>
    </div>
  );
}

/* ---------- Main Component ---------- */

export default function NuggetsDashboard() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [nuggets, setNuggets] = useState<NuggetRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<Filters>({
    section_type: "",
    company: "",
    importance: "",
    search: "",
    embedded: "",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Fetch analytics on mount
  useEffect(() => {
    fetch("/api/nuggets/analytics")
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setError(data.error);
        } else {
          setAnalytics(data);
        }
      })
      .catch(() => setError("Failed to load analytics"));
  }, []);

  // Fetch nuggets on page/filter change
  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ page: String(page), limit: "50" });
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params.set(k, v);
    });
    fetch(`/api/nuggets/list?${params}`)
      .then((r) => r.json())
      .then((data) => {
        setNuggets(data.nuggets || []);
        setTotal(data.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page, filters]);

  // Reset page when filters change
  const handleFiltersChange = (f: Filters) => {
    setPage(1);
    setFilters(f);
  };

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-red-500">{error}</p>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Navbar */}
      <nav className="flex items-center justify-between border-b border-border px-6 py-4">
        <Link href="/dashboard" className="text-lg font-bold tracking-tight">
          Link<span className="text-accent">Right</span>
        </Link>
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            &larr; Dashboard
          </Link>
          <Link
            href="/dashboard/settings"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            Settings
          </Link>
        </div>
      </nav>

      <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
        {/* Title + Import button */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Career Nuggets</h1>
            <p className="mt-1 text-sm text-muted">
              Analytics and management for your nugget library
            </p>
          </div>
          <Link
            href="/resume/new"
            className="rounded-full bg-cta px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
          >
            + Import Nuggets
          </Link>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <SummaryCard label="Total Nuggets" value={analytics.summary.total} />
          <SummaryCard label="Embedded" value={`${analytics.summary.pct_embedded}%`} />
          <SummaryCard label="Retrieval Ready" value={analytics.summary.retrieval_ready} />
          <SummaryCard
            label="Readiness"
            value={`${analytics.summary.pct_ready}%`}
            color={
              analytics.summary.pct_ready >= 80
                ? "green"
                : analytics.summary.pct_ready >= 50
                  ? "yellow"
                  : "red"
            }
          />
        </div>

        {/* Gaps Panel */}
        <GapsPanel gaps={analytics.gaps} />

        {/* Readiness Progress Bars */}
        <ReadinessSection readiness={analytics.readiness_by_section} />

        {/* Filters */}
        <FiltersBar filters={filters} onChange={handleFiltersChange} analytics={analytics} />

        {/* Nuggets Table */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
          </div>
        ) : (
          <NuggetsTable nuggets={nuggets} />
        )}

        {/* Pagination */}
        <Pagination page={page} total={total} limit={50} onChange={setPage} />
      </div>
    </div>
  );
}
