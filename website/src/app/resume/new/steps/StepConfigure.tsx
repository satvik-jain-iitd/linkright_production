"use client";

import { useState, useCallback } from "react";
import type { WizardData } from "../WizardShell";
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
        <div className="mt-3 grid grid-cols-3 gap-3">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              onClick={() => handleProviderChange(p.id)}
              className={`rounded-xl border py-4 text-center transition-all ${
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
          className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
