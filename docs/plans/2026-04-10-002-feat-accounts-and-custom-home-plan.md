---
title: "feat: Accounts & Customizable Home Page"
type: feat
status: active
date: 2026-04-10
origin: docs/brainstorms/accounts-and-custom-home-requirements.md
---

# feat: Accounts & Customizable Home Page

## Overview

Add Supabase-backed accounts and a personalized `/home` route to Morning Lineup. Logged-in users can follow 1+ MLB teams, customize which sections appear on their home page, reorder them via drag, choose display density and theme, and save their Scorecard Book games to their profile. The existing 30 static per-team pages are untouched — `/home` is a new client-side rendered route that reads the existing daily data ledger and merges per-team data at page load. Infra stays at $0 (GitHub Pages + Supabase free tier).

## Problem Frame

Brainstorm findings (see origin: `docs/brainstorms/accounts-and-custom-home-requirements.md`) concluded that Morning Lineup's Tier 2 business case is "the morning paper baseball deserves" — an editorial daily ritual for die-hard fans. Customization (multi-team following + personalized sections) is the actual product differentiator, not email delivery. Accounts-first sets up later email, scorecards, and monetization to work better than email-first would have. This plan implements the brainstorm's R1-R16 requirements at Full scope (teams + sections + order + density + theme + scorecard profile integration).

## Requirements Trace

Traceable to brainstorm requirements in `docs/brainstorms/accounts-and-custom-home-requirements.md`:

- **R1** — Email/password + Google OAuth via Supabase Auth
- **R2** — Login/logout/password reset, persistent session
- **R3** — `profiles` table in Supabase with followed teams, section visibility, order, density, theme
- **R4** — `/home` client-rendered route, no changes to 30 static pages
- **R5** — Multi-team merged briefing when user follows 2+ teams
- **R6** — Per-section visibility toggle (9 sections)
- **R7** — Drag-to-reorder sections, order persists
- **R8** — Display density: compact vs. full
- **R9** — Theme toggle: paper vs. dark
- **R10** — Logged-out `/home` shows signup prompt + preview, not a redirect
- **R11** — Scorecard Book persists to profile when logged in; localStorage fallback otherwise
- **R12** — Profile page lists saved scorecards
- **R13** — Settings page edits all preferences
- **R14** — Account deletion (row + scorecard cleanup)
- **R15** — All new UI matches editorial newspaper aesthetic (Playfair Display, Oswald, Lora, IBM Plex Mono, existing CSS variable system)
- **R16** — Zero regressions to existing 30 static team pages (golden snapshot tests must still pass)

Success criteria carried forward: SC1 (60-sec signup-to-home), SC2 (cross-device persistence), SC3 (<2s render), SC4 (zero regressions), SC5 (scorecard persistence), SC6 (100 accounts in 30 days), SC7 (>40% multi-team adoption), SC8 (3-of-7-day return rate).

## Delivery Phases

The 9 implementation units group into 5 phases. Each phase ends at a natural stopping point where the product is shippable and a decision can be made about whether to continue. You can stop between phases without leaving the product in a broken or half-useful state.

| Phase | Units | Theme | Shippable increment | Est. time |
|-------|-------|-------|---------------------|-----------|
| **A — Foundation** | 1, 2, 3 | Supabase + auth + session | Users can sign up, log in, log out. No home page yet — landing still the front door. | ~5 hrs |
| **B — Home Page** | 4, 5 | `/home` scaffold + multi-team merge | Logged-in users see their personalized merged briefing. Core product comes alive. | ~8 hrs |
| **C — Customization** | 6 | Visibility + drag-reorder + density + theme + settings page | Users can shape their own morning paper. The wedge is fully expressed. | ~6 hrs |
| **D — Scorecards** | 7 | Scorecard Book profile integration | Scorecards persist across devices. Premium feature anchor is in place for later. | ~5 hrs |
| **E — Polish** | 8, 9 | Logged-out preview + landing signup + regression check | Public-facing entry points + snapshot tests green. Ready for distribution push. | ~3 hrs |

**How to use phases:**
- Ship at the end of each phase, even if the next phase isn't started. Every phase leaves the product in a better state than the previous one.
- When sitting down to work, load only the current phase's units into the session context — don't load the whole plan. Keeps Claude sessions focused and cheap.
- Trim decision points: if Phase C runs long, R7 (drag-to-reorder) and R9 (theme toggle) are the designated trim candidates (see Key Technical Decisions). Phase C can ship with just visibility + density + settings page if needed.
- If distribution work should start before Phase D/E, that's fine — Phase A + B + C is already a complete Tier 2 product. Scorecards and polish can land post-launch.

## Scope Boundaries

**In scope:** everything under Requirements Trace above.

