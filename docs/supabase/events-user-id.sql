-- Add user_id to events for identity-stitched analytics.
-- Run AFTER events.sql. Idempotent.
--
-- Anon pageviews get user_id = null and are grouped by session_id.
-- Signed-in pageviews get user_id = auth.uid() and are grouped by user_id.
-- A query that coalesces the two gives you per-person rollups.

alter table public.events
  add column if not exists user_id uuid references public.profiles(id) on delete set null;

create index if not exists idx_events_user_id
  on public.events (user_id)
  where user_id is not null;

-- Tighten the insert policy so a malicious client can't spoof somebody
-- else's user_id. Anon rows must leave user_id null; authenticated rows
-- must set it to their own auth.uid() (or null, which still groups by session).
drop policy if exists "events_insert_anyone" on public.events;
create policy "events_insert_anyone"
  on public.events for insert
  to anon, authenticated
  with check (
    user_id is null
    or user_id = auth.uid()
  );
