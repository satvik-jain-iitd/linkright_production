"use client";

import { useState } from "react";
import type { WizardData } from "../WizardShell";

const PROVIDERS = [
  {
    id: "openrouter",
    name: "OpenRouter",
    description: "200+ models, free tier available",
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
    description: "Ultra-fast inference",
    models: [
      { id: "llama-3.3-70b-versatile", name: "Llama 3.3 70B" },
      { id: "llama-3.1-8b-instant", name: "Llama 3.1 8B Instant" },
      { id: "mixtral-8x7b-32768", name: "Mixtral 8x7B" },
    ],
  },
  {
    id: "gemini",
    name: "Google Gemini",
    description: "Direct Gemini API",
    models: [
      { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash" },
      { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro" },
    ],
  },
];

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

export function StepConfigure({ data, update, next, back }: Props) {
  const [validating, setValidating] = useState(false);
  const [keyStatus, setKeyStatus] = useState<"idle" | "valid" | "invalid">("idle");

  const provider = PROVIDERS.find((p) => p.id === data.model_provider) || PROVIDERS[0];

  const handleProviderChange = (providerId: string) => {
    const p = PROVIDERS.find((x) => x.id === providerId)!;
    update({
      model_provider: providerId,
      model_id: p.models[0].id,
      api_key: "",
    });
    setKeyStatus("idle");
  };

  const validateKey = async () => {
    if (!data.api_key.trim()) return;
    setValidating(true);
    try {
      const resp = await fetch("/api/keys/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: data.model_provider, api_key: data.api_key }),
      });
      const result = await resp.json();
      setKeyStatus(result.valid ? "valid" : "invalid");
    } catch {
      setKeyStatus("invalid");
    }
    setValidating(false);
  };

  const canProceed = data.api_key.trim().length > 0 && keyStatus === "valid";

  return (
    <div>
      <h2 className="text-2xl font-bold">Configure Your LLM</h2>
      <p className="mt-2 text-sm text-muted">
        Bring your own API key. We never store it — it&apos;s sent directly to
        the provider for this session only.
      </p>

      {/* Provider selection */}
      <div className="mt-8">
        <label className="text-sm font-semibold uppercase tracking-wide text-muted">
          Provider
        </label>
        <div className="mt-3 flex gap-3">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              onClick={() => handleProviderChange(p.id)}
              className={`flex-1 rounded-xl border py-4 text-center transition-all ${
                data.model_provider === p.id
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-border bg-surface text-muted hover:border-accent/30"
              }`}
            >
              <div className="text-sm font-semibold">{p.name}</div>
              <div className="mt-1 text-xs text-muted">{p.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Model selection */}
      <div className="mt-6">
        <label className="text-sm font-semibold uppercase tracking-wide text-muted">
          Model
        </label>
        <select
          value={data.model_id}
          onChange={(e) => update({ model_id: e.target.value })}
          className="mt-3 w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-foreground transition-colors focus:border-accent/50 focus:outline-none"
        >
          {provider.models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </div>

      {/* API key */}
      <div className="mt-6">
        <label className="text-sm font-semibold uppercase tracking-wide text-muted">
          API Key
        </label>
        <div className="mt-3 flex gap-3">
          <input
            type="password"
            value={data.api_key}
            onChange={(e) => {
              update({ api_key: e.target.value });
              setKeyStatus("idle");
            }}
            placeholder={`Paste your ${provider.name} API key`}
            className="flex-1 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-foreground placeholder-muted transition-colors focus:border-accent/50 focus:outline-none"
          />
          <button
            onClick={validateKey}
            disabled={!data.api_key.trim() || validating}
            className="rounded-xl border border-accent bg-accent/10 px-5 py-3 text-sm font-medium text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {validating ? "Checking..." : "Validate"}
          </button>
        </div>
        {keyStatus === "valid" && (
          <p className="mt-2 text-sm text-green-600">Key is valid</p>
        )}
        {keyStatus === "invalid" && (
          <p className="mt-2 text-sm text-red-500">Invalid key — check and try again</p>
        )}
      </div>

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={back}
          className="text-sm text-muted transition-colors hover:text-foreground"
        >
          &larr; Back
        </button>
        <button
          onClick={next}
          disabled={!canProceed}
          className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
