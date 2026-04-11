-- Profile tokens for Custom GPT session linking
-- Used by /api/profile/token (generate), /api/profile/token/verify, /api/profile/token/status

CREATE TABLE IF NOT EXISTS profile_tokens (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  token       text NOT NULL UNIQUE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
  used_at     timestamptz,          -- set when Custom GPT calls /session-close
  atoms_saved integer NOT NULL DEFAULT 0  -- incremented by Oracle on each ingest
);

-- Fast lookup by token (Custom GPT verify + Oracle ingest)
CREATE INDEX IF NOT EXISTS idx_profile_tokens_token
  ON profile_tokens(token);

-- Fast lookup by user (status polling)
CREATE INDEX IF NOT EXISTS idx_profile_tokens_user_id
  ON profile_tokens(user_id, created_at DESC);

COMMENT ON TABLE profile_tokens IS 'Session tokens for linking a user to a Custom GPT career coaching session. 24h expiry.';
COMMENT ON COLUMN profile_tokens.atoms_saved IS 'Number of career atoms successfully ingested in this session. Updated by Oracle ARM backend.';

-- RPC function used by Oracle ARM to safely increment atoms_saved
CREATE OR REPLACE FUNCTION increment_atoms_saved(p_token text)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
AS $$
  UPDATE profile_tokens
  SET atoms_saved = atoms_saved + 1
  WHERE token = p_token;
$$;
