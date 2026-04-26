-- 036_user_journey_mapping.sql
-- Links users to their specific interview journey bucket.

-- Add journey_bucket_slug to users for fast lookup
alter table public.users add column if not exists journey_bucket_slug text references interview_journey_buckets(slug);

-- Function to automatically set journey bucket based on profile/role if empty
create or replace function set_initial_journey_bucket()
returns trigger as $$
begin
  if new.journey_bucket_slug is null then
    -- Default to product_manager as the most common profile for LinkRight
    new.journey_bucket_slug := 'product_manager';
  end if;
  return new;
end;
$$ language plpgsql;

create trigger tr_set_initial_journey_bucket
before insert on public.users
for each row execute function set_initial_journey_bucket();