**Out of scope (deferred, not cancelled — per origin doc):**
- Email delivery / daily newsletter
- Push notifications
- Social features (comments, follows, public profiles)
- Paid tier / premium features
- Sponsor slots
- Prediction games / pick'em
- User-contributed content (custom history entries, game notes)
- Analytics dashboard for JB (separable, Plausible/Umami later)
- Native mobile apps
- SEO for `/home`
- Multi-sport expansion

**Non-goals (deliberate):**
- Not rewriting `build.py` or the sectioned architecture
- Not adding a backend server — Supabase client only
- Not monetizing in v1

## Context & Research

### Relevant Code and Patterns

- `build.py` — orchestrator; emits per-team static HTML into `{slug}/index.html`. **Do not modify for this plan** except to add one new line that writes `/home/index.html` shell and possibly copies `data/{today}.json` to a known public path
- `sections/*.py` — 9 section renderers, each exports `render(briefing)` and returns HTML. These are the source of truth for section layout; `/home` will re-fetch the already-rendered section HTML from the static team pages (Option B below) rather than reimplement rendering in JS
- `data/{YYYY-MM-DD}.json` — **key discovery**: a single shared daily ledger containing all 30 teams' data under `tmap`. Verified via repo scan on 2026-04-10. This is the render source for `/home`. File is ~2MB — acceptable for client-side fetch on desktop, consider a slimmer `/home`-specific ledger during Unit 4 if mobile perf suffers
- `{slug}/index.html` — per-team static pages; each section is wrapped in `<section id="{name}">` per the envelope in `build.py`. The section IDs match the filenames in `sections/` (headline, scouting, stretch, pressbox, farm, slate, division, around_league, history)
- `live.js` — vanilla-JS IIFE pattern used for polling; `/home` should follow the same "no-framework, no-build-step" convention
- `style.css` — inlined by `build.py`; defines the CSS variable system and editorial typography. New `/home` and auth UI must reuse these variables, not introduce new ones
- `scorecard/app.js` — scorecard controller; currently uses no persistence layer beyond in-memory state (repo scan found no `localStorage` references). Unit 7 will verify and add Supabase persistence + localStorage fallback
- `teams/{slug}.json` — team config source; `/home` will use this for display names, colors, and slug resolution
- `tests/snapshot_test.py` — golden snapshot harness. Must continue to pass byte-identical diffs against Cubs + Yankees fixtures after this plan lands (protects R16)
- `docs/plans/2026-04-08-004-feat-multi-team-support-plan.md` — prior plan that established the multi-team model. Reference for team slug conventions and per-team output structure

### Institutional Learnings

- The project follows a **"static first, no build step"** convention (Python stdlib + vanilla JS, no npm). The Supabase JS client is distributed as a single ES module from their CDN (`https://esm.sh/@supabase/supabase-js@2`) — this aligns with the existing pattern and does not require introducing a bundler or package manager
- The sectioned architecture (post-2026-04-10 refactor per `docs/plans/2026-04-10-001-refactor-sectioned-build-plan.md`) means sections render in isolation and can be extracted from the existing static HTML by DOM query on `<section id>`. This is what makes the client-side merge approach viable
- `build.py` runs as `__main__` — nothing in `sections/` may import from it at module top level. Irrelevant to this plan since we aren't editing sections, but worth knowing if Unit 4 ever needs to call section helpers

### External References

- Supabase Auth JS quickstart (static site pattern): `https://supabase.com/docs/guides/auth/quickstarts/vanilla-javascript`
- Supabase Row Level Security for profiles tables: `https://supabase.com/docs/guides/database/postgres/row-level-security`
- SortableJS via CDN for drag-to-reorder (single-file, no build): `https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js`

## Key Technical Decisions

