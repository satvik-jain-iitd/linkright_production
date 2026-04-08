"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";
import { KeyManagerPanel } from "@/components/KeyManagerPanel";

const PROVIDERS = [
  {
    id: "groq",
    name: "Groq",
    description: "Free · 30 RPM · 14,400 RPD",
    models: [
      { id: "llama-3.1-8b-instant",             name: "Llama 3.1 8B Instant  (fastest, free)" },
      { id: "allam-2-7b",                        name: "ALLaM 2 7B  (Arabic/English, free)" },
      { id: "gemma2-9b-it",                      name: "Gemma 2 9B  (free)" },
      { id: "llama-3.3-70b-versatile",           name: "Llama 3.3 70B  (best quality)" },
      { id: "deepseek-r1-distill-llama-70b",     name: "DeepSeek R1 Distill 70B  (reasoning)" },
      { id: "qwen-qwq-32b",                      name: "Qwen QwQ 32B  (reasoning)" },
      { id: "mixtral-8x7b-32768",                name: "Mixtral 8x7B  (long context)" },
    ],
  },
  {
    id: "cerebras",
    name: "Cerebras",
    description: "Free · 1M tok/day · ~2200 tok/s",
    models: [
      { id: "llama3.1-8b",    name: "Llama 3.1 8B  (fastest inference)" },
      { id: "llama-3.3-70b",  name: "Llama 3.3 70B" },
    ],
  },
  {
    id: "sambanova",
    name: "SambaNova",
    description: "Free · 30 RPM",
    models: [
      { id: "Meta-Llama-3.1-8B-Instruct",   name: "Llama 3.1 8B  (free)" },
      { id: "Meta-Llama-3.3-70B-Instruct",  name: "Llama 3.3 70B  (free)" },
    ],
  },
  {
    id: "siliconflow",
    name: "SiliconFlow",
    description: "Free · 1000 RPM (highest burst)",
    models: [
      { id: "Qwen/Qwen3-8B",                               name: "Qwen3 8B  (free, 1000 RPM)" },
      { id: "Qwen/Qwen2.5-7B-Instruct",                    name: "Qwen 2.5 7B  (free)" },
      { id: "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",     name: "DeepSeek R1 Distill 7B  (reasoning, free)" },
    ],
  },
  {
    id: "nvidia",
    name: "NVIDIA NIM",
    description: "Free · 40 RPM",
    models: [
      { id: "meta/llama-3.2-1b-instruct",              name: "Llama 3.2 1B  (smallest, free)" },
      { id: "meta/llama-3.1-8b-instruct",              name: "Llama 3.1 8B  (free)" },
      { id: "mistralai/mistral-7b-instruct-v0.3",      name: "Mistral 7B  (free)" },
    ],
  },
  {
    id: "github",
    name: "GitHub Models",
    description: "Free · 15 RPM · use GitHub PAT",
    models: [
      { id: "Phi-3.5-mini-instruct",                   name: "Phi-3.5 Mini 3.8B  (free)" },
      { id: "Phi-3-mini-4k-instruct",                  name: "Phi-3 Mini 3.8B  (free)" },
      { id: "meta-llama/Llama-3.2-1B-Instruct",        name: "Llama 3.2 1B  (free)" },
      { id: "meta-llama/Llama-3.2-3B-Instruct",        name: "Llama 3.2 3B  (free)" },
    ],
  },
  {
    id: "mistral",
    name: "Mistral AI",
    description: "Free · 2 RPM (low)",
    models: [
      { id: "ministral-3b-2512",   name: "Ministral 3B  (free)" },
      { id: "ministral-3-8b-2512", name: "Ministral 8B  (free)" },
    ],
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    description: "200+ models · free tier",
    models: [
      { id: "meta-llama/llama-3.2-3b-instruct:free",   name: "Llama 3.2 3B  (free)" },
      { id: "google/gemma-3-4b-it:free",               name: "Gemma 3 4B  (free)" },
      { id: "meta-llama/llama-3.3-70b-instruct:free",  name: "Llama 3.3 70B  (free)" },
      { id: "deepseek/deepseek-chat:free",             name: "DeepSeek V3  (free)" },
      { id: "google/gemini-2.0-flash-exp:free",        name: "Gemini 2.0 Flash Exp  (free)" },
      { id: "meta-llama/llama-3.3-70b-instruct",       name: "Llama 3.3 70B  (paid)" },
      { id: "anthropic/claude-3.5-sonnet",             name: "Claude 3.5 Sonnet  (paid)" },
    ],
  },
  {
    id: "gemini",
    name: "Google Gemini",
    description: "Free AI Studio key",
    models: [
      { id: "gemini-1.5-flash-8b",   name: "Gemini 1.5 Flash 8B  (highest free limits)" },
      { id: "gemini-2.5-flash-lite", name: "Gemini 2.5 Flash Lite  (fast, free)" },
      { id: "gemini-1.5-flash",      name: "Gemini 1.5 Flash  (free)" },
      { id: "gemini-2.5-flash",      name: "Gemini 2.5 Flash  (free)" },
      { id: "gemini-1.5-pro",        name: "Gemini 1.5 Pro  (long context)" },
    ],
  },
];

