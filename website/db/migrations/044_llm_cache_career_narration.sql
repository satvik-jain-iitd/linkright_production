-- Migration 044: Career narration cache
--
-- Why: /api/onboarding/narrate-career is the hottest single LLM call in onboarding.
-- Reasoning chain calls Gemini Flash (~10-30s for 8000 tokens) every time.
-- Same experiences+projects → same narration text. SHA256 cache eliminates
-- repeat LLM round-trips for identical inputs (test fixtures, retried flows,
-- repeat sessions).
--
-- Also addresses production flakiness: streaming Gemini occasionally returns
-- 0 chunks silently — stream "succeeds" with empty body, UI shows
-- "No narration generated yet" + "Write narration" CTA. Cache + dropping
-- streaming in favor of the more reliable non-streaming fallback chain
-- (Gemini → Groq 70b → OpenRouter → Oracle) makes narration deterministic.
--
-- This cache is GLOBAL (no user_id) — same as 037 and 043. Narration text
-- is sensitive but the row is keyed by sha256 of structured experience JSON
-- — only callers who already have the original input can look it up.
--
-- Run in Supabase SQL editor.

CREATE TABLE IF NOT EXISTS llm_cache_career_narration (
  narration_hash   text          PRIMARY KEY,        -- sha256(JSON of experiences + projects)
  narration_text   text          NOT NULL,           -- full markdown narration body
  llm_model        text          NOT NULL,
  prompt_version   text,
  created_at       timestamptz   DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_llm_cache_career_narration_created
  ON llm_cache_career_narration (created_at DESC);
