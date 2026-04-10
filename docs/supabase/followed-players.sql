-- followed_players — players a user tracks for the "My Players" home section.
-- Run in Supabase SQL editor after the base schema.

create table if not exists public.followed_players (
  user_id uuid not null references public.profiles(id) on delete cascade,
  mlbam_id bigint not null,
  full_name text not null,
  primary_position text,
  mlb_team_id int,
  mlb_team_abbr text,
  position int not null default 0,
  created_at timestamptz not null default now(),
  primary key (user_id, mlbam_id)
);

create index if not exists followed_players_user_position_idx
  on public.followed_players (user_id, position);

alter table public.followed_players enable row level security;

drop policy if exists "followed_players: select own" on public.followed_players;
create policy "followed_players: select own"
  on public.followed_players for select
  using (auth.uid() = user_id);

drop policy if exists "followed_players: insert own" on public.followed_players;
create policy "followed_players: insert own"
  on public.followed_players for insert
  with check (auth.uid() = user_id);

drop policy if exists "followed_players: update own" on public.followed_players;
create policy "followed_players: update own"
  on public.followed_players for update
  using (auth.uid() = user_id);

drop policy if exists "followed_players: delete own" on public.followed_players;
create policy "followed_players: delete own"
  on public.followed_players for delete
  using (auth.uid() = user_id);

-- Add my_players to the section defaults so new signups get it.
alter table public.profiles
  alter column section_visibility
  set default '{
    "headline": true,
    "scouting": true,
    "stretch": true,
    "pressbox": true,
    "farm": true,
    "slate": true,
    "division": true,
    "around_league": true,
    "history": true,
    "my_players": true
  }'::jsonb;

alter table public.profiles
  alter column section_order
  set default '[
    "headline","scouting","stretch","pressbox","farm",
    "slate","division","around_league","history","my_players"
  ]'::jsonb;
