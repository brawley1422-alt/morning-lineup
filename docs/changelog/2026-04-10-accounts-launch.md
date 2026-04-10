# 2026-04-10 — Accounts + Customizable Home launch

Today's session shipped the full accounts + personalization wedge, end
to end, plus a guest preview paywall. Everything below is live at
https://brawley1422-alt.github.io/morning-lineup/

## What shipped

### Phase A — Auth scaffolding
- Supabase project wired up (`config/supabase.js`, `auth/session.js`)
- Three tables with RLS: `profiles`, `followed_teams`, `scorecards`
- `handle_new_user` trigger auto-creates a profile row on signup
- Shared Supabase client with `storageKey: "ml-auth"` so every page
  reuses the same session
- Auth UI: `auth/index.html` (login / signup / forgot toggle),
  `auth/reset.html`, `auth/auth.css`, `auth/auth.js`, `auth/reset.js`
- Session smoke test page at `tests/session_smoke.html`

### Phase B — Merged `/home` view
- `/home` fetches each followed team's static page, extracts the
  nine `<section>` blocks via DOMParser, and re-mounts them in a
  per-team wrapper with the team's own colors
- Per-team CSS variable cascade drives the editorial look without
  re-implementing any section rendering
- Profile default theme set to `dark` (earlier `paper` default caused
  a white-background regression — fixed at both the SQL and JS layer)

### Phase C — `/settings` customization
- Section visibility toggles for all nine sections
- Drag-to-reorder sections (SortableJS via CDN)
- Followed-teams drag-to-reorder, add, remove
- Density: compact / full
- Theme: dark / paper
- Display name edit
- 500 ms debounced writes to `profiles`
- Cross-tab sync via `localStorage` ping + `visibilitychange` refetch
  so an open `/home` tab picks up changes instantly

### My Players tracker
- New `followed_players` table with RLS
- Search by name via MLB Stats API `/people/search`
- Add, remove, drag-reorder in settings
- New `my_players` section key added to defaults
- Existing profiles auto-backfill the new key on load
- `/home` renders a client-side "My Players" block that fetches
  season stats for every followed player in a single batched call
  to the MLB Stats API — hitters get slash line + HR/RBI, pitchers
  get W-L / ERA / K / IP
- Section position in the user's order is respected (top or bottom)

### Section menu (TOC) on `/home`
- Top-of-page section navigator that mirrors the user's order and
  visibility
- Anchor links to the first occurrence of each section type

### Team-page navigation
- Replaced the single home-button with two buttons: **Your Lineup**
  (→ `/home/`) and **All Teams** (→ landing)
- Positioned below the kicker row on both desktop and mobile
- `/home` footer swapped to "Browse all teams"

### Landing redirect
- Root `index.html` bounces guests to `/home` (checks `ml-auth`
  localStorage without loading the full Supabase client)
- Signed-in users stay on the team picker landing

### Service worker fix
- Old `sw.js` was cache-first for the shell, forcing a hard refresh
  after every deploy
- Rewrote to network-first with cache as an offline fallback
- Added `sw.js` to `deploy.py`'s STATIC_ASSETS so it actually ships
- Bumped cache name to `lineup-v2` to purge old caches

### Guest preview (logged-out paywall tease)
- `/home` for guests now renders a team dropdown (defaults to Cubs,
  persists in localStorage)
- Sections 1-3 (headline, scouting, stretch) render fully
- Sections 4-9 render behind a blur + gradient mask with a per-section
  "Claim your press pass" overlay
- "This is just a taste" top banner and "Want the whole paper?"
  bottom banner frame the experience

### Misc fixes shipped along the way
- Google OAuth button hidden until provider setup is complete
- Form `method="post" action="#"` as defense-in-depth so credentials
  can never leak into the URL if JS fails to bind
- `googleBtn` null-guard so removing the button didn't crash the
  submit handler (that bug briefly broke email login)

## New / modified files

- `auth/` — full new directory (session, login, signup, reset)
- `home/` — new directory (shell, merged-view renderer, guest preview)
- `settings/` — new directory (customization UI)
- `config/supabase.js` — client credentials
- `docs/supabase/schema.sql` — tables + triggers
- `docs/supabase/rls-policies.sql` — row-level security
- `docs/supabase/followed-players.sql` — players table migration
- `sw.js` — network-first rewrite
- `deploy.py` — STATIC_ASSETS extended to cover new dirs + sw.js
- `build.py` — two-button team-page nav
- `style.css` — `.nav-btns` / `.home-btn` / `.teams-btn` styling
- `landing.html` — guest redirect script
- `CLAUDE.md` — documented the `~/.secrets/morning-lineup.env`
  location for the deploy PAT

## Infra / config decisions worth remembering

- The deploy PAT is at `~/.secrets/morning-lineup.env` (chmod 600,
  outside the repo). Source it before running `deploy.py`.
- Supabase project ref: `xicuxuvuyalpngbhhkpl`
- Supabase pooler connection (IPv4): `aws-1-us-east-2.pooler.supabase.com:5432`
  (direct `db.{ref}.supabase.co` is IPv6-only from Yeezy)
- The publishable key (`sb_publishable_*`) is safe to commit — RLS
  is the real security boundary
- Google OAuth is *not* yet configured; provider is disabled in
  Supabase and the button is hidden on the auth page

## What's still pending

- **Phase D — Scorecard Book profile integration** (save completed
  scorecards to Supabase, profile page listing saved games, one-time
  localStorage→Supabase import on first login)
- **Phase E — Snapshot regression check** on team pages to make
  sure the static builds still match their golden fixtures after
  the nav button and CSS changes
- **Google OAuth setup** (dashboard work only — Google Cloud Console
  credentials + Supabase provider toggle)
- **Player stats upgrade** — add last-game line next to season line,
  maybe a small hot/cold trend indicator
