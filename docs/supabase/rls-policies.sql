-- Morning Lineup — Row Level Security policies
-- Run AFTER schema.sql. Idempotent.
--
-- Rule: a logged-in user can only read/write rows they own.
-- Anon key + RLS is the entire security model — no rows are reachable without auth.

-- ---------- enable RLS ----------
alter table public.profiles        enable row level security;
alter table public.followed_teams  enable row level security;
alter table public.scorecards      enable row level security;

-- ---------- profiles ----------
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
  on public.profiles for select
  using (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own"
  on public.profiles for insert
  with check (auth.uid() = id);

drop policy if exists "profiles_delete_own" on public.profiles;
create policy "profiles_delete_own"
  on public.profiles for delete
  using (auth.uid() = id);

-- ---------- followed_teams ----------
drop policy if exists "followed_teams_select_own" on public.followed_teams;
create policy "followed_teams_select_own"
  on public.followed_teams for select
  using (auth.uid() = user_id);

drop policy if exists "followed_teams_insert_own" on public.followed_teams;
create policy "followed_teams_insert_own"
  on public.followed_teams for insert
  with check (auth.uid() = user_id);

drop policy if exists "followed_teams_update_own" on public.followed_teams;
create policy "followed_teams_update_own"
  on public.followed_teams for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "followed_teams_delete_own" on public.followed_teams;
create policy "followed_teams_delete_own"
  on public.followed_teams for delete
  using (auth.uid() = user_id);

-- ---------- scorecards ----------
drop policy if exists "scorecards_select_own" on public.scorecards;
create policy "scorecards_select_own"
  on public.scorecards for select
  using (auth.uid() = user_id);

drop policy if exists "scorecards_insert_own" on public.scorecards;
create policy "scorecards_insert_own"
  on public.scorecards for insert
  with check (auth.uid() = user_id);

drop policy if exists "scorecards_update_own" on public.scorecards;
create policy "scorecards_update_own"
  on public.scorecards for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "scorecards_delete_own" on public.scorecards;
create policy "scorecards_delete_own"
  on public.scorecards for delete
  using (auth.uid() = user_id);
