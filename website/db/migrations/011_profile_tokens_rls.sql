-- RLS policies for profile_tokens table
-- Fixes: "new row violates row-level security policy for table profile_tokens"
-- Run this against Supabase if RLS was enabled without policies.

ALTER TABLE profile_tokens ENABLE ROW LEVEL SECURITY;

-- Authenticated user can read their own tokens
CREATE POLICY "Users can read own profile tokens"
  ON profile_tokens FOR SELECT
  USING (auth.uid() = user_id);

-- Authenticated user can insert tokens for themselves
CREATE POLICY "Users can insert own profile tokens"
  ON profile_tokens FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Authenticated user can update their own tokens (e.g. atoms_saved via RPC)
CREATE POLICY "Users can update own profile tokens"
  ON profile_tokens FOR UPDATE
  USING (auth.uid() = user_id);

-- Service role bypasses RLS automatically — no policy needed for Oracle/verify routes.