export function SettingsContent({ user }: { user: User }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");

  const [modelProvider, setModelProvider] = useState("groq");
  const [modelId, setModelId] = useState("llama-3.3-70b-versatile");
  // Webhook token
  const [webhookTokenMasked, setWebhookTokenMasked] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookFullToken, setWebhookFullToken] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const [webhookCopied, setWebhookCopied] = useState<"" | "token" | "url">("");

  useEffect(() => {
    fetch("/api/user/settings")
      .then((r) => r.json())
      .then((d) => {
        if (d.model_provider) setModelProvider(d.model_provider);
        if (d.model_id) setModelId(d.model_id);
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    // Fetch webhook token
    fetch("/api/user/webhook-token")
      .then((r) => r.json())
      .then((d) => {
        if (d.token_masked) setWebhookTokenMasked(d.token_masked);
        if (d.url) setWebhookUrl(d.url);
      })
      .catch(() => {});
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
        body: JSON.stringify({ model_provider: modelProvider, model_id: modelId }),
      });
      setSaveStatus(resp.ok ? "saved" : "error");
    } catch {
      setSaveStatus("error");
    } finally {
      setSaving(false);
      setTimeout(() => setSaveStatus("idle"), 3000);
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
            Your default provider and model used for resume generation.
          </p>

          <div className="mt-6 space-y-5">
            {/* Provider */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                Provider
              </label>
              <div className="mt-2 grid grid-cols-3 gap-2">
                {PROVIDERS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => handleProviderChange(p.id)}
                    className={`rounded-xl border py-3 text-center text-sm font-medium transition-all ${
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

        {/* API Key Management */}
        <div className="rounded-2xl border border-border bg-surface p-6">
          <h2 className="text-base font-semibold">API Key Management</h2>
          <p className="mt-1 text-sm text-muted">
            Manage API keys for all providers. Keys are stored securely and rotated automatically on failure.
          </p>
          <div className="mt-5 space-y-4">
            <KeyManagerPanel provider="groq" providerLabel="Groq" />
            <KeyManagerPanel provider="cerebras" providerLabel="Cerebras" />
            <KeyManagerPanel provider="sambanova" providerLabel="SambaNova" />
            <KeyManagerPanel provider="siliconflow" providerLabel="SiliconFlow" />
            <KeyManagerPanel provider="nvidia" providerLabel="NVIDIA NIM" />
            <KeyManagerPanel provider="github" providerLabel="GitHub Models" />
            <KeyManagerPanel provider="mistral" providerLabel="Mistral AI" />
            <KeyManagerPanel provider="openrouter" providerLabel="OpenRouter" />
            <KeyManagerPanel provider="gemini" providerLabel="Google Gemini" />
            <KeyManagerPanel provider="jina" providerLabel="Jina AI" />
            <KeyManagerPanel provider="anthropic" providerLabel="Anthropic" />
          </div>
        </div>

        {/* Webhook Token */}
        <div className="rounded-2xl border border-border bg-surface p-6">
          <h2 className="text-base font-semibold">Webhook Integration</h2>
          <p className="mt-1 text-sm text-muted">
            Use this token to push nuggets from external tools (e.g., Claude, ChatGPT, automation scripts) via the webhook API.
          </p>

          <div className="mt-5 space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                Webhook URL
              </label>
              <div className="mt-2 flex gap-2">
                <code className="flex-1 rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground font-mono">
                  {webhookUrl || "https://sync.linkright.in/api/webhooks/nuggets"}
                </code>
                <button
                  onClick={async () => {
                    await navigator.clipboard.writeText(webhookUrl || "https://sync.linkright.in/api/webhooks/nuggets");
                    setWebhookCopied("url");
                    setTimeout(() => setWebhookCopied(""), 2000);
                  }}
                  className="rounded-xl border border-border bg-background px-4 py-3 text-sm text-muted hover:text-foreground"
                >
                  {webhookCopied === "url" ? "Copied" : "Copy"}
                </button>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                Bearer Token
              </label>
              <div className="mt-2 flex gap-2">
                <code className="flex-1 rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground font-mono">
                  {webhookFullToken || webhookTokenMasked || "No token generated yet"}
                </code>
                {webhookFullToken && (
                  <button
                    onClick={async () => {
                      await navigator.clipboard.writeText(webhookFullToken);
                      setWebhookCopied("token");
                      setTimeout(() => setWebhookCopied(""), 2000);
                    }}
                    className="rounded-xl border border-border bg-background px-4 py-3 text-sm text-muted hover:text-foreground"
                  >
                    {webhookCopied === "token" ? "Copied" : "Copy"}
                  </button>
                )}
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={async () => {
                  setRegenerating(true);
                  try {
                    const resp = await fetch("/api/user/webhook-token", { method: "POST" });
                    const d = await resp.json();
                    if (d.token) {
                      setWebhookFullToken(d.token);
                      setWebhookTokenMasked("");
                    }
                  } catch {}
                  setRegenerating(false);
                }}
                disabled={regenerating}
                className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:opacity-40"
              >
                {regenerating ? "Regenerating..." : webhookTokenMasked ? "Regenerate Token" : "Generate Token"}
              </button>
              {webhookFullToken && (
                <span className="text-xs text-amber-600">
                  Save this token now — it won&apos;t be shown again after you leave this page.
                </span>
              )}
            </div>

            <div className="rounded-xl border border-border bg-background p-4">
              <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Usage</p>
              <pre className="text-xs text-foreground/70 font-mono whitespace-pre-wrap">{`curl -X POST ${webhookUrl || "https://sync.linkright.in/api/webhooks/nuggets"} \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"data": "[{\\"nugget_text\\": \\"...\\", \\"answer\\": \\"...\\", \\"primary_layer\\": \\"A\\", ...}]"}'`}</pre>
            </div>
          </div>
        </div>

        {/* Custom ChatGPT Action Setup Guide */}
        <div className="rounded-2xl border border-border bg-surface p-6">
          <h2 className="text-base font-semibold">Custom ChatGPT Diary Bot</h2>
          <p className="mt-1 text-sm text-muted">
            Create a Custom GPT that acts as your career diary. Speak naturally about your day,
            achievements, and projects. When you say &quot;send to LinkRight&quot;, it extracts
            structured nuggets and sends them to your account automatically.
          </p>

          <div className="mt-5 space-y-4">
            <div className="border-l-4 border-blue-500 pl-4">
              <h3 className="font-medium text-sm">Step 1: Create Custom GPT</h3>
              <p className="text-xs text-muted mt-1">
                Go to <a href="https://chat.openai.com/gpts/editor" target="_blank" rel="noopener noreferrer" className="text-accent underline">chat.openai.com/gpts/editor</a> and create a new GPT.
              </p>
            </div>

            <div className="border-l-4 border-blue-500 pl-4">
              <h3 className="font-medium text-sm">Step 2: Set Instructions</h3>
              <p className="text-xs text-muted mt-1">
                Paste this as the GPT&apos;s instructions:
              </p>
              <pre className="mt-2 p-3 bg-background rounded-xl border border-border text-xs overflow-x-auto max-h-40 overflow-y-auto font-mono">
{`You are a career diary assistant. Listen to the user talk about their work day, achievements, projects, and career events. Be conversational and supportive.

When the user says "send to LinkRight" or "save this" or "extract nuggets", do the following:
1. Extract all career nuggets from the conversation using the Two-Layer model
2. Format each as a JSON object with: nugget_text, answer, primary_layer, section_type, company, role, event_date, importance, resume_relevance, tags, leadership_signal
3. Call the sendNuggets action with the extracted nuggets

Rules for extraction:
- Every work_experience nugget MUST have company and role
- Answers must be self-contained with company, role, and timeframe
- Include metrics (%, $, numbers) when mentioned
- Set importance: P0=career-defining, P1=strong, P2=contextual, P3=peripheral`}
              </pre>
            </div>

            <div className="border-l-4 border-blue-500 pl-4">
              <h3 className="font-medium text-sm">Step 3: Add Action</h3>
              <p className="text-xs text-muted mt-1">
                In the GPT editor, go to &quot;Actions&quot; → &quot;Create new action&quot; → &quot;Import from URL&quot; and enter:
              </p>
              <code className="block mt-2 p-2 bg-background rounded-xl border border-border text-xs font-mono">
                https://sync.linkright.in/openapi-nuggets.yaml
              </code>
            </div>

            <div className="border-l-4 border-blue-500 pl-4">
              <h3 className="font-medium text-sm">Step 4: Set Authentication</h3>
              <p className="text-xs text-muted mt-1">
                In the action settings, set Authentication to &quot;API Key&quot;, Auth Type: &quot;Bearer&quot;,
                and paste your webhook token from above.
              </p>
            </div>

            <div className="border-l-4 border-green-500 pl-4">
              <h3 className="font-medium text-sm">Done!</h3>
              <p className="text-xs text-muted mt-1">
                Now chat with your GPT about your day. When ready, say &quot;send to LinkRight&quot;
                and your nuggets will appear in the dashboard automatically.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
