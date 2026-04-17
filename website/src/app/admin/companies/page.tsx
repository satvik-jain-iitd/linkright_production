// Admin — companies_global management.
// Upload CSV + preview diff + commit. List all companies with search + toggle.

"use client";

import { useCallback, useEffect, useState } from "react";

type Company = {
  company_slug: string;
  display_name: string;
  ats_provider: string | null;
  ats_identifier: string | null;
  brand_tier: string | null;
  stage: string | null;
  tier_flags: string[] | null;
  is_active: boolean;
  updated_at: string;
};

type Preview = {
  total_rows: number;
  valid: number;
  invalid_count: number;
  invalid_rows: { line: number; error: string }[];
  new_companies: number;
  updated_companies: number;
};

export default function AdminCompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "true" | "false">("all");
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[] | null>(null);
  const [committing, setCommitting] = useState(false);

  const loadCompanies = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.set("q", search);
    if (activeFilter !== "all") params.set("active", activeFilter);
    params.set("limit", "200");
    const r = await fetch(`/api/admin/companies?${params}`);
    const body = await r.json();
    if (!r.ok) {
      setError(body.error ?? "failed to load");
      setCompanies([]);
      setTotal(0);
    } else {
      setError(null);
      setCompanies(body.companies);
      setTotal(body.total);
    }
    setLoading(false);
  }, [search, activeFilter]);

  useEffect(() => {
    loadCompanies();
  }, [loadCompanies]);

  async function handlePreview() {
    if (!file) return;
    setUploading(true);
    setPreview(null);
    setPreviewRows(null);
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/admin/companies/upload", { method: "POST", body: fd });
    const body = await r.json();
    if (!r.ok) {
      alert(`Preview failed: ${body.error}`);
      setUploading(false);
      return;
    }
    setPreview(body.preview);
    setPreviewRows(body.rows);
    setUploading(false);
  }

  async function handleCommit() {
    if (!file) return;
    setCommitting(true);
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/admin/companies/upload?commit=1", { method: "POST", body: fd });
    const body = await r.json();
    setCommitting(false);
    if (!r.ok) {
      alert(`Commit failed: ${body.error}`);
      return;
    }
    alert(`Committed ${body.upserted} rows.`);
    setFile(null);
    setPreview(null);
    setPreviewRows(null);
    loadCompanies();
  }

  async function toggleActive(slug: string, next: boolean) {
    const r = await fetch(`/api/admin/companies?slug=${encodeURIComponent(slug)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: next }),
    });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      alert(`Failed: ${body.error ?? r.status}`);
      return;
    }
    loadCompanies();
  }

  if (error === "unauthenticated") {
    return (
      <div className="p-8 max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Admin — Companies</h1>
        <p className="text-red-600">Not signed in. <a href="/auth" className="underline">Sign in</a>.</p>
      </div>
    );
  }

  if (error === "not_admin") {
    return (
      <div className="p-8 max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Admin — Companies</h1>
        <p className="text-red-600">You are not an admin. Contact super_admin to be added to the allowlist.</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Admin — Companies</h1>

      {/* Upload section */}
      <section className="mb-8 p-6 rounded-xl border border-border bg-surface">
        <h2 className="text-lg font-semibold mb-3">Upload CSV</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Template at{" "}
          <a href="/specs/company_template.csv" className="underline" download>
            specs/company_template.csv
          </a>
          . Upload is idempotent — existing rows are updated on <code>company_slug</code> match.
        </p>
        <div className="flex gap-3 items-center mb-4">
          <input
            type="file"
            accept=".csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setPreview(null);
              setPreviewRows(null);
            }}
            className="text-sm"
          />
          <button
            onClick={handlePreview}
            disabled={!file || uploading}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground disabled:opacity-50"
          >
            {uploading ? "Parsing..." : "Preview"}
          </button>
          {preview && (
            <button
              onClick={handleCommit}
              disabled={committing || preview.valid === 0}
              className="px-4 py-2 rounded-lg bg-green-600 text-white disabled:opacity-50"
            >
              {committing ? "Committing..." : `Commit ${preview.valid} rows`}
            </button>
          )}
        </div>

        {preview && (
          <div className="text-sm space-y-2">
            <div className="grid grid-cols-4 gap-3 p-3 rounded-lg bg-muted">
              <div>
                <div className="text-xs text-muted-foreground">Total rows</div>
                <div className="text-lg font-semibold">{preview.total_rows}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Valid</div>
                <div className="text-lg font-semibold text-green-600">{preview.valid}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">New / Updated</div>
                <div className="text-lg font-semibold">
                  {preview.new_companies} / {preview.updated_companies}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Invalid</div>
                <div className="text-lg font-semibold text-red-600">{preview.invalid_count}</div>
              </div>
            </div>
            {preview.invalid_rows.length > 0 && (
              <details className="text-xs">
                <summary className="cursor-pointer text-red-600">
                  {preview.invalid_rows.length} invalid rows
                </summary>
                <ul className="mt-2 ml-4 list-disc">
                  {preview.invalid_rows.slice(0, 20).map((r, i) => (
                    <li key={i}>
                      line {r.line}: {r.error}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </section>

      {/* List section */}
      <section className="p-6 rounded-xl border border-border bg-surface">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-lg font-semibold">Companies ({total})</h2>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search name, slug, notes..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-border bg-background text-sm"
            />
            <select
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value as "all" | "true" | "false")}
              className="px-3 py-1.5 rounded-lg border border-border bg-background text-sm"
            >
              <option value="all">All</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left border-b border-border">
                <tr>
                  <th className="py-2 px-2">Slug</th>
                  <th className="py-2 px-2">Name</th>
                  <th className="py-2 px-2">ATS</th>
                  <th className="py-2 px-2">Tier</th>
                  <th className="py-2 px-2">Stage</th>
                  <th className="py-2 px-2">Flags</th>
                  <th className="py-2 px-2">Active</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((c) => (
                  <tr key={c.company_slug} className="border-b border-border/50">
                    <td className="py-2 px-2 font-mono text-xs">{c.company_slug}</td>
                    <td className="py-2 px-2">{c.display_name}</td>
                    <td className="py-2 px-2 text-xs">
                      {c.ats_provider}
                      {c.ats_identifier ? `:${c.ats_identifier}` : ""}
                    </td>
                    <td className="py-2 px-2 text-xs">{c.brand_tier ?? "—"}</td>
                    <td className="py-2 px-2 text-xs">{c.stage ?? "—"}</td>
                    <td className="py-2 px-2 text-xs">
                      {(c.tier_flags ?? []).slice(0, 3).join(", ")}
                    </td>
                    <td className="py-2 px-2">
                      <button
                        onClick={() => toggleActive(c.company_slug, !c.is_active)}
                        className={`px-2 py-1 rounded text-xs ${
                          c.is_active
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {c.is_active ? "Active" : "Inactive"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {companies.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                No companies yet. Upload a CSV above.
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
