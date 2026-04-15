-- Morning Lineup — events table for lightweight in-house analytics.
-- Run AFTER schema.sql in the Supabase SQL Editor. Idempotent.
--
-- Philosophy: no third-party tracker, no cookies, no external dependency.
-- The site already uses Supabase for auth/profiles; this piggybacks on the
-- same project for page views and custom events (share clicks, install
-- accepts, signups).
--
-- Security model:
--   - Anon users can INSERT only (write-only from the browser).
--   - Nobody can SELECT via the anon key — reads happen in the Supabase
--     Table Editor / SQL Editor with the service role, or via a future
--     admin-only auth check.
--
-- Retention: no automatic pruning. If table grows past free-tier row
-- limits, add a scheduled DELETE for rows older than 90 days.

create table if not exists public.events (
  id bigserial primary key,
  event_type text not null,
  team_slug text,
  path text,
  referrer text,
  session_id text,
  ua text,
  created_at timestamptz not null default now()
);

create index if not exists idx_events_created_at on public.events (created_at desc);
create index if not exists idx_events_team       on public.events (team_slug);
create index if not exists idx_events_type       on public.events (event_type);

alter table public.events enable row level security;

drop policy if exists "events_insert_anyone" on public.events;
create policy "events_insert_anyone"
  on public.events for insert
  to anon, authenticated
  with check (true);

-- Intentionally no SELECT/UPDATE/DELETE policies for anon.
-- Queries happen in the Supabase dashboard with the service role.
