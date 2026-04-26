-- 041_user_integrations.sql
-- Backfill migration: user_integrations table for per-user OAuth tokens.
-- Currently used for LinkedIn Broadcast pillar (and future: GitHub, Telegram).
-- Already exists in production (created manually). Documenting for version control.
-- Idempotent.

CREATE TABLE IF NOT EXISTS user_integrations (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  provider          text        NOT NULL,
  access_token      text,
  refresh_token     text,
  token_type        text,
  expires_at        timestamptz,
  scope             text,
  external_user_id  text,                    -- LinkedIn URN, GitHub login, etc.
  external_handle   text,                    -- human-readable handle/username
  profile_url       text,
  status            text        NOT NULL DEFAULT 'connected',
  connected_at      timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT integration_status_valid
    CHECK (status IN ('connected', 'revoked', 'expired', 'error')),
  CONSTRAINT uniq_user_provider UNIQUE (user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_integrations_user
  ON user_integrations (user_id);
CREATE INDEX IF NOT EXISTS idx_integrations_provider_status
  ON user_integrations (provider, status);
-- Used by cron/refresh-linkedin-tokens to find tokens about to expire.
CREATE INDEX IF NOT EXISTS idx_integrations_expires
  ON user_integrations (provider, expires_at)
  WHERE status = 'connected';

ALTER TABLE user_integrations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_reads_own_integrations" ON user_integrations;
CREATE POLICY "user_reads_own_integrations" ON user_integrations
  FOR SELECT USING (auth.uid() = user_id);

-- No INSERT/UPDATE/DELETE for user — OAuth callback uses service role.
DROP POLICY IF EXISTS "service_writes_integrations" ON user_integrations;
CREATE POLICY "service_writes_integrations" ON user_integrations
  FOR ALL USING (auth.role() = 'service_role');

-- Auto-update updated_at on row change.
CREATE OR REPLACE FUNCTION trg_user_integrations_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS user_integrations_updated_at ON user_integrations;
CREATE TRIGGER user_integrations_updated_at
  BEFORE UPDATE ON user_integrations
  FOR EACH ROW EXECUTE FUNCTION trg_user_integrations_updated_at();