- **Supabase for auth + profile + scorecards** — free tier covers projected v1 volume (under 50k users), single-vendor reduces complexity. Rationale grounded in origin doc D6 (architecture decision). No server maintenance, preserves $0 infra
- **Client-side rendering for `/home` only** — the 30 static per-team pages stay as-is (protects R16, golden snapshot tests, SEO). `/home` is a new route with its own HTML shell and a vanilla-JS app that fetches the daily ledger + user profile and renders the merged view in the browser
- **Single shared daily ledger** — `data/{YYYY-MM-DD}.json` already contains all 30 teams. `/home` fetches this one file (cache-busted by date) instead of N per-team files. Reduces request count from N to 1
- **Section source-of-truth strategy: Option B (HTML extraction)** — `/home` fetches each followed team's existing `{slug}/index.html`, parses it with `DOMParser`, extracts `<section id="{name}">` blocks, and re-assembles them into a merged shell. This reuses 100% of existing section rendering logic without reimplementing it in JS. Alternative considered: Option A (emit per-team JSON + render in JS) — rejected because it would require mirroring 9 section renderers in JavaScript, a ~2-3 week extra lift. Option B is pragmatic and low-risk; if performance becomes an issue with 3+ followed teams, revisit in a post-v1 iteration
- **Vanilla JS + Supabase ES module, no bundler** — aligns with the project's "no build step" convention. Supabase client via `esm.sh`, SortableJS via CDN, no npm, no webpack
- **CSS reuse, not rewrite** — all auth, home, settings, and profile UI reuse `style.css` variables and typography. No new design system. Protects R15
- **Row Level Security (RLS) mandatory on all user-scoped tables** — `profiles`, `scorecards`, `followed_teams`. Users can only read/write their own rows. Supabase RLS policies enforce this server-side
- **Google OAuth is a nice-to-have, not a blocker** — if OAuth setup slows the plan, email/password ships first and Google lands in a fast-follow. R1 accepts this (email/password + "optionally Google OAuth")
- **Drag-to-reorder (R7) and theme toggle (R9) are the designated trim candidates** — origin doc Q8 explicitly flagged these as the most easily deferred if timeline slips. Planning treats them as in-scope for v1 but flags them as the first to cut

## Open Questions

### Resolved During Planning

- **Where does the daily data live for `/home`?** — `data/{today}.json`, the existing shared ledger. Confirmed via repo scan
- **How does `/home` get section HTML without reimplementing renderers?** — DOMParser extraction from existing static pages (Option B)
- **Does the project use npm / a bundler?** — No. Plan follows existing static + CDN pattern
- **Does the scorecard currently persist state?** — Repo scan found no `localStorage` references in `scorecard/*.js`. Unit 7 will verify and add persistence fresh rather than migrating existing data
- **Plan numbering for today?** — `2026-04-10-001` is already taken by the sectioned-build refactor. This plan is `2026-04-10-002`

### Deferred to Implementation

- **Exact Supabase schema field types** — resolved during Unit 1 when writing the migration SQL against real Supabase SQL editor
- **Multi-team merge layout specifics** — grouped by team vs. interleaved by section (origin Q5). Unit 5 will prototype one approach (grouped-by-team, primary team first) and iterate based on how it actually looks with 2-3 real teams
- **Exact `/home` URL path** — `/morning-lineup/home/index.html` is the GitHub Pages natural path. Unit 4 will confirm routing works without a custom domain
- **Supabase project region** — origin Q2. Default `us-east-1` during Unit 1; change only if latency measurably hurts
- **Email provider for Supabase auth emails** — origin Q1. Supabase default is fine for v1; Resend integration is a post-launch optimization
- **Scorecard schema shape** — Unit 7 will define the table after reading `scorecard/parser.js` and `scorecard/scorebook.js` to understand the in-memory data model
- **Ledger size on mobile** — the 2MB `data/{today}.json` may be too heavy for mobile cold-loads. Unit 4 will measure real payload, and if needed, `build.py` can emit a slimmer `data/{today}-home.json` as a follow-up (not a v1 blocker)

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
                          Browser (/home)
  ┌────────────────────────────────────────────────────────────┐
  │  home.js (vanilla JS, ES module)                           │
  │                                                            │
  │   1. supabase.auth.getSession()                            │
  │          │                                                 │
  │          ├─ no session ──▶ render logged-out preview       │
  │          │                                                 │
  │          └─ session ──▶ fetch profile from `profiles`      │
  │                             │                              │
  │                             ▼                              │
  │              fetch data/{today}.json (once)                │
  │                             │                              │
  │                             ▼                              │
  │        for each followed_team in profile:                  │
  │            fetch {slug}/index.html                         │
  │            DOMParser → extract <section id="...">          │
  │                             │                              │
  │                             ▼                              │
  │        apply profile.section_visibility + order            │
  │                             │                              │
  │                             ▼                              │
  │        apply density + theme via CSS class on <body>       │
  │                             │                              │
  │                             ▼                              │
  │        render merged page into #home-shell                 │
  └────────────────────────────────────────────────────────────┘
```

Supabase schema (directional):

```
profiles (1:1 with auth.users)
  ├─ id (uuid, fk auth.users)
  ├─ display_name (text)
  ├─ section_visibility (jsonb)   — {"headline": true, "farm": false, ...}
  ├─ section_order (jsonb)         — ["headline", "stretch", ...]
  ├─ density ("compact" | "full")
  ├─ theme ("paper" | "dark")
  └─ created_at, updated_at

followed_teams (many-to-many)
  ├─ user_id (uuid, fk profiles)
  ├─ team_slug (text)              — matches teams/{slug}.json
  ├─ position (int)                — primary=0, secondary=1, ...
  └─ created_at

