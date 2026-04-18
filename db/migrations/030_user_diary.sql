-- 030_user_diary.sql
-- Wave 2 / S19 — Daily diary feature.
--
-- Storage for 60-second diary entries. Each entry optionally feeds the
-- career memory (embedding) and becomes a source for Broadcast drafts.
-- Streak is computed live from distinct entry dates; no separate counter.

create table if not exists user_diary_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  content text not null check (char_length(content) <= 4000),
  audio_url text,
  transcript text,
  mood text,
  tags text[] default '{}',
  source text default 'web' check (source in ('web', 'extension', 'api', 'import')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists user_diary_entries_user_created_idx
  on user_diary_entries (user_id, created_at desc);

-- RLS — user can only see / write their own diary.
alter table user_diary_entries enable row level security;

drop policy if exists "diary_select_own" on user_diary_entries;
create policy "diary_select_own"
  on user_diary_entries
  for select
  using (auth.uid() = user_id);

drop policy if exists "diary_insert_own" on user_diary_entries;
create policy "diary_insert_own"
  on user_diary_entries
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "diary_update_own" on user_diary_entries;
create policy "diary_update_own"
  on user_diary_entries
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "diary_delete_own" on user_diary_entries;
create policy "diary_delete_own"
  on user_diary_entries
  for delete
  using (auth.uid() = user_id);

-- Helper RPC: current streak (consecutive days including today) for a user.
-- Used by dashboard + notifications. Calculated from distinct entry dates
-- walking back from today.
create or replace function diary_streak(p_user_id uuid)
returns integer
language sql
stable
security invoker
as $$
  with ordered as (
    select distinct (created_at at time zone 'Asia/Kolkata')::date as d
    from user_diary_entries
    where user_id = p_user_id
    order by d desc
  ),
  walk as (
    select d, row_number() over (order by d desc) as rn
    from ordered
  ),
  streak as (
    select d, rn,
           (current_date at time zone 'Asia/Kolkata')::date - (rn - 1) * interval '1 day' as expected
    from walk
  )
  select coalesce(count(*)::int, 0)
  from streak
  where d = expected::date;
$$;

grant execute on function diary_streak(uuid) to authenticated;
