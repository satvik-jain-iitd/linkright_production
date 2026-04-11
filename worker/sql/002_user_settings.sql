-- Migration 002: Create user_settings table
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor > New query)

CREATE TABLE IF NOT EXISTS user_settings (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id),
  model_provider TEXT DEFAULT 'groq',
  model_id TEXT DEFAULT 'llama-3.1-8b-instant',
  api_key TEXT,
  career_graph JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: users can only read/write their own row
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own settings" ON user_settings
  FOR ALL USING (auth.uid() = user_id);
