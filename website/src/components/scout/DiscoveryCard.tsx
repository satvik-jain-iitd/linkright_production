"use client";

interface DiscoveryCardProps {
  discovery: {
    id: string;
    title: string;
    company_name: string;
    location: string | null;
    job_url: string;
    description_snippet: string | null;
    auto_score_grade: string | null;
    liveness_status?: string;
    status: "new" | "saved" | "dismissed" | "applied";
    discovered_at: string;
  };
  onStatusChange: (id: string, status: "saved" | "dismissed" | "new") => void;
  onApply: (id: string) => void;
}

const GRADE_COLORS: Record<string, string> = {
  A: "bg-green-100 text-green-700",
  B: "bg-blue-100 text-blue-700",
  C: "bg-yellow-100 text-yellow-700",
  D: "bg-orange-100 text-orange-700",
  F: "bg-red-100 text-red-600",
};

export function DiscoveryCard({ discovery, onStatusChange, onApply }: DiscoveryCardProps) {
  const isActioned = discovery.status === "applied";

  return (
    <div data-testid="discovery-card" className="rounded-xl border border-border bg-surface p-4 transition-colors hover:border-accent/20">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <a
              href={discovery.job_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-foreground hover:text-accent hover:underline truncate"
            >
              {discovery.title}
            </a>
            {discovery.auto_score_grade && (
              <span
                className={`flex-shrink-0 rounded px-1.5 py-0.5 text-xs font-bold ${
                  GRADE_COLORS[discovery.auto_score_grade] || "bg-gray-100 text-gray-600"
                }`}
              >
                {discovery.auto_score_grade}
              </span>
            )}
            {discovery.status === "saved" && (
              <span className="flex-shrink-0 rounded bg-accent/10 px-1.5 py-0.5 text-xs font-medium text-accent">
                Saved
              </span>
            )}
            {discovery.status === "applied" && (
              <span className="flex-shrink-0 rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium text-green-700">
                Applied
              </span>
            )}
            {discovery.liveness_status && discovery.liveness_status !== "active" && (
              <span className="flex-shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-500">
                Closed
              </span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-2 text-sm text-muted">
            <span>{discovery.company_name}</span>
            {discovery.location && (
              <>
                <span className="text-border">|</span>
                <span>{discovery.location}</span>
              </>
            )}
          </div>
          {discovery.description_snippet && (
            <p className="mt-2 text-sm text-muted line-clamp-2">
              {discovery.description_snippet}
            </p>
          )}
          <p className="mt-2 text-xs text-muted">
            Discovered {new Date(discovery.discovered_at).toLocaleDateString()}
          </p>
        </div>

        {/* Actions */}
        {!isActioned && (
          <div className="flex flex-shrink-0 items-center gap-1">
            {discovery.status !== "saved" ? (
              <button
                onClick={() => onStatusChange(discovery.id, "saved")}
                title="Save"
                className="rounded-lg p-2 text-muted transition-colors hover:bg-accent/10 hover:text-accent"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
              </button>
            ) : (
              <button
                onClick={() => onStatusChange(discovery.id, "new")}
                title="Unsave"
                className="rounded-lg p-2 text-accent transition-colors hover:bg-accent/10"
              >
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
              </button>
            )}
            <button
              onClick={() => onApply(discovery.id)}
              title="Track application"
              className="rounded-lg bg-cta px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-cta-hover"
            >
              Track
            </button>
            {discovery.status !== "dismissed" && (
              <button
                onClick={() => onStatusChange(discovery.id, "dismissed")}
                title="Dismiss"
                className="rounded-lg p-2 text-muted transition-colors hover:bg-red-50 hover:text-red-500"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