scorecards
  ├─ id (uuid)
  ├─ user_id (uuid, fk profiles)
  ├─ game_pk (int)                 — MLB Stats API game ID
  ├─ game_date (date)
  ├─ teams (jsonb)                 — {"home": "cubs", "away": "pirates"}
  ├─ scorecard_data (jsonb)        — full scorebook state
  └─ created_at, updated_at

RLS: all three tables — users can read/write only their own rows.
```

## Implementation Units

### Phase A — Foundation

*Units 1-3. Shippable as: users can sign up and log in. Landing page is still the front door. ~5 hrs.*

- [x] **Unit 1: Supabase project setup + schema + RLS**

**Goal:** Create the Supabase project, define the three tables (`profiles`, `followed_teams`, `scorecards`), enable RLS, and store the project URL + anon key in a committed config file.

**Requirements:** R1, R3, R11, R14

**Dependencies:** None

**Files:**
- Create: `config/supabase.js` (exports `SUPABASE_URL` and `SUPABASE_ANON_KEY` constants — anon key is safe to commit, RLS enforces security)
- Create: `docs/supabase/schema.sql` (the migration SQL — committed for reference and reproducibility)
- Create: `docs/supabase/rls-policies.sql` (row-level security policies)
- Test: none — this is external infra setup

**Approach:**
- Create a new Supabase project in `us-east-1` (default)
- Run schema.sql in the Supabase SQL editor
- Run rls-policies.sql to enable RLS on all three tables with "users can only touch their own rows" policies
- Enable email/password auth in Supabase dashboard
- (Optional) configure Google OAuth provider — if setup is slow, defer to a post-v1 fast-follow

**Patterns to follow:**
- Supabase RLS quickstart for JS static sites

**Test scenarios:**
- Test expectation: none — pure infra setup, verified manually via the Supabase dashboard. Subsequent units exercise the schema through application code

**Verification:**
- Supabase dashboard shows three tables with RLS enabled
- A manually-inserted test user can read their own profile row and gets denied reading another user's row
- `config/supabase.js` exports the URL and key, importable from a browser via ES module

---

- [x] **Unit 2: Auth UI — signup, login, password reset**

**Goal:** Ship signup, login, and password reset pages that match the editorial aesthetic. Wires the Supabase JS client and handles the full auth lifecycle for email/password users.

**Requirements:** R1, R2, R15

**Dependencies:** Unit 1

**Files:**
- Create: `auth/index.html` (login page with signup toggle and "forgot password" link)
- Create: `auth/reset.html` (password reset flow landing page — Supabase sends a link here)
- Create: `auth/auth.js` (ES module — Supabase client init, signup/login/logout/reset handlers)
- Create: `auth/auth.css` (scoped styles that extend `style.css` variables — no new design system)
- Modify: `build.py` (one-time: add `auth/` to the deploy manifest so `deploy.py` uploads it)

**Approach:**
- Single-page auth with JS-driven toggle between "log in" and "sign up" modes
- Reuse `style.css` CSS variables for colors, typography, spacing
- Use Supabase JS client via `https://esm.sh/@supabase/supabase-js@2`
- After successful login, redirect to `/home`
- Password reset: Supabase sends an email with a link to `auth/reset.html?token=...`, the page exchanges the token for a session and prompts for a new password
- Google OAuth button is present but optional — can be wired in the same unit or deferred

**Patterns to follow:**
- `scorecard/app.js` — vanilla JS module pattern
- `style.css` — typography and variable conventions

**Test scenarios:**
- Happy path: user submits email/password → account created → redirected to `/home`
- Happy path: existing user submits credentials → session established → redirected
- Edge case: submit with empty email → form blocks submission, inline error
- Edge case: submit with invalid email format → Supabase returns error, UI displays it
- Error path: signup with already-registered email → error message displayed, not a crash
- Error path: login with wrong password → error message displayed, no session created
- Error path: password reset for non-existent email → UI shows "if an account exists, we sent a link" (no user enumeration)
- Integration: after signup, a row appears in `profiles` with sensible defaults (empty followed teams, all sections visible, default density, default theme)

**Verification:**
- A fresh browser can complete the signup flow end-to-end without console errors
- Session persists across page reloads (Supabase stores in localStorage by default)
- Logout clears the session and redirects to landing

---

- [x] **Unit 3: Shared auth helper + session wiring**

**Goal:** Provide a small JS module that any page can import to get the current user, subscribe to auth state changes, and perform Supabase queries with a shared client instance.

**Requirements:** R2, R3

**Dependencies:** Unit 1, Unit 2

