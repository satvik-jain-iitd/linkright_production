"use client";

// [BYOK-REMOVED] These imports are no longer needed
// import { useEffect, useState } from "react";
// import Link from "next/link";
// import type { User } from "@supabase/supabase-js";
// import { KeyManagerPanel } from "@/components/KeyManagerPanel";

/* [BYOK-REMOVED]
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
*/

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function SettingsContent(_props?: any) {
  // [BYOK-REMOVED] Full settings page removed — BYOK eliminated, server manages LLM keys
  // Original ~320 line component had: LLM provider/model selector, KeyManagerPanel for 11 providers,
  // webhook token management, and ChatGPT bot setup guide. See git history for full implementation.
  return (
    <div className="max-w-2xl mx-auto p-8 text-center">
      <h2 className="text-xl font-semibold text-foreground mb-2">Settings</h2>
      <p className="text-muted text-sm">Settings have been simplified. Your resumes are now generated using our optimized AI pipeline — no configuration needed.</p>
    </div>
  );
}
