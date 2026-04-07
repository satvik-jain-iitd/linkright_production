-- Add webhook token for external nugget ingestion
-- Used by /api/webhooks/nuggets endpoint for authentication

ALTER TABLE user_settings
  ADD COLUMN IF NOT EXISTS webhook_token uuid DEFAULT gen_random_uuid();

-- Index for fast webhook auth lookup
CREATE INDEX IF NOT EXISTS idx_user_settings_webhook_token
  ON user_settings(webhook_token) WHERE webhook_token IS NOT NULL;

COMMENT ON COLUMN user_settings.webhook_token IS 'Bearer token for /api/webhooks/nuggets endpoint. Regeneratable by user.';