**Files:**
- Create: `auth/session.js` (exports `getSession`, `getProfile`, `requireAuth`, `onAuthChange`, and a `supabase` client instance)
- Test: `tests/session_smoke.html` (manual smoke page that imports `session.js` and displays current session state — useful for debugging, not shipped)

**Approach:**
- Single Supabase client instance exported from `session.js` so every page shares the same connection
- `getProfile()` fetches the current user's row from `profiles` and caches it in-memory for the page lifetime
- `requireAuth()` returns `{session, profile}` or redirects to `/auth` if no session
- `onAuthChange(callback)` subscribes to Supabase auth state changes so pages can react to logout from another tab

**Patterns to follow:**
- ES module pattern (same as `scorecard/*.js` style)

**Test scenarios:**
- Happy path: logged-in user calls `getProfile()` → returns their profile row
- Edge case: logged-in user has no `profiles` row yet → `getProfile()` creates a default row and returns it (protects against incomplete signup)
- Error path: logged-out user calls `requireAuth()` → redirect to `/auth`
- Integration: logout in one tab triggers `onAuthChange` in another tab with a null session

**Verification:**
- `session.js` can be imported from any page in the repo and works without errors
- Auth state stays consistent across tabs

---

### Phase B — Home Page

*Units 4-5. Shippable as: logged-in users see their personalized merged briefing. Core product comes alive. ~8 hrs.*

- [x] **Unit 4: `/home` route scaffold + data loader**

**Goal:** Create the `/home` route with a minimal page shell, load the current user's profile, fetch the daily data ledger, and render a placeholder list of followed teams. Proves the routing, data pipeline, and auth wiring before adding the merge logic.

**Requirements:** R4, R10

**Dependencies:** Unit 3

**Files:**
- Create: `home/index.html` (page shell — masthead, nav, `<main id="home-shell">`, footer)
- Create: `home/home.js` (ES module — loads session, profile, ledger; renders placeholder)
- Create: `home/home.css` (scoped styles extending `style.css`)
- Modify: `build.py` (add `home/` to deploy manifest; optional: copy `data/{today}.json` to a stable path like `data/latest.json` so `/home` doesn't need to know today's date client-side)

**Approach:**
- Page shell is a static HTML file — no server rendering
- On load, `home.js` calls `requireAuth()`; if logged out, it renders the signup preview (R10) instead of redirecting
- If logged in, fetch the user's profile and `data/latest.json` in parallel
- For v1 placeholder, just list the followed team names and a "coming soon" message for the merged sections
- Handles the empty state: logged-in user with zero followed teams → prompt them to pick a team (links to `/settings`)

**Patterns to follow:**
- `live.js` — vanilla-JS module pattern, no framework
- `{slug}/index.html` — page envelope structure (masthead, section, footer)

**Test scenarios:**
- Happy path: logged-in user with 1 followed team → page loads, shows team name + placeholder
- Happy path: logged-in user with 3 followed teams → page loads, shows all 3 team names
- Edge case: logged-in user with 0 followed teams → page shows "pick your teams" prompt linking to settings
- Edge case: logged-out user → page shows signup preview, not a redirect
- Error path: `data/latest.json` 404 → graceful fallback message, no crash
- Error path: profile fetch fails → error displayed, user can retry
- Integration: page load triggers exactly one fetch for the ledger (not N)

**Verification:**
- Navigating to `/home` after login shows the placeholder
- Navigating to `/home` logged out shows the signup preview
- Browser dev tools show one ledger fetch, one profile fetch, no redundant requests

---

- [x] **Unit 5: Section extraction + multi-team merge renderer**

**Goal:** Implement the core `/home` behavior: fetch each followed team's static `{slug}/index.html`, extract section blocks via DOMParser, and render a merged view that respects the user's section visibility and order preferences.

**Requirements:** R4, R5, R6, R7 (partial — rendering only, drag lands in Unit 6)

**Dependencies:** Unit 4

**Files:**
- Modify: `home/home.js` (add section extraction + merge + render logic)
- Modify: `home/home.css` (add merged-view styling)
- Test: `tests/home_merge_test.html` (manual smoke page that loads a known fixture set of 2 teams and verifies the merged output)

