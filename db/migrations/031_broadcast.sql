-- 031_broadcast.sql
-- Wave 2 / S15-S18 — Broadcast (LinkedIn post draft + schedule + tracker).
--
-- Tables:
--   user_integrations — OAuth tokens for external services (LinkedIn first,
--                       extensible for GitHub / Twitter / etc.)
--   broadcast_posts   — drafts, scheduled, and posted LinkedIn posts.
--
-- The posting pipeline itself (n8n) reads broadcast_posts where status =
-- 'scheduled' AND scheduled_at <= now(), posts via LinkedIn API, writes
-- engagement back on a cron.

create table if not exists user_integrations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  provider text not null check (provider in ('linkedin', 'github', 'twitter', 'x', 'medium')),
  access_token text,
  refresh_token text,
  token_type text default 'Bearer',
  expires_at timestamptz,
  scope text,
  external_user_id text,
  external_handle text,
  profile_url text,
  status text not null default 'connected' check (status in ('connected', 'revoked', 'expired')),
  connected_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, provider)
);

alter table user_integrations enable row level security;

drop policy if exists "integrations_own" on user_integrations;
create policy "integrations_own"
  on user_integrations
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create table if not exists broadcast_posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'draft' check (status in ('draft', 'scheduled', 'posted', 'failed', 'cancelled')),
  content text not null,
  source_insight_id uuid,            -- optional: career_nuggets / diary entry
  source_insight_kind text,          -- 'nugget' | 'diary' | 'resume'
  linkedin_post_id text,             -- LinkedIn urn after posting
  scheduled_at timestamptz,
  posted_at timestamptz,
  failed_reason text,
  engagement_json jsonb,             -- { likes, comments, shares, impressions }
  tone_edits jsonb default '[]',     -- history of tone adjustments
  regens_used int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists broadcast_posts_user_status_idx
  on broadcast_posts (user_id, status, scheduled_at);

create index if not exists broadcast_posts_due_idx
  on broadcast_posts (status, scheduled_at)
  where status = 'scheduled';

alter table broadcast_posts enable row level security;

drop policy if exists "broadcast_select_own" on broadcast_posts;
create policy "broadcast_select_own"
  on broadcast_posts
  for select
  using (auth.uid() = user_id);

drop policy if exists "broadcast_insert_own" on broadcast_posts;
create policy "broadcast_insert_own"
  on broadcast_posts
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "broadcast_update_own" on broadcast_posts;
create policy "broadcast_update_own"
  on broadcast_posts
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "broadcast_delete_own" on broadcast_posts;
create policy "broadcast_delete_own"
  on broadcast_posts
  for delete
  using (auth.uid() = user_id);

-- touch updated_at on change (Postgres doesn't ship this by default)
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists broadcast_posts_set_updated_at on broadcast_posts;
create trigger broadcast_posts_set_updated_at
  before update on broadcast_posts
  for each row execute function set_updated_at();

drop trigger if exists user_integrations_set_updated_at on user_integrations;
create trigger user_integrations_set_updated_at
  before update on user_integrations
  for each row execute function set_updated_at();
