"use client";

import { useState, useCallback } from "react";
import type { WizardData } from "../WizardShell";
import { KeyManagerPanel } from "@/components/KeyManagerPanel";

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
  const [hasKey, setHasKey] = useState(!!data.api_key);

  const provider = PROVIDERS.find((p) => p.id === data.model_provider) || PROVIDERS[0];

  const handleProviderChange = (providerId: string) => {
    const p = PROVIDERS.find((x) => x.id === providerId)!;
    update({
      model_provider: providerId,
      model_id: p.models[0].id,
      api_key: "",
    });
    setHasKey(false);
  };

  // When KeyManagerPanel reports the primary key ID, update wizard
  const handleKeySelected = useCallback(
    (keyId: string) => {
      if (keyId) {
        // Store the key ID — the pipeline reads the actual key from DB
        update({ api_key: keyId });
        setHasKey(true);
      } else {
        update({ api_key: "" });
        setHasKey(false);
      }
    },
    [update]
  );

  return (
    <div>
      <h2 className="text-2xl font-bold">Configure Your LLM</h2>
      <p className="mt-2 text-sm text-muted">
        Add your API keys below. Keys are stored securely and used for resume
        generation.
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

      {/* API Keys — KeyManagerPanel */}
      <div className="mt-6">
        <label className="text-sm font-semibold uppercase tracking-wide text-muted">
          API Keys
        </label>
        <div className="mt-3">
          <KeyManagerPanel
            provider={data.model_provider}
            providerLabel={provider.name}
            onKeySelected={handleKeySelected}
          />
        </div>
      </div>

      {/* Jina AI embedding keys */}
      <div className="mt-6 border-t border-border pt-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">
          Embedding Keys (Jina AI)
        </h3>
        <p className="text-xs text-gray-500 mb-3">
          Multiple Jina keys run embedding in parallel — 2 keys = 2x faster.
        </p>
        <KeyManagerPanel provider="jina" providerLabel="Jina AI" />
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
          disabled={!hasKey}
          className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