**Approach:**
- For each followed team (in `position` order), fetch `{slug}/index.html`
- Parse with `DOMParser` and query for `<section id="{name}">` blocks
- For each section name in the user's `section_order`, if `section_visibility[name]` is true, concatenate the corresponding blocks from each team
- Merge strategy for v1: **grouped by team**. Primary team's full set of sections first, then secondary team's, then tertiary. Each team block gets its own team-branded header strip
- Team color CSS variables are applied per-team-block so each team's sections render in that team's colors
- Cache extracted sections in a `Map` keyed by team slug for the page lifetime (don't re-fetch on re-render)

**Patterns to follow:**
- `live.js` — DOM manipulation style, no framework
- `build.py` page envelope — structural reference for how sections nest

**Test scenarios:**
- Happy path: user follows Cubs + Yankees → merged view shows Cubs sections (in Cubs colors) then Yankees sections (in Yankees colors)
- Happy path: user hides "farm" section in profile → merged view omits farm for all teams
- Happy path: user reorders sections (headline, stretch, history, rest) → merged view renders in that order for each team block
- Edge case: user follows only 1 team → merged view renders identically to the static team page for visible sections
- Edge case: followed team's static page 404s (shouldn't happen but defensive) → error block shown for that team, other teams still render
- Edge case: section exists in one team's HTML but not another (e.g., scouting report on off-day) → missing section is silently skipped for that team
- Error path: DOMParser fails on malformed HTML → error logged, team skipped, user sees a message
- Integration: rendering with all 9 sections visible across 3 teams completes in <2s on desktop (SC3)

**Verification:**
- Visual check: merged view with 2 followed teams looks cohesive and uses each team's colors
- All visible sections from both teams are present
- Hiding a section in profile and reloading removes it from the merged view
- Performance: initial render <2s with 3 teams, 9 sections each

---

### Phase C — Customization

*Unit 6. Shippable as: users can shape their own morning paper. The wedge is fully expressed. ~6 hrs. Trim candidates if timeline slips: R7 drag-to-reorder and R9 theme toggle.*

- [x] **Unit 6: Customization controls — visibility toggles, drag-to-reorder, density, theme**

**Goal:** Add the customization UI that lets users toggle section visibility, drag to reorder, choose density, and toggle theme. All changes persist to the `profiles` table.

**Requirements:** R6, R7, R8, R9, R13

**Dependencies:** Unit 5

**Files:**
- Create: `settings/index.html` (settings page shell)
- Create: `settings/settings.js` (customization controls, profile update handlers)
- Create: `settings/settings.css`
- Modify: `home/home.js` (read density + theme from profile, apply via body class; re-render when profile updates)
- Modify: `build.py` (deploy `settings/`)

**Approach:**
- Settings page lists the 9 sections with checkboxes for visibility and drag handles for order
- SortableJS via CDN (`https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js`) handles drag — no custom drag code
- Density is a radio pair: compact / full
- Theme is a radio pair: paper / dark
- On any change, debounce 500ms then write to Supabase
- `/home` subscribes to a `storage` event or re-fetches profile on focus to pick up changes made in another tab

**Patterns to follow:**
- `style.css` — CSS variable system for density and theme
- Existing scorecard dark/paper toggle if present in `scorecard/styles.css`

**Test scenarios:**
- Happy path: user unchecks "farm" → debounced save → profile row updates → `/home` hides farm on next render
- Happy path: user drags "history" to the top → save → `/home` renders history first
- Happy path: user switches density to compact → body class applied → type scales down via CSS variables
- Happy path: user switches theme to dark → body class applied → CSS variables swap
- Edge case: user toggles the same section 5 times quickly → only one save fires after debounce
- Error path: Supabase write fails (network) → inline error on the settings page, local state reverts
- Integration: change in settings tab reflects in an open `/home` tab within a few seconds

**Verification:**
- All four customization dimensions (visibility, order, density, theme) persist across page reloads
- Cross-device: change on desktop visible on mobile after login
- No regressions to `/home` initial render performance

---

### Phase D — Scorecards

*Unit 7. Shippable as: scorecards persist across devices. Premium feature anchor in place for later monetization. ~5 hrs. Can land post-launch if distribution work starts earlier.*

- [ ] **Unit 7: Scorecard Book profile integration**

**Goal:** Add Supabase persistence to the Scorecard Book so logged-in users save completed scorecards to their profile, and a profile page lists them.

**Requirements:** R11, R12

**Dependencies:** Unit 3

**Files:**
- Modify: `scorecard/app.js` (add save-to-Supabase hook on game complete; load from Supabase on open)
- Create: `profile/index.html` (profile page — display name, saved scorecards list, delete account button)
- Create: `profile/profile.js`
- Create: `profile/profile.css`
- Modify: `build.py` (deploy `profile/`; update scorecard deploy to include session.js import)

**Approach:**
- Scorecard currently has no persistence (repo scan found no localStorage references). Add both localStorage (for logged-out users) and Supabase (for logged-in users)
- When the user logs in with existing localStorage scorecards, offer a one-time "import to your profile" prompt
- Profile page fetches `scorecards` rows for current user, sorts by `game_date` desc, renders a list with "reopen" links
- Delete account button calls Supabase user delete; RLS cascade handles profile + scorecards cleanup

