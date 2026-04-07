-- Multi API Key Support
-- Allows users to store multiple API keys per provider with priority-based fallback
-- Run in Supabase SQL editor

CREATE TABLE IF NOT EXISTS user_api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users NOT NULL,
  provider text NOT NULL CHECK (provider IN ('openrouter', 'groq', 'gemini', 'jina', 'anthropic')),
  label text NOT NULL DEFAULT 'default',
  api_key_encrypted text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  priority int NOT NULL DEFAULT 0,
  last_used_at timestamptz,
  last_failed_at timestamptz,
  fail_count int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT unique_user_provider_label UNIQUE (user_id, provider, label)
);

-- Indexes for efficient key lookup
CREATE INDEX IF NOT EXISTS idx_api_keys_user_provider
  ON user_api_keys(user_id, provider) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_api_keys_priority
  ON user_api_keys(user_id, provider, priority) WHERE is_active = true;

-- Row-level security
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own API keys" ON user_api_keys
  FOR ALL USING (auth.uid() = user_id);

-- Comment for documentation
COMMENT ON TABLE user_api_keys IS 'Stores multiple API keys per provider per user. Keys tried in priority order (0=first). Failed keys tracked via fail_count/last_failed_at.';
COMMENT ON COLUMN user_api_keys.api_key_encrypted IS 'API key stored as-is (encrypt at app layer or use Supabase Vault in production)';
COMMENT ON COLUMN user_api_keys.priority IS 'Lower number = tried first. 0 is highest priority.';
