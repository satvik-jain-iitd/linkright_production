"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";

const PROVIDERS = [
  {
    id: "openrouter",
    name: "OpenRouter",
    models: [
      { id: "meta-llama/llama-3.3-70b-instruct:free", name: "Llama 3.3 70B (Free)" },
      { id: "meta-llama/llama-3.3-70b-instruct", name: "Llama 3.3 70B" },
      { id: "google/gemini-2.0-flash-001", name: "Gemini 2.0 Flash" },
      { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet" },
    ],
  },
  {
    id: "groq",
    name: "Groq",
    models: [
      { id: "llama-3.3-70b-versatile", name: "Llama 3.3 70B" },
      { id: "llama-3.1-8b-instant", name: "Llama 3.1 8B Instant" },
      { id: "mixtral-8x7b-32768", name: "Mixtral 8x7B" },
    ],
  },
  {
    id: "gemini",
    name: "Google Gemini",
    models: [
      { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash" },
      { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro" },
    ],
  },
];

export function SettingsContent({ user }: { user: User }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");

  const [modelProvider, setModelProvider] = useState("groq");
  const [modelId, setModelId] = useState("llama-3.3-70b-versatile");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [careerText, setCareerText] = useState("");
  const [savingCareer, setSavingCareer] = useState(false);
  const [careerStatus, setCareerStatus] = useState<"idle" | "saved" | "error">("idle");

  useEffect(() => {
    fetch("/api/user/settings")
      .then((r) => r.json())
      .then((d) => {
        if (d.model_provider) setModelProvider(d.model_provider);
        if (d.model_id) setModelId(d.model_id);
        if (d.api_key) setApiKey(d.api_key);
        if (d.career_text) setCareerText(d.career_text);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const provider = PROVIDERS.find((p) => p.id === modelProvider) || PROVIDERS[0];

  const handleProviderChange = (id: string) => {
    const p = PROVIDERS.find((x) => x.id === id)!;
    setModelProvider(id);
    setModelId(p.models[0].id);
  };

  const saveSettings = async () => {
    setSaving(true);
    setSaveStatus("idle");
    try {
      const resp = await fetch("/api/user/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_provider: modelProvider, model_id: modelId, api_key: apiKey }),
      });
      setSaveStatus(resp.ok ? "saved" : "error");
    } catch {
      setSaveStatus("error");
    } finally {
      setSaving(false);
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  };

  const saveCareerProfile = async () => {
    if (careerText.trim().length < 200) {
      setCareerStatus("error");
      setTimeout(() => setCareerStatus("idle"), 3000);
      return;
    }
    setSavingCareer(true);
    setCareerStatus("idle");
    try {
      const resp = await fetch("/api/career/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ career_text: careerText }),
      });
      setCareerStatus(resp.ok ? "saved" : "error");
    } catch {
      setCareerStatus("error");
    } finally {
      setSavingCareer(false);
      setTimeout(() => setCareerStatus("idle"), 3000);
    }
  };

  if (loading) {
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
          <Link href="/dashboard" className="text-sm text-muted transition-colors hover:text-foreground">
            ← Dashboard
          </Link>
          <span className="text-sm text-muted">
            {user.user_metadata?.full_name || user.email}
          </span>
        </div>
      </nav>

      <div className="mx-auto max-w-2xl px-6 py-12 space-y-10">
        <h1 className="text-2xl font-bold">Settings</h1>

        {/* LLM Configuration */}
        <div className="rounded-2xl border border-border bg-surface p-6">
          <h2 className="text-base font-semibold">LLM Configuration</h2>
          <p className="mt-1 text-sm text-muted">
            Your default provider and API key used for resume generation.
          </p>

          <div className="mt-6 space-y-5">
            {/* Provider */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                Provider
              </label>
              <div className="mt-2 flex gap-2">
                {PROVIDERS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => handleProviderChange(p.id)}
                    className={`flex-1 rounded-xl border py-3 text-center text-sm font-medium transition-all ${
                      modelProvider === p.id
                        ? "border-accent bg-accent/10 text-accent"
                        : "border-border bg-background text-muted hover:border-accent/30"
                    }`}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Model */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                Model
              </label>
              <select
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
                className="mt-2 w-full rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground focus:border-accent/50 focus:outline-none"
              >
                {provider.models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* API Key */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                API Key
              </label>
              <div className="mt-2 flex gap-2">
                <input
                  type={showKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={`Your ${provider.name} API key`}
                  className="flex-1 rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground placeholder-muted focus:border-accent/50 focus:outline-none"
                />
                <button
                  onClick={() => setShowKey((s) => !s)}
                  className="rounded-xl border border-border bg-background px-4 py-3 text-sm text-muted hover:text-foreground"
                >
                  {showKey ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={saveSettings}
                disabled={saving}
                className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:opacity-40"
              >
                {saving ? "Saving..." : "Save Settings"}
              </button>
              {saveStatus === "saved" && (
                <span className="text-sm text-green-600">Saved</span>
              )}
              {saveStatus === "error" && (
                <span className="text-sm text-red-500">Failed to save</span>
              )}
            </div>
          </div>
        </div>

        {/* Career Profile */}
        <div className="rounded-2xl border border-border bg-surface p-6">
          <h2 className="text-base font-semibold">Career Profile</h2>
          <p className="mt-1 text-sm text-muted">
            Your career profile is used to auto-fill enrichment questions and inform the resume pipeline. Minimum 200 characters.
          </p>

          <div className="mt-5">
            <textarea
              value={careerText}
              onChange={(e) => setCareerText(e.target.value)}
              placeholder="Paste your career profile here (Markdown or plain text)..."
              className="w-full rounded-xl border border-border bg-background p-4 text-sm text-foreground placeholder-muted focus:border-accent/50 focus:outline-none"
              rows={18}
            />
            <div className="mt-2 flex items-center justify-between">
              <span className="text-xs text-muted">{careerText.length} characters</span>
              {careerText.length < 200 && careerText.length > 0 && (
                <span className="text-xs text-red-400">Minimum 200 characters required</span>
              )}
            </div>
          </div>

          <div className="mt-4 flex items-center gap-4">
            <button
              onClick={saveCareerProfile}
              disabled={savingCareer || careerText.trim().length < 200}
              className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:opacity-40"
            >
              {savingCareer ? "Saving..." : "Update Profile"}
            </button>
            {careerStatus === "saved" && (
              <span className="text-sm text-green-600">Profile updated</span>
            )}
            {careerStatus === "error" && (
              <span className="text-sm text-red-500">
                {careerText.trim().length < 200 ? "Too short — need 200+ characters" : "Failed to save"}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
