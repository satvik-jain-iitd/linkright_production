-- 042_broadcast_posts.sql
-- Backfill migration: broadcast_posts (LinkedIn publish queue) + claim RPC.
-- Already in production (created manually). Documenting for version control.
-- Idempotent.

CREATE TABLE IF NOT EXISTS broadcast_posts (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  content             text        NOT NULL,
  status              text        NOT NULL DEFAULT 'draft',
  scheduled_at        timestamptz,
  posted_at           timestamptz,
  linkedin_post_id    text,                                  -- LinkedIn URN after publish
  engagement_json     jsonb,                                  -- {likes, comments, shares, impressions}
  failed_reason       text,
  claimed_at          timestamptz,                            -- broadcast_claim_due lock
  claim_token         uuid,                                   -- broadcast_claim_due lock token
  source_insight_id   uuid,                                   -- diary_entry_id or nugget_id
  source_insight_kind text,                                   -- 'diary' | 'nugget' | 'resume'
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT post_status_valid
    CHECK (status IN ('draft', 'scheduled', 'posted', 'failed', 'cancelled')),
  CONSTRAINT post_kind_valid
    CHECK (source_insight_kind IS NULL
           OR source_insight_kind IN ('nugget', 'diary', 'resume')),
  CONSTRAINT post_content_len CHECK (char_length(content) <= 3000)
);

CREATE INDEX IF NOT EXISTS idx_broadcast_user_created
  ON broadcast_posts (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_broadcast_status
  ON broadcast_posts (status, scheduled_at);
-- The cron's claim query needs this index — finds due, unlocked rows fast.
CREATE INDEX IF NOT EXISTS idx_broadcast_due_unlocked
  ON broadcast_posts (scheduled_at)
  WHERE status = 'scheduled' AND claimed_at IS NULL;

ALTER TABLE broadcast_posts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_reads_own_posts" ON broadcast_posts;
CREATE POLICY "user_reads_own_posts" ON broadcast_posts
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_inserts_own_posts" ON broadcast_posts;
CREATE POLICY "user_inserts_own_posts" ON broadcast_posts
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_updates_own_posts" ON broadcast_posts;
CREATE POLICY "user_updates_own_posts" ON broadcast_posts
  FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_deletes_own_posts" ON broadcast_posts;
CREATE POLICY "user_deletes_own_posts" ON broadcast_posts
  FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "service_writes_posts" ON broadcast_posts;
CREATE POLICY "service_writes_posts" ON broadcast_posts
  FOR ALL USING (auth.role() = 'service_role');

-- Auto-update updated_at trigger.
CREATE OR REPLACE FUNCTION trg_broadcast_posts_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS broadcast_posts_updated_at ON broadcast_posts;
CREATE TRIGGER broadcast_posts_updated_at
  BEFORE UPDATE ON broadcast_posts
  FOR EACH ROW EXECUTE FUNCTION trg_broadcast_posts_updated_at();

-- ────────────────────────────────────────────────────────────────────────────
-- broadcast_claim_due(p_limit) — atomic claim of due 'scheduled' posts.
-- Uses FOR UPDATE SKIP LOCKED so parallel cron polls don't double-claim.
-- Returns the claimed rows. The cron then publishes via LinkedIn API and
-- writes back via /api/broadcast/webhook POST.
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION broadcast_claim_due(p_limit int DEFAULT 20)
RETURNS TABLE (
  post_id      uuid,
  user_id      uuid,
  content      text,
  scheduled_at timestamptz,
  claim_token  uuid
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_token uuid := gen_random_uuid();
BEGIN
  RETURN QUERY
  WITH due AS (
    SELECT id
    FROM broadcast_posts
    WHERE status = 'scheduled'
      AND scheduled_at <= now()
      AND claimed_at IS NULL
    ORDER BY scheduled_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT p_limit
  ),
  upd AS (
    UPDATE broadcast_posts bp
    SET claimed_at = now(), claim_token = v_token
    FROM due
    WHERE bp.id = due.id
    RETURNING bp.id, bp.user_id, bp.content, bp.scheduled_at, bp.claim_token
  )
  SELECT id, user_id, content, scheduled_at, claim_token FROM upd;
END;
$$;
