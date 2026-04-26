-- 039_sma_post_drafts.sql
-- SMA_v2 draft store: holds the LLM-generated LinkedIn post for a picked concept.
-- Created when user picks a concept from sma_suggestions inbox.
-- Promoted to broadcast_posts on publish (broadcast cron handles LinkedIn API).
-- Idempotent: re-runs are safe.

CREATE TABLE IF NOT EXISTS sma_post_drafts (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  suggestion_id         uuid        REFERENCES sma_suggestions ON DELETE CASCADE,
  concept_index         int         NOT NULL,
  draft_content         text        NOT NULL,
  status                text        NOT NULL DEFAULT 'draft',
  broadcast_post_id     uuid,                                -- set after publish to broadcast_posts
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT valid_draft_status CHECK (status IN ('draft', 'edited', 'published', 'discarded'))
);

CREATE INDEX IF NOT EXISTS idx_sma_drafts_user_status
  ON sma_post_drafts (user_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sma_drafts_suggestion
  ON sma_post_drafts (suggestion_id);

ALTER TABLE sma_post_drafts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_reads_own_drafts" ON sma_post_drafts
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "user_updates_own_drafts" ON sma_post_drafts
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "user_inserts_own_drafts" ON sma_post_drafts
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "service_writes_drafts" ON sma_post_drafts
  FOR ALL USING (auth.role() = 'service_role');

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION trg_sma_post_drafts_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS sma_post_drafts_updated_at ON sma_post_drafts;
CREATE TRIGGER sma_post_drafts_updated_at
  BEFORE UPDATE ON sma_post_drafts
  FOR EACH ROW EXECUTE FUNCTION trg_sma_post_drafts_updated_at();
