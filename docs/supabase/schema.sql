-- Morning Lineup — Supabase schema
-- Run in Supabase SQL editor. Idempotent: safe to re-run.
--
-- Tables:
--   profiles         — 1:1 with auth.users, stores customization state
--   followed_teams   — many-to-many, ordered list of teams a user follows
--   scorecards       — saved Scorecard Book games per user

-- ---------- profiles ----------
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  section_visibility jsonb not null default '{
    "headline": true,
    "scouting": true,
    "stretch": true,
    "pressbox": true,
    "farm": true,
    "slate": true,
    "division": true,
    "around_league": true,
    "history": true
  }'::jsonb,
  section_order jsonb not null default '[
    "headline","scouting","stretch","pressbox","farm","slate","division","around_league","history"
  ]'::jsonb,
  density text not null default 'full' check (density in ('compact','full')),
  theme text not null default 'dark' check (theme in ('paper','dark')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Auto-update updated_at on any row change.
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Auto-create a profile row whenever a new auth.users row is inserted.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1)));
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------- followed_teams ----------
create table if not exists public.followed_teams (
  user_id uuid not null references public.profiles(id) on delete cascade,
  team_slug text not null,
  position int not null default 0,
  created_at timestamptz not null default now(),
  primary key (user_id, team_slug)
);

create index if not exists followed_teams_user_position_idx
  on public.followed_teams (user_id, position);

-- ---------- scorecards ----------
create table if not exists public.scorecards (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  game_pk bigint not null,
  game_date date not null,
  teams jsonb not null,
  scorecard_data jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, game_pk)
);

create index if not exists scorecards_user_date_idx
  on public.scorecards (user_id, game_date desc);

drop trigger if exists scorecards_set_updated_at on public.scorecards;
create trigger scorecards_set_updated_at
  before update on public.scorecards
  for each row execute function public.set_updated_at();