**Patterns to follow:**
- Scorecard in-memory data model in `scorecard/parser.js` and `scorecard/scorebook.js` — must be inspected during implementation to define the `scorecards.scorecard_data` JSONB shape

**Test scenarios:**
- Happy path: logged-in user completes a game → scorecard saved to Supabase → appears in profile list
- Happy path: logged-out user completes a game → saved to localStorage → still accessible in the scorecard finder
- Happy path: user logs in with localStorage scorecards → prompted to import → rows appear in Supabase
- Happy path: user clicks "reopen" in profile → scorecard loads with saved state
- Edge case: user reopens a scorecard, edits it, saves → existing row updated (not duplicated)
- Edge case: same game scored twice (rare — maybe re-watching) → second save creates a new row, not an overwrite
- Error path: Supabase save fails mid-game → falls back to localStorage, surfaces an inline warning
- Error path: delete account → confirms → all rows gone, session cleared, redirect to landing
- Integration: scorecard saved on desktop is visible on mobile after login

**Verification:**
- Completing a game while logged in results in a row in `scorecards`
- Profile page lists saved games in reverse chronological order
- Account deletion removes all user data

---

### Phase E — Polish

*Units 8-9. Shippable as: public-facing entry points + snapshot tests green. Ready for distribution push. ~3 hrs.*

- [ ] **Unit 8: Logged-out `/home` preview + landing page signup prompt**

**Goal:** Implement the R10 behavior where logged-out visitors to `/home` see a signup prompt plus a preview (not a redirect), and add a signup/login entry point to the existing landing page.

**Requirements:** R10, R15

**Dependencies:** Unit 4

**Files:**
- Modify: `home/home.js` (add logged-out preview render path)
- Modify: `home/home.css` (preview styles)
- Modify: `landing.html` (add "Sign in" / "Sign up" buttons to the masthead)

**Approach:**
- Logged-out `/home` shows a marketing block explaining what accounts unlock, with a "try it with the Cubs" teaser that renders a preview merged view using a hardcoded default (e.g., Cubs only, all sections visible)
- CTA buttons route to `/auth`
- Landing page gains small, unobtrusive sign in/up links in the masthead — no visual overhaul

**Patterns to follow:**
- `landing.html` — existing masthead and typography
- Editorial tone from existing team pages

**Test scenarios:**
- Happy path: logged-out visitor opens `/home` → sees marketing block + Cubs preview
- Happy path: clicks "sign up" → lands on `/auth` in signup mode
- Happy path: landing page shows sign in/up buttons in masthead
- Edge case: logged-in visitor opens `/home` directly → never sees the preview, goes to personalized view
- Integration: landing page masthead looks identical to existing design except for the two new links

**Verification:**
- Logged-out `/home` has zero Supabase write calls (read-only preview)
- Landing page visually unchanged except for the new links

---

- [ ] **Unit 9: Zero-regression check + snapshot test re-bless (if needed)**

**Goal:** Verify that nothing in the existing 30 static team pages or the landing page has regressed. Re-bless snapshot tests only if a pure-additive change (new links in landing masthead) caused an intentional diff.

**Requirements:** R16

**Dependencies:** Units 2, 4, 6, 7, 8 (anything that touched `build.py` or shared assets)

**Files:**
- Run: `tests/snapshot_test.py` (read-only test, no file changes unless re-blessing)
- Possibly update: `tests/fixtures/expected_cubs.html`, `tests/fixtures/expected_yankees.html` (only if the landing masthead change intentionally broke them — and only if landing.html is part of the snapshot set, which it may not be)

**Approach:**
- Run the golden snapshot tests after all prior units are landed
- If Cubs + Yankees pages are byte-identical to expected, no action needed
- If the landing masthead change (Unit 8) causes a diff *and* landing.html is covered by snapshots, re-bless per `tests/README.md`
- Any unexpected diff in Cubs or Yankees pages is a regression bug — fix the source, don't re-bless

**Patterns to follow:**
- `tests/README.md` — snapshot re-bless procedure

**Test scenarios:**
- Test expectation: none (this unit runs existing tests rather than authoring new ones). The verification is that snapshots pass or that any diff is clearly intentional and re-blessed

**Verification:**
- `python3 tests/snapshot_test.py` passes
- Manual spot-check: open `cubs/index.html`, `yankees/index.html`, and `landing.html` in a browser — visually unchanged (except for the two new sign-in/up links on landing)

## System-Wide Impact

