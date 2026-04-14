"use client";

import { useEffect, useState, useCallback } from "react";
import { DiscoveryCard } from "@/components/scout/DiscoveryCard";

interface Discovery {
  id: string;
  title: string;
  company_name: string;
  location: string | null;
  job_url: string;
  description_snippet: string | null;
  auto_score_grade: string | null;
  liveness_status: string;
  status: "new" | "saved" | "dismissed" | "applied";
  discovered_at: string;
  company_watchlist?: { company_name: string; ats_provider: string | null };
}

const STATUS_TABS = [
  { value: "", label: "All" },
  { value: "new", label: "New" },
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "dismissed", label: "Dismissed" },
] as const;

export default function DiscoveriesPage() {
  const [discoveries, setDiscoveries] = useState<Discovery[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("");

  const fetchDiscoveries = useCallback(async (status: string) => {
    setLoading(true);
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    params.set("limit", "50");

    const res = await fetch(`/api/discoveries?${params}`);
    if (res.ok) {
      const data = await res.json();
      setDiscoveries(data.discoveries);
      setTotal(data.total);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchDiscoveries(activeTab); }, [activeTab, fetchDiscoveries]);

  const handleStatusChange = async (id: string, newStatus: "saved" | "dismissed" | "new") => {
    const res = await fetch(`/api/discoveries/${id}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    if (res.ok) {
      setDiscoveries((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: newStatus } : d))
      );
    }
  };

  const handleApply = async (id: string) => {
    const res = await fetch(`/api/discoveries/${id}/apply`, { method: "POST" });
    if (res.ok) {
      setDiscoveries((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: "applied" as const } : d))
      );
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-foreground">Discoveries</h1>
        <p className="mt-1 text-sm text-muted">
          {total} job{total !== 1 ? "s" : ""} discovered from your watchlist
        </p>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              activeTab === tab.value
                ? "bg-accent text-white"
                : "bg-surface text-muted hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-12 text-center text-sm text-muted">Loading discoveries...</div>
      ) : discoveries.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border py-16 text-center">
          <p className="text-sm text-muted">
            {activeTab ? `No ${activeTab} discoveries` : "No discoveries yet"}
          </p>
          <p className="mt-1 text-xs text-muted">
            Add companies to your watchlist and run a scan
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {discoveries.map((discovery) => (
            <DiscoveryCard
              key={discovery.id}
              discovery={discovery}
              onStatusChange={handleStatusChange}
              onApply={handleApply}
            />
          ))}
        </div>
      )}
    </div>
  );
}
