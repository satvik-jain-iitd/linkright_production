-- 032_broadcast_claim_token.sql
-- Wave 2 / Broadcast idempotency (Part 8 in broadcast-n8n-workflow.md).
--
-- Prevents duplicate LinkedIn posts when n8n's callback fails to reach us:
-- the next poll would otherwise pick up the same post again. A short-lived
-- "claim" on each due post means parallel polls (or retries) see an already-
-- claimed row and skip it.

alter table broadcast_posts
  add column if not exists claimed_at timestamptz,
  add column if not exists claim_token uuid;

-- Index for the claim query (status='scheduled' AND claimed_at IS NULL OR stale).
create index if not exists broadcast_posts_claim_idx
  on broadcast_posts (status, scheduled_at, claimed_at)
  where status = 'scheduled';

-- Helper RPC: atomically claim up to N due posts for the caller (n8n).
-- Stale claims older than 10 min get re-claimed (they probably died mid-flight).
create or replace function broadcast_claim_due(p_limit int default 20)
returns table (
  post_id uuid,
  user_id uuid,
  content text,
  scheduled_at timestamptz,
  claim_token uuid
)
language plpgsql
security definer
as $$
declare
  v_now timestamptz := now();
  v_stale_cutoff timestamptz := v_now - interval '10 minutes';
begin
  return query
    with candidates as (
      select id
      from broadcast_posts
      where status = 'scheduled'
        and scheduled_at <= v_now
        and (claimed_at is null or claimed_at < v_stale_cutoff)
      order by scheduled_at asc
      limit p_limit
      for update skip locked
    )
    update broadcast_posts bp
      set claimed_at = v_now,
          claim_token = gen_random_uuid()
      from candidates c
      where bp.id = c.id
      returning bp.id, bp.user_id, bp.content, bp.scheduled_at, bp.claim_token;
end;
$$;

-- Service-role only — never called from client code.
revoke all on function broadcast_claim_due(int) from public;
grant execute on function broadcast_claim_due(int) to service_role;

-- Release claim helper (called on successful callback so fallback paths
-- don't keep claimed_at lingering). status update to 'posted'/'failed' is
-- enough to take the row out of the due-query, but clearing claim makes
-- the admin dashboard cleaner.
create or replace function broadcast_release_claim(p_post_id uuid)
returns void
language sql
security definer
as $$
  update broadcast_posts
    set claimed_at = null, claim_token = null
    where id = p_post_id;
$$;

revoke all on function broadcast_release_claim(uuid) from public;
grant execute on function broadcast_release_claim(uuid) to service_role;
