"use client";

interface CompanyCardProps {
  company: {
    id: string;
    company_name: string;
    company_slug: string;
    ats_provider: string | null;
    positive_keywords: string[];
    negative_keywords: string[];
    is_active: boolean;
    last_scanned_at: string | null;
    scan_interval_minutes?: number;
  };
  onDelete: () => void;
  onToggle: () => void;
  onIntervalChange?: (id: string, interval: number) => void;
}

const ATS_LABELS: Record<string, string> = {
  greenhouse: "Greenhouse",
  lever: "Lever",
  ashby: "Ashby",
  smartrecruiters: "SmartRecruiters",
  workable: "Workable",
  recruitee: "Recruitee",
  bamboohr: "BambooHR",
  workday: "Workday",
  icims: "iCIMS",
};

const INTERVAL_OPTIONS = [
  { value: 15, label: "15 min" },
  { value: 60, label: "1 hour" },
  { value: 360, label: "6 hours" },
  { value: 1440, label: "Daily" },
];

export function CompanyCard({ company, onDelete, onToggle, onIntervalChange }: CompanyCardProps) {
  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        company.is_active
          ? "border-border bg-surface"
          : "border-border/50 bg-surface/50 opacity-60"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-foreground truncate">{company.company_name}</h3>
          <div className="mt-1 flex items-center gap-2">
            {company.ats_provider && (
              <span className="rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                {ATS_LABELS[company.ats_provider] || company.ats_provider}
              </span>
            )}
            <span className="text-xs text-muted">{company.company_slug}</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onToggle}
            title={company.is_active ? "Pause scanning" : "Resume scanning"}
            className="rounded-lg p-1.5 text-muted transition-colors hover:bg-background hover:text-foreground"
          >
            {company.is_active ? (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
          </button>
          <button
            onClick={onDelete}
            title="Remove from watchlist"
            className="rounded-lg p-1.5 text-muted transition-colors hover:bg-red-50 hover:text-red-500"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* Keywords */}
      {(company.positive_keywords.length > 0 || company.negative_keywords.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-1">
          {company.positive_keywords.map((kw) => (
            <span key={kw} className="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-700">
              +{kw}
            </span>
          ))}
          {company.negative_keywords.map((kw) => (
            <span key={kw} className="rounded bg-red-50 px-1.5 py-0.5 text-xs text-red-600">
              -{kw}
            </span>
          ))}
        </div>
      )}

      {/* Scan interval + last scanned */}
      <div className="mt-3 flex items-center justify-between">
        <p className="text-xs text-muted">
          {company.last_scanned_at
            ? `Last scanned ${new Date(company.last_scanned_at).toLocaleDateString()}`
            : "Never scanned"}
        </p>
        {onIntervalChange && (
          <select
            value={company.scan_interval_minutes ?? 60}
            onChange={(e) => onIntervalChange(company.id, Number(e.target.value))}
            className="rounded border border-border bg-background px-1.5 py-0.5 text-xs text-muted focus:border-accent focus:outline-none"
            title="Scan frequency"
          >
            {INTERVAL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        )}
      </div>
    </div>
  );
}
