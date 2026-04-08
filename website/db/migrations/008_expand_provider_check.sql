-- Expand provider CHECK constraint to include new free providers
-- Run in Supabase SQL Editor (no auto-migration runner)
-- See: 004_user_api_keys.sql for original constraint

ALTER TABLE user_api_keys DROP CONSTRAINT user_api_keys_provider_check;

ALTER TABLE user_api_keys ADD CONSTRAINT user_api_keys_provider_check
  CHECK (provider IN (
    'openrouter', 'groq', 'gemini', 'jina', 'anthropic',
    'cerebras', 'sambanova', 'siliconflow', 'nvidia', 'github', 'mistral'
  ));