- **Interaction graph:** New `/home`, `/auth`, `/settings`, `/profile` routes are additive — no existing route is modified except `landing.html` (two new links) and `scorecard/app.js` (persistence hook added, no behavior change for existing users)
- **Error propagation:** Supabase failures must degrade gracefully. Scorecard must always work offline via localStorage. `/home` must render something useful even if the ledger fetch fails
- **State lifecycle risks:** Logging out in one tab should invalidate the session in other tabs — `onAuthChange` (Unit 3) handles this. Supabase token refresh happens automatically
- **API surface parity:** None — the 30 static team pages have no API. Only the new Supabase-backed surfaces need RLS enforcement
- **Integration coverage:** Multi-tab auth state, scorecard save under flaky network, section extraction with partial HTML, mobile performance on the 2MB ledger
- **Unchanged invariants:** All 30 per-team static pages continue to render byte-identically (R16 + Unit 9). `build.py` section architecture is untouched. `sections/*.py` files are not modified. Scorecard core behavior is unchanged for logged-out users (existing flow preserved)

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Supabase free tier limits (50k MAU, 500MB DB) exceeded during growth | Monitor during distribution push; upgrade to Pro ($25/mo) is a non-blocker decision made against actual usage, not projected |
| 2MB daily data ledger too heavy for mobile cold-load | Unit 4 measures real payload; if needed, `build.py` emits a trimmed `data/{today}-home.json` with only home-page-relevant fields. Not a v1 blocker |
| DOMParser extraction fragile if section HTML structure changes | Mitigated by `tests/snapshot_test.py` catching unintended section-structure changes. If sections change, `/home` needs updating — flag this in `docs/plans/2026-04-10-001-refactor-sectioned-build-plan.md` as a downstream consumer |
| Drag-to-reorder library (SortableJS CDN) unavailable or version-pinned issues | SortableJS is stable and widely mirrored; pin version in URL. If CDN outage, drag-to-reorder degrades to up/down buttons — acceptable v1 fallback |
| Google OAuth setup slows the plan | R1 accepts email/password alone for v1; Google is a fast-follow. No blocker |
| Multi-team merge UX is ugly with 3+ teams | Unit 5 prototypes grouped-by-team first; iterate based on how it actually looks. Interleaved-by-section is a fallback option |
| Scorecard data model is more complex than anticipated and JSONB persistence is lossy | Unit 7 reads `scorecard/parser.js` and `scorecard/scorebook.js` before defining the schema. If the model has circular refs or non-serializable state, add a serialize/deserialize layer |
| Golden snapshot tests break on intentional landing-masthead change | Unit 9 explicitly handles this with a re-bless path if landing.html is in the snapshot set |
| JB trims scope mid-build (drag-reorder + theme flagged as trim candidates) | Plan is structured so Units 6 (drag + density + theme) is the most droppable. Even without Unit 6, the product works — users have default section order and density, no theme toggle |
| Scope is ambitious for a side-project timeline | Origin doc Q8 already flagged this. Trim order: R7 (drag) first, R9 (theme) second. Everything else is load-bearing for the "customization is the wedge" thesis |

## Documentation / Operational Notes

- **Update `CLAUDE.md`** after Unit 4 to document the `/home` route and the client-side rendering pattern, so future planning knows `/home` is not a `build.py` output
- **Add a Supabase section** to `CLAUDE.md` documenting the project URL location, RLS policy file, and the "anon key is safe to commit, RLS enforces security" reasoning
- **Memory update recommended** after launch: update `project_morning_lineup.md` in `.claude/projects/-home-tooyeezy/memory/` with accounts status, signup URL, and Supabase project reference
- **Monitoring:** No formal monitoring in v1. Supabase dashboard shows auth signups and DB row counts. SC6 (100 accounts in 30 days) and SC7 (40% multi-team) can be read directly from the dashboard

## Sources & References

- **Origin document:** `docs/brainstorms/accounts-and-custom-home-requirements.md`
- Related plans: `docs/plans/2026-04-08-004-feat-multi-team-support-plan.md` (multi-team foundation), `docs/plans/2026-04-10-001-refactor-sectioned-build-plan.md` (sectioned architecture that makes `/home` merge viable)
- Section renderers: `sections/headline.py`, `sections/scouting.py`, `sections/stretch.py`, `sections/pressbox.py`, `sections/farm.py`, `sections/slate.py`, `sections/division.py`, `sections/around_league.py`, `sections/history.py`
- Data ledger: `data/2026-04-10.json` (verified 2026-04-10)
- Build orchestrator: `build.py`
- Existing static: `cubs/index.html`, `yankees/index.html`, `landing.html`
- Snapshot tests: `tests/snapshot_test.py`, `tests/README.md`
- Supabase quickstart: `https://supabase.com/docs/guides/auth/quickstarts/vanilla-javascript`
- Supabase RLS: `https://supabase.com/docs/guides/database/postgres/row-level-security`
- SortableJS: `https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js`
