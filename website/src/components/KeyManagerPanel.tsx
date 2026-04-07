"use client";

import { useState, useEffect, useCallback } from "react";

interface ApiKey {
  id: string;
  provider: string;
  label: string;
  api_key_masked: string;
  is_active: boolean;
  priority: number;
  fail_count: number;
  last_used_at: string | null;
  created_at: string;
}

export interface KeyManagerPanelProps {
  provider: string;
  providerLabel: string;
  onKeySelected?: (key: string) => void;
}

export function KeyManagerPanel({ provider, providerLabel, onKeySelected }: KeyManagerPanelProps) {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKey, setNewKey] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState("");
  const [validating, setValidating] = useState<string | null>(null);
  const [validationStatus, setValidationStatus] = useState<Record<string, "valid" | "invalid">>({});
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    try {
      const resp = await fetch(`/api/user/keys?provider=${provider}`);
      if (!resp.ok) return;
      const data = await resp.json();
      setKeys(data.keys || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [provider]);

  useEffect(() => {
    setLoading(true);
    setKeys([]);
    setValidationStatus({});
    fetchKeys();
  }, [fetchKeys]);

  // Notify parent when keys change — primary = lowest priority active key
  useEffect(() => {
    if (!onKeySelected) return;
    const active = keys.filter((k) => k.is_active).sort((a, b) => a.priority - b.priority);
    // We can't send the real key (it's masked), so we send the key ID
    // The parent will know keys exist; the pipeline reads from DB
    if (active.length > 0) {
      onKeySelected(active[0].id);
    } else {
      onKeySelected("");
    }
  }, [keys, onKeySelected]);

  const handleAdd = async () => {
    if (!newKey.trim()) return;
    setAdding(true);
    setAddError("");
    try {
      const resp = await fetch("/api/user/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, api_key: newKey.trim(), label: newLabel.trim() || undefined }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        setAddError(err.error || "Failed to add key");
        return;
      }
      setNewKey("");
      setNewLabel("");
      await fetchKeys();
    } catch {
      setAddError("Network error");
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this API key?")) return;
    setDeleting(id);
    try {
      await fetch(`/api/user/keys/${id}`, { method: "DELETE" });
      await fetchKeys();
    } catch {
      // silent
    } finally {
      setDeleting(null);
    }
  };

  const handleValidate = async (id: string) => {
    setValidating(id);
    try {
      const resp = await fetch(`/api/user/keys/${id}/validate`, { method: "POST" });
      const data = await resp.json();
      setValidationStatus((prev) => ({ ...prev, [id]: data.valid ? "valid" : "invalid" }));
    } catch {
      setValidationStatus((prev) => ({ ...prev, [id]: "invalid" }));
    } finally {
      setValidating(null);
    }
  };

  const handleToggleActive = async (id: string, currentActive: boolean) => {
    try {
      await fetch(`/api/user/keys/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !currentActive }),
      });
      await fetchKeys();
    } catch {
      // silent
    }
  };

  const handleMovePriority = async (id: string, direction: "up" | "down") => {
    const sorted = [...keys].sort((a, b) => a.priority - b.priority);
    const idx = sorted.findIndex((k) => k.id === id);
    if (idx < 0) return;

    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= sorted.length) return;

    const current = sorted[idx];
    const swap = sorted[swapIdx];

    // Swap priorities
    try {
      await Promise.all([
        fetch(`/api/user/keys/${current.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ priority: swap.priority }),
        }),
        fetch(`/api/user/keys/${swap.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ priority: current.priority }),
        }),
      ]);
      await fetchKeys();
    } catch {
      // silent
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="flex items-center gap-2 text-sm text-muted">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
          Loading keys...
        </div>
      </div>
    );
  }

  const sorted = [...keys].sort((a, b) => a.priority - b.priority);

  return (
    <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
      <h3 className="text-sm font-semibold text-foreground">
        API Keys for {providerLabel}
      </h3>

      {/* Key list */}
      {sorted.length === 0 && (
        <p className="text-xs text-muted">No keys added yet.</p>
      )}

      {sorted.map((key, idx) => (
        <div
          key={key.id}
          className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm"
        >
          {/* Priority badge */}
          <span className="shrink-0 rounded bg-accent/10 px-1.5 py-0.5 text-xs font-semibold text-accent">
            #{idx + 1}
          </span>

          {/* Label + masked key */}
          <div className="min-w-0 flex-1">
            <span className="font-medium text-foreground">{key.label}</span>
            <span className="ml-2 text-xs text-muted">{key.api_key_masked}</span>
          </div>

          {/* Active indicator */}
          <button
            onClick={() => handleToggleActive(key.id, key.is_active)}
            className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
              key.is_active
                ? "bg-green-100 text-green-700 hover:bg-green-200"
                : "bg-gray-100 text-gray-500 hover:bg-gray-200"
            }`}
            title={key.is_active ? "Click to deactivate" : "Click to activate"}
          >
            {key.is_active ? "Active" : "Off"}
          </button>

          {/* Validation status / button */}
          <button
            onClick={() => handleValidate(key.id)}
            disabled={validating === key.id}
            className="shrink-0 rounded-md border border-border px-2 py-0.5 text-xs text-muted transition-colors hover:border-accent/30 hover:text-foreground disabled:opacity-40"
            title="Validate key"
          >
            {validating === key.id ? (
              "..."
            ) : validationStatus[key.id] === "valid" ? (
              <span className="text-green-600">Valid</span>
            ) : validationStatus[key.id] === "invalid" ? (
              <span className="text-red-500">Invalid</span>
            ) : (
              "Check"
            )}
          </button>

          {/* Move up */}
          <button
            onClick={() => handleMovePriority(key.id, "up")}
            disabled={idx === 0}
            className="shrink-0 rounded-md border border-border px-1.5 py-0.5 text-xs text-muted transition-colors hover:border-accent/30 hover:text-foreground disabled:opacity-20"
            title="Move up"
          >
            &#8593;
          </button>

          {/* Move down */}
          <button
            onClick={() => handleMovePriority(key.id, "down")}
            disabled={idx === sorted.length - 1}
            className="shrink-0 rounded-md border border-border px-1.5 py-0.5 text-xs text-muted transition-colors hover:border-accent/30 hover:text-foreground disabled:opacity-20"
            title="Move down"
          >
            &#8595;
          </button>

          {/* Delete */}
          <button
            onClick={() => handleDelete(key.id)}
            disabled={deleting === key.id}
            className="shrink-0 rounded-md border border-red-200 px-1.5 py-0.5 text-xs text-red-400 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
            title="Delete key"
          >
            {deleting === key.id ? "..." : "\u2715"}
          </button>
        </div>
      ))}

      {/* Add key form */}
      <div className="flex gap-2">
        <input
          type="password"
          value={newKey}
          onChange={(e) => { setNewKey(e.target.value); setAddError(""); }}
          placeholder="Enter API key..."
          className="min-w-0 flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder-muted focus:border-accent/50 focus:outline-none"
        />
        <input
          type="text"
          value={newLabel}
          onChange={(e) => setNewLabel(e.target.value)}
          placeholder="Label (optional)"
          className="w-32 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder-muted focus:border-accent/50 focus:outline-none"
        />
        <button
          onClick={handleAdd}
          disabled={adding || !newKey.trim()}
          className="shrink-0 rounded-lg border border-accent bg-accent/10 px-4 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {adding ? "Adding..." : "+ Add"}
        </button>
      </div>
      {addError && (
        <p className="text-xs text-red-500">{addError}</p>
      )}
    </div>
  );
}
